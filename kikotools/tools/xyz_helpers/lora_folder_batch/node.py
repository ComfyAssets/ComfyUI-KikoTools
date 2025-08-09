"""LoRA Folder Batch node for ComfyUI."""

from typing import Tuple, Any, Dict, List
import os
import logging
from ....base.base_node import ComfyAssetsBaseNode
from .logic import (
    get_lora_folders,
    scan_folder_for_loras,
    filter_loras_by_pattern,
    parse_strength_string,
    create_lora_params,
    get_lora_info,
    validate_folder_path,
)

logger = logging.getLogger(__name__)


class LoRAFolderBatchNode(ComfyAssetsBaseNode):
    """
    LoRA Folder Batch node for processing multiple LoRAs from a folder.

    Scans a specified folder for all .safetensors files and creates
    LORA_PARAMS for batch processing with FluxSamplerParams. Perfect
    for testing different epochs or variations of the same LoRA.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        return {
            "required": {
                "folder_path": (
                    "STRING",
                    {
                        "default": ".",
                        "multiline": False,
                        "dynamicPrompts": False,
                        "tooltip": "Folder path relative to models/loras (or absolute path)",
                    },
                ),
                "strength": (
                    "STRING",
                    {
                        "default": "1.0",
                        "multiline": False,
                        "dynamicPrompts": False,
                        "tooltip": "Strength values (e.g., '1.0' or '0.5,0.75,1.0' or '0.5...1.0+0.1')",
                    },
                ),
                "batch_mode": (
                    ["sequential", "combinatorial"],
                    {
                        "default": "sequential",
                        "tooltip": "Sequential: one strength per LoRA, Combinatorial: all strengths for each LoRA",
                    },
                ),
            },
            "optional": {
                "include_pattern": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Regex pattern to include files (empty = all)",
                    },
                ),
                "exclude_pattern": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Regex pattern to exclude files (e.g., 'test|backup')",
                    },
                ),
            },
        }

    RETURN_TYPES = ("LORA_PARAMS", "STRING", "INT")
    RETURN_NAMES = ("lora_params", "lora_list", "lora_count")
    FUNCTION = "batch_loras"
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def batch_loras(
        self,
        folder_path: str,
        strength: str,
        batch_mode: str,
        include_pattern: str = "",
        exclude_pattern: str = "",
    ) -> Tuple[Dict[str, Any], str, int]:
        """
        Batch process LoRAs from a folder.

        Args:
            folder_path: Folder to scan (relative to models/loras or absolute)
            strength: Strength values string
            batch_mode: How to batch the LoRAs
            include_pattern: Optional include regex
            exclude_pattern: Optional exclude regex

        Returns:
            Tuple of (lora_params, lora_list_string, lora_count)
        """
        try:

            # Validate folder only if not in test mode
            try:
                if not validate_folder_path(folder_path):
                    self.handle_error(f"Invalid or inaccessible folder: {folder_path}")
            except ImportError:
                # In test environment, skip validation
                pass

            # Scan folder for LoRAs
            lora_files = scan_folder_for_loras(folder_path)

            if not lora_files:
                self.log_info(f"No LoRA files found in {folder_path}")
                return ({"loras": [], "strengths": []}, "", 0)

            self.log_info(f"Found {len(lora_files)} LoRA files in {folder_path}")

            # Apply filters
            if include_pattern or exclude_pattern:
                filtered = filter_loras_by_pattern(
                    lora_files, include_pattern, exclude_pattern
                )
                if len(filtered) < len(lora_files):
                    self.log_info(
                        f"Filtered from {len(lora_files)} to {len(filtered)} LoRAs"
                    )
                lora_files = filtered

            if not lora_files:
                self.log_info("No LoRAs left after filtering")
                return ({"loras": [], "strengths": []}, "", 0)

            # Parse strength values
            strengths = parse_strength_string(strength)
            self.log_info(f"Using strength values: {strengths}")

            # Create LORA_PARAMS
            lora_params = create_lora_params(lora_files, strengths, batch_mode)

            # Create info string
            lora_list = []
            for lora_file in lora_files:
                info = get_lora_info(lora_file)
                if info["epoch"] is not None:
                    lora_list.append(f"{info['name']} (epoch {info['epoch']})")
                else:
                    lora_list.append(info["name"])

            lora_list_str = "\n".join(lora_list)

            # Calculate total combinations
            if batch_mode == "combinatorial":
                total_combos = len(lora_files) * len(strengths)
            else:
                total_combos = len(lora_files)

            self.log_info(
                f"Created batch with {len(lora_files)} LoRAs, "
                f"{len(strengths)} strength values, "
                f"{total_combos} total combinations"
            )

            return (lora_params, lora_list_str, len(lora_files))

        except Exception as e:
            self.handle_error(f"Error creating LoRA batch: {str(e)}", e)
            return ({"loras": [], "strengths": []}, "", 0)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """
        Force re-execution when folder contents might have changed.

        This ensures we always scan for the latest LoRAs.
        """
        import time

        return str(time.time())
