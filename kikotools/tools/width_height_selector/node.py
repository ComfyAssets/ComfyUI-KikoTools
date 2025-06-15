"""Width Height Selector node for ComfyUI."""

from typing import Tuple
from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    get_preset_dimensions,
    validate_dimensions,
    sanitize_dimensions,
)
from .presets import (
    PRESET_OPTIONS,
    PRESET_METADATA,
    get_model_recommendation,
    get_preset_metadata,
    get_presets_by_model_group,
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
        # Create formatted preset options with metadata
        preset_options = ["custom"]  # Custom first

        # Add formatted presets with metadata
        for preset_name in PRESET_OPTIONS.keys():
            if preset_name != "custom":
                metadata = PRESET_METADATA.get(preset_name)
                if metadata:
                    formatted_option = (
                        f"{preset_name} - {metadata.aspect_ratio} "
                        f"({metadata.megapixels:.1f}MP) - {metadata.model_group}"
                    )
                    preset_options.append(formatted_option)
                else:
                    preset_options.append(preset_name)

        return {
            "required": {
                "preset": (
                    preset_options,
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
            preset: Selected preset name or formatted preset string
            width: Custom width value
            height: Custom height value

        Returns:
            Tuple of (width, height)
        """
        try:
            # Extract original preset name from formatted string if needed
            original_preset = self._extract_preset_name(preset)

            # Get base dimensions from preset or custom input
            final_width, final_height = get_preset_dimensions(
                original_preset, width, height
            )

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

    def _extract_preset_name(self, formatted_preset: str) -> str:
        """
        Extract the original preset name from a formatted preset string.

        Args:
            formatted_preset: Either original preset name or formatted string

        Returns:
            Original preset name
        """
        # If it's already "custom", return as-is
        if formatted_preset == "custom":
            return formatted_preset

        # If it contains formatting metadata, extract the resolution part
        if " - " in formatted_preset:
            # Format is: "1024×1024 - 1:1 (1.0MP) - SDXL"
            # Extract the first part (resolution)
            resolution_part = formatted_preset.split(" - ")[0]

            # Verify this is a valid preset name
            if resolution_part in PRESET_OPTIONS:
                return resolution_part

        # If no formatting or not found, check if it's directly a valid preset
        if formatted_preset in PRESET_OPTIONS:
            return formatted_preset

        # Default to "custom" if we can't parse it
        return "custom"

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

        metadata = get_preset_metadata(preset)
        if metadata.width > 0:  # Valid metadata
            return (
                f"{preset} - {metadata.aspect_ratio} ({metadata.megapixels:.1f}MP) - "
                f"{metadata.description}"
            )

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
            preset: Preset name or formatted preset string
            width: Width value
            height: Height value

        Returns:
            True if inputs are valid
        """
        # Extract original preset name
        original_preset = self._extract_preset_name(preset)

        # Check if preset exists or is custom
        if original_preset != "custom" and original_preset not in PRESET_OPTIONS:
            return False

        # For custom preset, validate dimensions
        if original_preset == "custom":
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

    @classmethod
    def get_presets_by_model(cls, model_group: str) -> dict:
        """
        Get all presets for a specific model group with metadata.

        Args:
            model_group: Model group name ("SDXL", "FLUX", "Ultra-Wide")

        Returns:
            Dictionary of presets with metadata
        """
        return get_presets_by_model_group(model_group)

    @classmethod
    def get_preset_metadata_static(cls, preset: str) -> dict:
        """
        Get metadata for a preset as a dictionary.

        Args:
            preset: Preset name

        Returns:
            Dictionary with metadata information
        """
        metadata = get_preset_metadata(preset)
        return {
            "width": metadata.width,
            "height": metadata.height,
            "aspect_ratio": metadata.aspect_ratio,
            "aspect_decimal": metadata.aspect_decimal,
            "megapixels": metadata.megapixels,
            "model_group": metadata.model_group,
            "category": metadata.category,
            "description": metadata.description,
        }

    @classmethod
    def get_model_groups(cls) -> list:
        """
        Get list of available model groups.

        Returns:
            List of model group names
        """
        return list(set(metadata.model_group for metadata in PRESET_METADATA.values()))

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
