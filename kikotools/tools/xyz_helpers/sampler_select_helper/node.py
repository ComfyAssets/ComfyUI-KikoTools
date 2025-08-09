"""Sampler Select Helper node for ComfyUI."""

from typing import Tuple
from ....base.base_node import ComfyAssetsBaseNode
from .logic import process_sampler_selection, SAMPLERS


class SamplerSelectHelperNode(ComfyAssetsBaseNode):
    """
    Sampler Select Helper node for multi-sampler selection.

    Provides checkboxes for each available sampler and returns a
    comma-separated string of selected samplers. Useful for batch
    processing and XYZ plot generation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        return {
            "required": {
                sampler: (
                    "BOOLEAN",
                    {"default": False, "tooltip": f"Enable {sampler} sampler"},
                )
                for sampler in SAMPLERS
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_samplers",)
    FUNCTION = "select_samplers"
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def select_samplers(self, **sampler_flags) -> Tuple[str]:
        """
        Process sampler selections and return comma-separated string.

        Args:
            **sampler_flags: Boolean flags for each sampler

        Returns:
            Tuple containing comma-separated string of selected samplers
        """
        try:
            selected = process_sampler_selection(**sampler_flags)

            if selected:
                self.log_info(f"Selected {len(selected.split(', '))} samplers")
            else:
                self.log_info("No samplers selected")

            return (selected,)

        except Exception as e:
            self.handle_error(f"Error selecting samplers: {str(e)}", e)
            return ("",)
