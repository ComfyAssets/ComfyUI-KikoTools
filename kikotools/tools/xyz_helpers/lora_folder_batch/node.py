"""LoRA Folder Batch node for ComfyUI."""

from typing import Tuple, Any, Dict
import logging
from ....base.base_node import ComfyAssetsBaseNode
from .logic import (
    scan_folder_for_loras,
    filter_loras_by_pattern,
    parse_strength_string,
    create_lora_params,
    create_lora_params_batched,
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
                "max_loras": (
                    "INT",
                    {
                        "default": 50,
                        "min": 1,
                        "max": 500,
                        "tooltip": "Maximum number of LoRAs to process (to prevent UI disconnection)",
                    },
                ),
                "auto_batch": (
                    ["disabled", "enabled"],
                    {
                        "default": "disabled",
                        "tooltip": "Auto-batch large sets into chunks of 25 LoRAs",
                    },
                ),
                "batch_size": (
                    "INT",
                    {
                        "default": 25,
                        "min": 5,
                        "max": 100,
                        "tooltip": "Number of LoRAs per batch when auto-batching",
                    },
                ),
                "batch_index": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 100,
                        "tooltip": "Which batch to output (0-based index)",
                    },
                ),
                "sort_order": (
                    ["natural", "alphabetical", "newest", "oldest"],
                    {
                        "default": "natural",
                        "tooltip": "How to sort the LoRA files",
                    },
                ),
            },
        }

    RETURN_TYPES = ("LORA_PARAMS", "STRING", "INT")
    RETURN_NAMES = ("lora_params", "lora_list", "lora_count")
    FUNCTION = "batch_loras"
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def batch_loras(  # noqa: C901
        self,
        folder_path: str,
        strength: str,
        batch_mode: str,
        include_pattern: str = "",
        exclude_pattern: str = "",
        max_loras: int = 50,
        sort_order: str = "natural",
        auto_batch: str = "disabled",
        batch_size: int = 25,
        batch_index: int = 0,
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

            # Apply sorting based on sort_order
            if sort_order != "natural":
                from .logic import sort_lora_files

                lora_files = sort_lora_files(lora_files, sort_order)

            # Only limit if NOT auto-batching
            if auto_batch == "disabled" and len(lora_files) > max_loras:
                self.log_info(
                    f"⚠️ Limiting to {max_loras} LoRAs (found {len(lora_files)}). "
                    f"Enable auto_batch or increase max_loras to process more."
                )
                lora_files = lora_files[:max_loras]

            # Parse strength values
            strengths = parse_strength_string(strength)
            self.log_info(f"Using strength values: {strengths}")

            # Create LORA_PARAMS with auto-batching if enabled
            if auto_batch == "enabled" and len(lora_files) > batch_size:
                all_batches = create_lora_params_batched(
                    lora_files, strengths, batch_mode, batch_size
                )

                # Check if batch_index is valid
                if batch_index >= len(all_batches):
                    self.log_info(
                        f"⚠️ Batch index {batch_index} out of range. "
                        f"Only {len(all_batches)} batches available. Using batch 0."
                    )
                    batch_index = 0

                lora_params = all_batches[batch_index]

                # Update lora_files to only include current batch for list display
                batch_start = lora_params["batch_info"]["start_idx"]
                batch_end = lora_params["batch_info"]["end_idx"]
                lora_files_for_display = lora_files[batch_start:batch_end]
            else:
                # Regular single batch mode
                lora_params = create_lora_params(lora_files, strengths, batch_mode)
                lora_files_for_display = lora_files

            # Create info string for current batch only
            lora_list = []
            for lora_file in lora_files_for_display:
                info = get_lora_info(lora_file)
                if info["epoch"] is not None:
                    lora_list.append(f"{info['name']} (epoch {info['epoch']})")
                else:
                    lora_list.append(info["name"])

            # Add batch info to the list string if auto-batching
            if auto_batch == "enabled" and "batch_info" in lora_params:
                batch_header = (
                    f"=== Batch {batch_index + 1}/{lora_params['batch_info']['total']} "
                    f"(LoRAs {lora_params['batch_info']['start_idx'] + 1}-"
                    f"{lora_params['batch_info']['end_idx']}) ===\n\n"
                )
                lora_list_str = batch_header + "\n".join(lora_list)
            else:
                lora_list_str = "\n".join(lora_list)

            # Calculate total combinations for current batch
            current_batch_loras = len(lora_files_for_display)
            if batch_mode == "combinatorial":
                total_combos = current_batch_loras * len(strengths)
            else:
                total_combos = current_batch_loras

            # Warn if generating many combinations
            if total_combos > 100:
                self.log_info(
                    f"⚠️ WARNING: Generating {total_combos} combinations! "
                    f"This may cause UI disconnection. Consider reducing max_loras or strength values."
                )

            if auto_batch == "enabled" and "batch_info" in lora_params:
                self.log_info(
                    f"Output batch {batch_index + 1}/{lora_params['batch_info']['total']} "
                    f"with {current_batch_loras} LoRAs, "
                    f"{len(strengths)} strength values, "
                    f"{total_combos} total combinations"
                )
            else:
                self.log_info(
                    f"Created batch with {current_batch_loras} LoRAs, "
                    f"{len(strengths)} strength values, "
                    f"{total_combos} total combinations"
                )

            return (lora_params, lora_list_str, current_batch_loras)

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
