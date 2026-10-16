"""Checkpoint Folder Iterator node for ComfyUI."""

from typing import Tuple

from ...base.base_node import ComfyAssetsBaseNode
from .logic import label_for, list_checkpoint_entries, pick_checkpoint


class CheckpointFolderIteratorNode(ComfyAssetsBaseNode):
    """
    Load one checkpoint from a folder per queued run.

    Set index to 0 with "increment" and queue as many runs as there are
    checkpoints: each run loads the next file, so only one model is in
    memory at a time. A run past the last checkpoint fails with a clear
    error rather than wrapping around, so over-queuing never restarts the
    sweep. Pairs with Model Compare Sheet to build a labeled grid.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder": (
                    "STRING",
                    {
                        "default": ".",
                        "multiline": False,
                        "tooltip": "Folder relative to models/checkpoints (or absolute)",
                    },
                ),
                "index": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 9999,
                        "control_after_generate": True,
                        "tooltip": "Which checkpoint to load; errors past the end",
                    },
                ),
            },
            "optional": {
                "include_pattern": (
                    "STRING",
                    {"default": "", "tooltip": "Regex to include (empty = all)"},
                ),
                "exclude_pattern": (
                    "STRING",
                    {"default": "", "tooltip": "Regex to exclude (empty = none)"},
                ),
            },
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE", "STRING", "STRING", "INT", "INT")
    RETURN_NAMES = ("model", "clip", "vae", "ckpt_name", "label", "index", "count")
    FUNCTION = "load"
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def load(
        self,
        folder: str,
        index: int,
        include_pattern: str = "",
        exclude_pattern: str = "",
    ) -> Tuple[object, object, object, str, str, int, int]:
        import folder_paths
        import comfy.sd

        entries = list_checkpoint_entries(folder, include_pattern, exclude_pattern)
        ckpt_name, ckpt_path = pick_checkpoint(entries, index)
        self.log_info(f"Loading {index + 1}/{len(entries)}: {ckpt_name}")

        model, clip, vae = comfy.sd.load_checkpoint_guess_config(
            ckpt_path,
            output_vae=True,
            output_clip=True,
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
        )[:3]
        return model, clip, vae, ckpt_name, label_for(ckpt_name), index, len(entries)
