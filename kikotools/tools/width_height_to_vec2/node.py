"""
Width Height to VEC2 Node

Converts width and height inputs to a VEC2 tuple for use with
nodes like jovi_glsl that expect vector inputs.
"""

from typing import Any, Dict, Tuple, Union

from ...base import ComfyAssetsBaseNode


class WidthHeightToVec2Node(ComfyAssetsBaseNode):
    """
    Convert width and height values to VEC2 format.

    Accepts INT, FLOAT, STRING, or ANY types and outputs a VEC2 tuple
    suitable for nodes expecting vector inputs.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define ComfyUI input interface."""
        return {
            "required": {
                "width": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 1,
                        "max": 8192,
                        "step": 1,
                        "tooltip": "Width value (x component of VEC2)",
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 1,
                        "max": 8192,
                        "step": 1,
                        "tooltip": "Height value (y component of VEC2)",
                    },
                ),
            },
        }

    RETURN_TYPES = ("VEC2",)
    RETURN_NAMES = ("vec2",)
    FUNCTION = "convert_to_vec2"
    CATEGORY = "🫶 ComfyAssets/🖼️ Resolution"

    def convert_to_vec2(
        self,
        width: Union[int, float, str, Any],
        height: Union[int, float, str, Any],
    ) -> Tuple[Tuple[int, int]]:
        """
        Convert width and height to VEC2 tuple.

        Args:
            width: Width value (will be converted to int)
            height: Height value (will be converted to int)

        Returns:
            Tuple containing the VEC2 tuple (width, height)
        """
        try:
            # Convert to integers, handling various input types
            w = self._to_int(width, "width")
            h = self._to_int(height, "height")

            # Clamp values to valid range
            w = max(1, min(8192, w))
            h = max(1, min(8192, h))

            self.log_info(f"Converted to VEC2: ({w}, {h})")

            # Return as tuple wrapped in tuple (ComfyUI return format)
            return ((w, h),)

        except Exception as e:
            error_msg = f"Failed to convert to VEC2: {str(e)}"
            self.handle_error(error_msg, e)

    def _to_int(self, value: Any, name: str) -> int:
        """
        Convert a value to integer.

        Args:
            value: Value to convert (int, float, str, or any)
            name: Parameter name for error messages

        Returns:
            Integer value

        Raises:
            ValueError: If conversion fails
        """
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            return int(value)
        elif isinstance(value, str):
            try:
                # Try parsing as float first (handles "1024.0")
                return int(float(value.strip()))
            except ValueError:
                raise ValueError(f"Cannot convert {name} string '{value}' to integer")
        else:
            # Try generic conversion for ANY type
            try:
                return int(value)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Cannot convert {name} of type {type(value).__name__} to integer"
                )


# Node registration
NODE_CLASS_MAPPINGS = {
    "WidthHeightToVec2": WidthHeightToVec2Node,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WidthHeightToVec2": "Width Height to VEC2",
}
