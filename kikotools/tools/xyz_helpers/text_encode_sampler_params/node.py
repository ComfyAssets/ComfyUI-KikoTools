"""Text Encode for Sampler Params node for ComfyUI."""

from typing import Tuple, Any
from ....base.base_node import ComfyAssetsBaseNode
from .logic import (
    split_prompts,
    encode_prompts,
    create_sampler_params_conditioning,
    validate_prompt_format,
)


class TextEncodeSamplerParamsNode(ComfyAssetsBaseNode):
    """
    Text Encode for Sampler Params node.

    Splits multi-line text by separators (---, ***, ===, ~~~) and encodes
    each part separately. Returns a special conditioning format suitable
    for batch processing and XYZ plot generation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "default": "Separate prompts with at least three dashes\n---\nLike so",
                        "tooltip": "Multi-line text with --- separators between prompts",
                    },
                ),
                "clip": ("CLIP", {"tooltip": "CLIP model for text encoding"}),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("conditioning",)
    FUNCTION = "encode_prompts"
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def encode_prompts(self, text: str, clip: Any) -> Tuple[Any]:
        """
        Split and encode multiple prompts for batch processing.

        Args:
            text: Multi-line text with separators
            clip: CLIP encoder model

        Returns:
            Tuple containing conditioning dictionary
        """
        try:
            if not validate_prompt_format(text):
                self.handle_error("Invalid prompt format")

            prompts = split_prompts(text)

            if not prompts:
                self.log_info("No prompts found in text")
                return ({"text": [], "encoded": []},)

            self.log_info(f"Processing {len(prompts)} prompts")

            encoded = encode_prompts(prompts, clip)

            if not encoded:
                self.handle_error("Failed to encode any prompts")

            conditioning = create_sampler_params_conditioning(prompts, encoded)

            self.log_info(
                f"Successfully encoded {len(encoded)} prompts "
                f"(avg {sum(len(p) for p in prompts) // len(prompts)} chars)"
            )

            return (conditioning,)

        except Exception as e:
            self.handle_error(f"Error processing prompts: {str(e)}", e)
            return ({"text": [], "encoded": []},)
