"""Scheduler Select Helper node for ComfyUI."""

from typing import Tuple
from ....base.base_node import ComfyAssetsBaseNode
from .logic import process_scheduler_selection, SCHEDULERS


class SchedulerSelectHelperNode(ComfyAssetsBaseNode):
    """
    Scheduler Select Helper node for multi-scheduler selection.

    Provides checkboxes for each available scheduler and returns a
    comma-separated string of selected schedulers. Useful for batch
    processing and XYZ plot generation.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        return {
            "required": {
                scheduler: (
                    "BOOLEAN",
                    {"default": False, "tooltip": f"Enable {scheduler} scheduler"},
                )
                for scheduler in SCHEDULERS
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_schedulers",)
    FUNCTION = "select_schedulers"
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def select_schedulers(self, **scheduler_flags) -> Tuple[str]:
        """
        Process scheduler selections and return comma-separated string.

        Args:
            **scheduler_flags: Boolean flags for each scheduler

        Returns:
            Tuple containing comma-separated string of selected schedulers
        """
        try:
            selected = process_scheduler_selection(**scheduler_flags)

            if selected:
                self.log_info(f"Selected {len(selected.split(', '))} schedulers")
            else:
                self.log_info("No schedulers selected")

            return (selected,)

        except Exception as e:
            self.handle_error(f"Error selecting schedulers: {str(e)}", e)
            return ("",)
