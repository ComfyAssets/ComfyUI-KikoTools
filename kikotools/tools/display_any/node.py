"""DisplayAny node for ComfyUI - displays any input value or tensor information."""

from typing import Any, Dict, Tuple

from ...base import ComfyAssetsBaseNode
from .logic import format_display_value, validate_display_mode


class DisplayAnyNode(ComfyAssetsBaseNode):
    """Display any input value or tensor shape information.

    This node can display any type of input in two modes:
    - Raw value: Shows the string representation of the input
    - Tensor shape: Extracts and displays shapes of any tensors in the input
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define input types for the node."""
        return {
            "required": {
                "input": ("*", {}),  # Accept any type of input
                "mode": (["raw value", "tensor shape"],),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs) -> bool:
        """Validate inputs - always returns True as we accept any input."""
        return True

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("display_text",)
    FUNCTION = "display"
    OUTPUT_NODE = True  # This node displays output in the UI

    def display(self, input: Any, mode: str = "raw value") -> Dict[str, Any]:
        """Display the input value according to the selected mode.

        Args:
            input: Any input value to display
            mode: Display mode - "raw value" or "tensor shape"

        Returns:
            Dictionary with UI display and result
        """
        # Validate mode
        if not validate_display_mode(mode):
            mode = "raw value"  # Default to raw value if invalid

        # Format the display text
        display_text = format_display_value(input, mode)

        # Return both UI display and result
        return {
            "ui": {"text": display_text},
            "result": (display_text,),
        }
