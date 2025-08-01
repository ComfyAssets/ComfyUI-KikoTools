"""Core logic for Width Height Selector tool."""

from typing import Tuple
from math import gcd
from .presets import PRESET_OPTIONS


def get_preset_dimensions(
    preset: str, custom_width: int, custom_height: int
) -> Tuple[int, int]:
    """
    Get dimensions from preset name or use custom dimensions.

    Args:
        preset: Preset name (e.g., "1024×1024", "custom")
        custom_width: Custom width value
        custom_height: Custom height value

    Returns:
        Tuple of (width, height) as integers
    """
    if preset == "custom" or preset not in PRESET_OPTIONS:
        return custom_width, custom_height

    return PRESET_OPTIONS[preset]


def apply_swap_logic(width: int, height: int, swap_enabled: bool) -> Tuple[int, int]:
    """
    Apply swap logic to dimensions.

    Args:
        width: Original width
        height: Original height
        swap_enabled: Whether to swap dimensions

    Returns:
        Tuple of (width, height) after potential swap
    """
    if swap_enabled:
        return height, width
    return width, height


def calculate_aspect_ratio(width: int, height: int) -> str:
    """
    Calculate and format aspect ratio as a string.

    Args:
        width: Image width
        height: Image height

    Returns:
        Formatted aspect ratio string (e.g., "16:9", "4:3", "1:1")
    """
    if width <= 0 or height <= 0:
        return "Invalid"

    # Calculate greatest common divisor to simplify ratio
    ratio_gcd = gcd(width, height)
    ratio_width = width // ratio_gcd
    ratio_height = height // ratio_gcd

    return f"{ratio_width}:{ratio_height}"


def validate_dimensions(width: int, height: int) -> bool:
    """
    Validate that dimensions meet ComfyUI requirements.

    Args:
        width: Image width to validate
        height: Image height to validate

    Returns:
        True if dimensions are valid, False otherwise
    """
    # Check positive values
    if width <= 0 or height <= 0:
        return False

    # Check divisible by 8 (ComfyUI requirement)
    if width % 8 != 0 or height % 8 != 0:
        return False

    # Check reasonable bounds (64 minimum, 8192 maximum)
    if not (64 <= width <= 8192) or not (64 <= height <= 8192):
        return False

    return True


def sanitize_dimensions(width: int, height: int) -> Tuple[int, int]:
    """
    Sanitize dimensions to meet ComfyUI requirements.

    Rounds to nearest multiple of 8 and clamps to valid range.

    Args:
        width: Raw width value
        height: Raw height value

    Returns:
        Tuple of sanitized (width, height)
    """
    # Clamp to valid range
    width = max(64, min(8192, width))
    height = max(64, min(8192, height))

    # Round to nearest multiple of 8
    width = ((width + 4) // 8) * 8
    height = ((height + 4) // 8) * 8

    return width, height


def get_dimension_info(
    preset: str, width: int, height: int, swap_enabled: bool
) -> dict:
    """
    Get comprehensive dimension information including metadata.

    Args:
        preset: Preset name
        width: Width value
        height: Height value
        swap_enabled: Whether swap is enabled

    Returns:
        Dictionary with dimension info and metadata
    """
    # Get base dimensions from preset or custom
    base_width, base_height = get_preset_dimensions(preset, width, height)

    # Apply swap if enabled
    final_width, final_height = apply_swap_logic(base_width, base_height, swap_enabled)

    # Calculate metadata
    aspect_ratio = calculate_aspect_ratio(final_width, final_height)
    is_valid = validate_dimensions(final_width, final_height)
    is_square = final_width == final_height
    is_landscape = final_width > final_height
    is_portrait = final_height > final_width

    # Calculate megapixels
    megapixels = (final_width * final_height) / 1_000_000

    return {
        "width": final_width,
        "height": final_height,
        "aspect_ratio": aspect_ratio,
        "is_valid": is_valid,
        "is_square": is_square,
        "is_landscape": is_landscape,
        "is_portrait": is_portrait,
        "megapixels": round(megapixels, 2),
        "preset_used": preset,
        "swap_applied": swap_enabled,
    }


def format_dimension_string(width: int, height: int) -> str:
    """
    Format dimensions as a readable string.

    Args:
        width: Image width
        height: Image height

    Returns:
        Formatted dimension string (e.g., "1920×1080")
    """
    return f"{width}×{height}"


def parse_dimension_string(dimension_str: str) -> Tuple[int, int]:
    """
    Parse dimension string back to width/height integers.

    Args:
        dimension_str: Dimension string (e.g., "1920×1080", "1920x1080")

    Returns:
        Tuple of (width, height) as integers

    Raises:
        ValueError: If dimension string cannot be parsed
    """
    # Handle both × and x separators
    if "×" in dimension_str:
        parts = dimension_str.split("×")
    elif "x" in dimension_str:
        parts = dimension_str.split("x")
    else:
        raise ValueError(f"Invalid dimension string format: {dimension_str}")

    if len(parts) != 2:
        raise ValueError(f"Dimension string must have exactly 2 parts: {dimension_str}")

    try:
        width = int(parts[0].strip())
        height = int(parts[1].strip())
        return width, height
    except ValueError as e:
        raise ValueError(f"Could not parse dimensions from {dimension_str}: {e}")


def get_optimal_scale_factor(
    current_width: int, current_height: int, target_width: int, target_height: int
) -> float:
    """
    Calculate optimal scale factor to get from current to target dimensions.

    Args:
        current_width: Current image width
        current_height: Current image height
        target_width: Target width
        target_height: Target height

    Returns:
        Scale factor as float
    """
    if current_width <= 0 or current_height <= 0:
        return 1.0

    width_scale = target_width / current_width
    height_scale = target_height / current_height

    # Return the average scale factor
    return (width_scale + height_scale) / 2.0


def suggest_similar_presets(width: int, height: int, max_suggestions: int = 3) -> list:
    """
    Suggest similar presets based on current dimensions.

    Args:
        width: Current width
        height: Current height
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of preset names sorted by similarity
    """
    if width <= 0 or height <= 0:
        return []

    current_ratio = width / height
    suggestions = []

    for preset_name, (preset_width, preset_height) in PRESET_OPTIONS.items():
        if preset_name == "custom":
            continue

        preset_ratio = preset_width / preset_height
        ratio_diff = abs(current_ratio - preset_ratio)

        suggestions.append((preset_name, ratio_diff))

    # Sort by similarity (smallest ratio difference first)
    suggestions.sort(key=lambda x: x[1])

    # Return just the preset names
    return [preset[0] for preset in suggestions[:max_suggestions]]
