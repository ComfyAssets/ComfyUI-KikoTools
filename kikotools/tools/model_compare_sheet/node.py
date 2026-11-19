"""Model Compare Sheet node for ComfyUI."""

import json
import os
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional

import numpy as np
import torch
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    GRID_FILENAME,
    PREVIEW_FILENAME,
    archive_previous_sweep,
    build_contact_sheet,
    list_tiles,
    preview_of,
    read_fingerprint,
    replace_index_tiles,
    resolve_run_dir,
    sweep_fingerprint,
    tile_filename,
    write_fingerprint,
)


class ModelCompareSheetNode(ComfyAssetsBaseNode):
    """
    Save each run's image into output/model_compare/<run_name>/ and rebuild a
    labeled contact sheet from every tile saved so far. Pair with Checkpoint
    Folder Iterator: after the last queued run the grid holds every model.

    A run at index 0, or a run whose settings (prompt, sampler settings, size,
    LoRAs: everything but the model index and seeds) differ from the ones the
    grid was started with, moves the existing tiles to <run_name>_<timestamp>
    and starts a new grid, so one sheet never mixes prompts.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "label": ("STRING", {"forceInput": True}),
                "index": ("INT", {"forceInput": True}),
                "run_name": (
                    "STRING",
                    {
                        "default": "illustrious",
                        "tooltip": "Subfolder of output/model_compare for this run",
                    },
                ),
                "columns": ("INT", {"default": 5, "min": 1, "max": 32}),
                "tile_width": ("INT", {"default": 512, "min": 64, "max": 4096}),
                "font_size": ("INT", {"default": 28, "min": 8, "max": 256}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("grid",)
    FUNCTION = "collect"
    OUTPUT_NODE = True
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def collect(
        self,
        images: torch.Tensor,
        label: str,
        index: int,
        run_name: str,
        columns: int,
        tile_width: int,
        font_size: int,
        prompt: Optional[Dict] = None,
        extra_pnginfo: Optional[Dict] = None,
        unique_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        import folder_paths

        if images.shape[0] == 0:
            raise ValueError("images must contain at least one image")

        output_dir = folder_paths.get_output_directory()
        run_dir = resolve_run_dir(output_dir, run_name)
        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        for key, value in (extra_pnginfo or {}).items():
            metadata.add_text(key, json.dumps(value))

        parent = os.path.dirname(run_dir)
        os.makedirs(parent, exist_ok=True)
        with TemporaryDirectory(prefix=".model-compare-", dir=parent) as staging:
            names = []
            for i, image in enumerate(images):
                array = (image.cpu().numpy().clip(0, 1) * 255).round().astype(np.uint8)
                name = tile_filename(index, label, i, images.shape[0])
                with Image.fromarray(array) as tile:
                    tile.save(
                        os.path.join(staging, name + ".tmp"),
                        format="PNG",
                        pnginfo=metadata,
                    )
                names.append(name)
            fingerprint = sweep_fingerprint(prompt, unique_id)
            recorded = read_fingerprint(run_dir)
            changed = None not in (fingerprint, recorded) and fingerprint != recorded
            if index == 0 or changed:
                archived = archive_previous_sweep(run_dir)
                if archived:
                    reason = "settings changed" if index else "new sweep"
                    self.log_info(f"{reason}: previous tiles moved to {archived}")
            os.makedirs(run_dir, exist_ok=True)
            replace_index_tiles(run_dir, index, staging, names)
            if fingerprint:
                write_fingerprint(run_dir, fingerprint)

        sheet = build_contact_sheet(list_tiles(run_dir), columns, tile_width, font_size)
        sheet.save(os.path.join(run_dir, GRID_FILENAME))
        preview_of(sheet).save(os.path.join(run_dir, PREVIEW_FILENAME))
        self.log_info(f"Contact sheet: {run_dir}/{GRID_FILENAME}")

        grid = torch.from_numpy(np.asarray(sheet).astype(np.float32) / 255.0)[None]
        subfolder = os.path.relpath(run_dir, output_dir)
        return {
            "ui": {
                "images": [
                    {
                        "filename": PREVIEW_FILENAME,
                        "subfolder": subfolder,
                        "type": "output",
                    }
                ]
            },
            "result": (grid,),
        }
