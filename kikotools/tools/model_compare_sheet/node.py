"""Model Compare Sheet node for ComfyUI."""

import json
import os
from typing import Dict, Optional

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
    resolve_run_dir,
    tile_filename,
)


class ModelCompareSheetNode(ComfyAssetsBaseNode):
    """
    Save each run's image into output/model_compare/<run_name>/ and rebuild a
    labeled contact sheet from every tile saved so far. Pair with Checkpoint
    Folder Iterator: after the last queued run the grid holds every model.
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
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
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
    ):
        import folder_paths

        output_dir = folder_paths.get_output_directory()
        run_dir = resolve_run_dir(output_dir, run_name)
        if index == 0:
            archived = archive_previous_sweep(run_dir)
            if archived:
                self.log_info(f"New sweep: previous tiles moved to {archived}")
        os.makedirs(run_dir, exist_ok=True)

        metadata = PngInfo()
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
        for key, value in (extra_pnginfo or {}).items():
            metadata.add_text(key, json.dumps(value))

        for i, image in enumerate(images):
            array = (image.cpu().numpy().clip(0, 1) * 255).round().astype(np.uint8)
            name = tile_filename(index, label, i, images.shape[0])
            Image.fromarray(array).save(os.path.join(run_dir, name), pnginfo=metadata)

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
