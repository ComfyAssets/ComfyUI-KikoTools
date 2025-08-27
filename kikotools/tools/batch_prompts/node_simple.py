"""Simple Batch Prompts node for ComfyUI - debugging version."""

import os
from typing import Tuple
from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    load_prompts_from_file,
    get_prompt_at_index,
    split_prompt_into_positive_negative,
)

# Global counter that persists across all executions
GLOBAL_COUNTER = {"count": 0}


class SimpleBatchPromptsNode(ComfyAssetsBaseNode):
    """
    Simplified Batch Prompts node for debugging.
    Uses a global counter to ensure prompts change.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        return {
            "required": {
                "prompt_file": ("STRING", {"default": "prompts.txt"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("positive", "negative", "index")
    FUNCTION = "get_next_prompt"
    CATEGORY = "🫶 ComfyAssets/📝 Text"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Force re-execution every time."""
        GLOBAL_COUNTER["count"] += 1
        return GLOBAL_COUNTER["count"]

    def get_next_prompt(self, prompt_file: str) -> Tuple[str, str, int]:
        """Get the next prompt in sequence."""
        # Resolve file path
        if not os.path.isabs(prompt_file):
            try:
                import folder_paths

                input_dir = folder_paths.get_input_directory()
                full_path = os.path.join(input_dir, prompt_file)
            except ImportError:
                full_path = os.path.abspath(prompt_file)
        else:
            full_path = prompt_file

        # Load prompts
        prompts = load_prompts_from_file(full_path)
        if not prompts:
            return ("No prompts found", "", 0)

        # Get current prompt based on global counter
        index = GLOBAL_COUNTER["count"] % len(prompts)
        current_prompt, _ = get_prompt_at_index(prompts, index, wrap=True)

        # Split positive/negative
        positive, negative = split_prompt_into_positive_negative(current_prompt)

        print(
            f"[SimpleBatchPrompts] Counter={GLOBAL_COUNTER['count']}, Index={index}, Prompt={positive[:30]}..."
        )

        return (positive, negative, index)
