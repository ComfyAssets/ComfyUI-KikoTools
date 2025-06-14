"""Width Height Selector node for ComfyUI."""

from typing import Tuple
from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    get_preset_dimensions,
    calculate_aspect_ratio,
    validate_dimensions,
    sanitize_dimensions,
)
from .presets import (
    PRESET_OPTIONS,
    PRESET_DESCRIPTIONS,
    get_model_recommendation,
)


class WidthHeightSelectorNode(ComfyAssetsBaseNode):
    """
    Width Height Selector node for selecting image dimensions.

    Provides preset-based dimension selection with swap functionality,
    optimized for SDXL and FLUX models with comprehensive aspect ratio support.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        # Get all preset options excluding the custom tuple
        preset_keys = [key for key in PRESET_OPTIONS.keys()]

        return {
            "required": {
                "preset": (
                    preset_keys,
                    {
                        "default": "custom",
                        "tooltip": "Select from optimized resolution presets or use "
                        "custom dimensions. SDXL presets are ~1MP, FLUX presets are "
                        "higher resolution, Ultra-wide presets support modern "
                        "aspect ratios.",
                    },
                ),
                "width": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 64,
                        "max": 8192,
                        "step": 8,
                        "tooltip": "Custom width in pixels (must be multiple of 8). "
                        "Used when preset is 'custom' or as fallback for invalid "
                        "presets.",
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 64,
                        "max": 8192,
                        "step": 8,
                        "tooltip": "Custom height in pixels (must be multiple of 8). "
                        "Used when preset is 'custom' or as fallback for invalid "
                        "presets.",
                    },
                ),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "get_dimensions"
    CATEGORY = "ComfyAssets"

    def get_dimensions(self, preset: str, width: int, height: int) -> Tuple[int, int]:
        """
        Get width and height dimensions with preset and swap support.

        Args:
            preset: Selected preset name or "custom"
            width: Custom width value
            height: Custom height value

        Returns:
            Tuple of (width, height)
        """
        try:
            # Get base dimensions from preset or custom input
            final_width, final_height = get_preset_dimensions(preset, width, height)

            # Sanitize dimensions to ensure they meet ComfyUI requirements
            final_width, final_height = sanitize_dimensions(final_width, final_height)

            # Validate final dimensions
            if not validate_dimensions(final_width, final_height):
                # This should not happen after sanitization, but handle gracefully
                self.handle_error(
                    f"Generated invalid dimensions: {final_width}×{final_height}. "
                    f"Using fallback dimensions 1024×1024."
                )
                final_width, final_height = 1024, 1024

            return (final_width, final_height)

        except Exception as e:
            # Handle any unexpected errors gracefully
            error_msg = (
                f"Error processing dimensions: {str(e)}. Using fallback 1024×1024."
            )
            self.handle_error(error_msg)
            return (1024, 1024)

    def get_preset_info(self, preset: str) -> str:
        """
        Get descriptive information about a preset.

        Args:
            preset: Preset name

        Returns:
            Description string for the preset
        """
        if preset == "custom":
            return "Custom dimensions - use the width and height inputs below"

        if preset in PRESET_DESCRIPTIONS:
            return PRESET_DESCRIPTIONS[preset]

        # Fallback for unknown presets
        if preset in PRESET_OPTIONS:
            width, height = PRESET_OPTIONS[preset]
            aspect_ratio = calculate_aspect_ratio(width, height)
            return f"{preset} - {aspect_ratio} aspect ratio"

        return f"Unknown preset: {preset}"

    def get_model_optimization(self, preset: str) -> str:
        """
        Get model optimization information for a preset.

        Args:
            preset: Preset name

        Returns:
            Optimization information string
        """
        return get_model_recommendation(preset)

    def validate_inputs(self, preset: str, width: int, height: int) -> bool:
        """
        Validate node inputs.

        Args:
            preset: Preset name
            width: Width value
            height: Height value

        Returns:
            True if inputs are valid
        """
        # Check if preset exists or is custom
        if preset != "custom" and preset not in PRESET_OPTIONS:
            return False

        # For custom preset, validate dimensions
        if preset == "custom":
            if not validate_dimensions(width, height):
                return False

        return True

    @classmethod
    def get_preset_list(cls) -> list:
        """
        Get list of available presets for external use.

        Returns:
            List of preset names
        """
        return list(PRESET_OPTIONS.keys())

    @classmethod
    def get_preset_dimensions_static(cls, preset: str) -> Tuple[int, int]:
        """
        Static method to get preset dimensions without node instance.

        Args:
            preset: Preset name

        Returns:
            Tuple of (width, height) or (0, 0) if invalid
        """
        if preset in PRESET_OPTIONS:
            return PRESET_OPTIONS[preset]
        return (0, 0)

    def __str__(self) -> str:
        """String representation of the node."""
        return f"WidthHeightSelectorNode(presets={len(PRESET_OPTIONS)})"

    def __repr__(self) -> str:
        """Detailed string representation of the node."""
        return (
            f"WidthHeightSelectorNode("
            f"presets={len(PRESET_OPTIONS)}, "
            f"category='{self.CATEGORY}', "
            f"function='{self.FUNCTION}'"
            f")"
        )
