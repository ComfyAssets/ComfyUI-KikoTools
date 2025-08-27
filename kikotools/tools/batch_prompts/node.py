"""Batch Prompts node for ComfyUI."""

import os
from typing import Tuple
from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    load_prompts_from_file,
    get_prompt_at_index,
    get_next_prompt,
    get_prompt_preview,
    get_batch_info,
    validate_prompt_file,
    split_prompt_into_positive_negative,
)
from .state_manager import STATE_MANAGER


class BatchPromptsNode(ComfyAssetsBaseNode):
    """
    Batch Prompts node for loading and iterating through prompts from text files.

    Loads prompts from a text file where prompts are separated by '---' markers,
    provides iteration control, and outputs both current and next prompts with
    optional positive/negative splitting.
    """

    # Class variable to cache loaded prompts
    _prompt_cache = {}

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        # Try to get input folder path
        try:
            import folder_paths

            folder_paths.get_input_directory()
        except Exception:
            pass

        return {
            "required": {
                "prompt_file": (
                    "STRING",
                    {
                        "default": "prompts.txt",
                        "multiline": False,
                        "tooltip": "Path to text file containing prompts separated by '---'",
                    },
                ),
                "index": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 9999,
                        "step": 1,
                        "tooltip": "Current prompt index (0-based)",
                    },
                ),
                "auto_increment": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Automatically increment index after each execution",
                    },
                ),
                "wrap_around": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Wrap to first prompt after reaching the end",
                    },
                ),
                "split_negative": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Split prompts into positive/negative at 'Negative:' marker",
                    },
                ),
            },
            "optional": {
                "reload_file": (
                    "BOOLEAN",
                    {"default": False, "tooltip": "Force reload file from disk"},
                ),
                "show_preview": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "Show prompt preview in console"},
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "INT", "INT", "STRING")
    RETURN_NAMES = (
        "positive",
        "negative",
        "full_prompt",
        "next_prompt",
        "current_index",
        "total_prompts",
        "batch_info",
    )
    FUNCTION = "process_batch_prompts"
    CATEGORY = "🫶 ComfyAssets/📝 Text"

    def process_batch_prompts(
        self,
        prompt_file: str,
        index: int,
        auto_increment: bool,
        wrap_around: bool,
        split_negative: bool,
        reload_file: bool = False,
        show_preview: bool = True,
    ) -> Tuple[str, str, str, str, int, int, str]:
        """
        Process batch prompts from file.

        Args:
            prompt_file: Path to prompt file
            index: Current prompt index
            auto_increment: Whether to auto-increment index
            wrap_around: Whether to wrap around at end
            split_negative: Whether to split positive/negative prompts
            reload_file: Force reload from disk
            show_preview: Show prompt preview in console

        Returns:
            Tuple of (positive, negative, full_prompt, next_prompt, current_index, total_prompts, batch_info)
        """
        try:
            # Handle file path first to get a consistent key
            if not os.path.isabs(prompt_file):
                # Try to resolve relative to ComfyUI input directory
                try:
                    import folder_paths

                    input_dir = folder_paths.get_input_directory()
                    full_path = os.path.join(input_dir, prompt_file)
                except Exception:
                    # Fallback to current directory
                    full_path = os.path.abspath(prompt_file)
            else:
                full_path = prompt_file

            # Use persistent state manager for tracking execution
            if auto_increment:
                # Use file-based persistent state
                actual_index = STATE_MANAGER.increment_execution_count(full_path)
                print(
                    f"[BatchPrompts] Auto-increment: using index {actual_index} for {os.path.basename(prompt_file)}"
                )
            else:
                actual_index = index
                print(f"[BatchPrompts] Manual mode: using index {actual_index}")

            # Validate file
            is_valid, error_msg = validate_prompt_file(full_path)
            if not is_valid:
                self.handle_error(f"Invalid prompt file: {error_msg}")

            # Load prompts (with caching)
            cache_key = full_path
            if reload_file or cache_key not in self._prompt_cache:
                prompts = load_prompts_from_file(full_path)
                if not prompts:
                    self.handle_error(f"No prompts found in file: {prompt_file}")
                self._prompt_cache[cache_key] = prompts
                # Reset execution count when reloading file
                if reload_file:
                    STATE_MANAGER.reset_execution_count(full_path)
                self.log_info(f"Loaded {len(prompts)} prompts from {prompt_file}")
            else:
                prompts = self._prompt_cache[cache_key]

            # Get current prompt using the determined index
            current_prompt, used_index = get_prompt_at_index(
                prompts, actual_index, wrap_around
            )

            # Get next prompt
            next_prompt_text, next_index = get_next_prompt(
                prompts, used_index, wrap_around
            )

            # Split positive/negative if requested
            if split_negative:
                positive, negative = split_prompt_into_positive_negative(current_prompt)
            else:
                positive = current_prompt
                negative = ""

            # Get batch info
            batch_info_dict = get_batch_info(prompts, used_index)
            batch_info_str = (
                f"Prompt {batch_info_dict['current_index'] + 1} of {batch_info_dict['total_prompts']} "
                f"({batch_info_dict['percentage']:.1f}% complete)"
            )

            # Show preview if requested
            if show_preview:
                preview = get_prompt_preview(positive, 80)
                self.log_info(
                    f"Current prompt [{used_index + 1}/{len(prompts)}]: {preview}"
                )

            # No need to manually reset - the modulo operation in get_prompt_at_index handles wrapping

            return (
                positive,
                negative,
                current_prompt,
                next_prompt_text,
                used_index,
                len(prompts),
                batch_info_str,
            )

        except Exception as e:
            self.handle_error(f"Error processing batch prompts: {str(e)}")
            # Return empty values on error
            return ("", "", "", "", 0, 0, "Error")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """
        Check if node inputs have changed.
        This ensures the node re-executes when needed.
        """
        # Import time to ensure unique value each check
        import time

        # Return current timestamp to guarantee the node is seen as changed
        # This forces re-execution on every workflow run
        return str(time.time())
