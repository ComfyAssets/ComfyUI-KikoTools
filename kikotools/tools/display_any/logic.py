"""Logic for DisplayAny node - displays any input value or tensor shape."""

from typing import Any, List


def get_tensor_shapes(input_value: Any) -> List[List[int]]:
    """Extract tensor shapes from nested structures.

    Args:
        input_value: Any input value that may contain tensors

    Returns:
        List of tensor shapes found in the input
    """
    shapes = []

    def extract_shapes(value: Any) -> None:
        """Recursively extract shapes from nested structures."""
        if isinstance(value, dict):
            for v in value.values():
                extract_shapes(v)
        elif isinstance(value, (list, tuple)):
            for item in value:
                extract_shapes(item)
        elif hasattr(value, "shape"):
            # Handle tensors (numpy arrays, torch tensors, etc.)
            shapes.append(list(value.shape))

    extract_shapes(input_value)
    return shapes


def format_display_value(input_value: Any, mode: str = "raw value") -> str:
    """Format input value for display based on selected mode.

    Args:
        input_value: Any input value to display
        mode: Display mode - "raw value" or "tensor shape"

    Returns:
        Formatted string representation of the input
    """
    if mode == "tensor shape":
        shapes = get_tensor_shapes(input_value)
        if shapes:
            return str(shapes)
        else:
            return "No tensors found in input"

    # Default to raw value display
    # Try to format as JSON for better readability
    try:
        import json

        if isinstance(input_value, (dict, list)):
            return json.dumps(input_value, indent=2)
    except (TypeError, ValueError):
        pass

    return str(input_value)


def validate_display_mode(mode: str) -> bool:
    """Validate if the display mode is supported.

    Args:
        mode: Display mode to validate

    Returns:
        True if mode is valid, False otherwise
    """
    valid_modes = ["raw value", "tensor shape"]
    return mode in valid_modes
