"""Empty Latent Batch node for ComfyUI."""

import torch
from typing import Dict, Tuple

from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    create_empty_latent_batch,
    validate_dimensions,
    sanitize_dimensions,
)
from ..width_height_selector.logic import get_preset_dimensions
from ..width_height_selector.presets import (
    PRESET_OPTIONS,
    PRESET_METADATA,
)


class EmptyLatentBatchNode(ComfyAssetsBaseNode):
    """
    Empty Latent Batch node for creating empty latent tensors with batch support.

    Creates empty latent tensors with specified dimensions and batch size,
    compatible with ComfyUI's latent format for use with VAE and diffusion models.
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
                        "presets. This will be converted to latent space dimensions.",
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
                        "presets. This will be converted to latent space dimensions.",
                    },
                ),
                "batch_size": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 64,
                        "step": 1,
                        "tooltip": "Number of empty latents to create in the batch. "
                        "Useful for batch processing workflows.",
                    },
                ),
            }
        }

    RETURN_TYPES = ("LATENT", "INT", "INT")
    RETURN_NAMES = ("latent", "width", "height")
    FUNCTION = "create_empty_latent"
    CATEGORY = "🫶 ComfyAssets/📦 Latents"

    def create_empty_latent(
        self, preset: str, width: int, height: int, batch_size: int
    ) -> Tuple[Dict[str, torch.Tensor], int, int]:
        """
        Create empty latent tensor with specified dimensions and batch size.

        Args:
            preset: Selected preset name or formatted preset string
            width: Custom width value
            height: Custom height value
            batch_size: Number of latents in the batch

        Returns:
            Tuple containing (latent dictionary with 'samples' tensor, width, height)
        """
        try:
            # Extract original preset name from formatted string if needed
            original_preset = self._extract_preset_name(preset)

            # Get base dimensions from preset or custom input
            base_width, base_height = get_preset_dimensions(
                original_preset, width, height
            )

            # Sanitize dimensions to ensure they meet requirements
            final_width, final_height = sanitize_dimensions(base_width, base_height)

            # Log if dimensions were changed from the base dimensions
            if final_width != base_width or final_height != base_height:
                self.log_info(
                    f"Dimensions adjusted from {base_width}×{base_height} to "
                    f"{final_width}×{final_height} to meet VAE requirements"
                )

            # Validate final dimensions
            if not validate_dimensions(final_width, final_height):
                self.handle_error(
                    f"Invalid dimensions after sanitization: {final_width}×{final_height}"
                )

            # Validate batch size
            if batch_size <= 0:
                self.handle_error(f"Batch size must be positive, got {batch_size}")

            if batch_size > 64:
                self.log_info(
                    f"Large batch size ({batch_size}) may use significant memory"
                )

            # Create the empty latent batch
            latent_dict = create_empty_latent_batch(
                final_width, final_height, batch_size
            )

            # Log the operation
            latent_height = final_height // 8
            latent_width = final_width // 8
            self.log_info(
                f"Created empty latent batch: {batch_size}×4×{latent_height}×{latent_width} "
                f"(pixel dims: {final_width}×{final_height})"
            )

            return (latent_dict, final_width, final_height)

        except Exception as e:
            # Handle any unexpected errors gracefully
            error_msg = f"Error creating empty latent batch: {str(e)}"
            self.handle_error(error_msg, e)

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

    def validate_inputs(
        self, preset: str, width: int, height: int, batch_size: int
    ) -> bool:
        """
        Validate node inputs.

        Args:
            preset: Preset name or formatted preset string
            width: Width value
            height: Height value
            batch_size: Batch size value

        Returns:
            True if inputs are valid
        """
        # Extract original preset name
        original_preset = self._extract_preset_name(preset)

        # Check if preset exists or is custom
        if original_preset != "custom" and original_preset not in PRESET_OPTIONS:
            return False

        # Get dimensions from preset or use custom
        base_width, base_height = get_preset_dimensions(original_preset, width, height)

        # Check dimension validity (after sanitization)
        sanitized_width, sanitized_height = sanitize_dimensions(base_width, base_height)
        if not validate_dimensions(sanitized_width, sanitized_height):
            return False

        # Check batch size
        if batch_size <= 0 or batch_size > 64:
            return False

        return True

    def get_latent_info(self, width: int, height: int, batch_size: int) -> str:
        """
        Get descriptive information about the latent that will be created.

        Args:
            width: Width in pixels
            height: Height in pixels
            batch_size: Batch size

        Returns:
            Description string for the latent
        """
        sanitized_width, sanitized_height = sanitize_dimensions(width, height)
        latent_width = sanitized_width // 8
        latent_height = sanitized_height // 8

        return (
            f"Empty latent batch: {batch_size} × 4 × {latent_height} × {latent_width} "
            f"(pixel dimensions: {sanitized_width}×{sanitized_height})"
        )

    def get_memory_estimate(self, width: int, height: int, batch_size: int) -> str:
        """
        Estimate memory usage for the latent batch.

        Args:
            width: Width in pixels
            height: Height in pixels
            batch_size: Batch size

        Returns:
            Memory estimate string
        """
        sanitized_width, sanitized_height = sanitize_dimensions(width, height)
        latent_width = sanitized_width // 8
        latent_height = sanitized_height // 8

        # Calculate tensor size in bytes (float32 = 4 bytes per element)
        elements = batch_size * 4 * latent_height * latent_width
        bytes_size = elements * 4  # 4 bytes per float32

        # Convert to human-readable format
        if bytes_size < 1024:
            return f"{bytes_size} bytes"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"

    def __str__(self) -> str:
        """String representation of the node."""
        return "EmptyLatentBatchNode"

    def __repr__(self) -> str:
        """Detailed string representation of the node."""
        return (
            f"EmptyLatentBatchNode("
            f"category='{self.CATEGORY}', "
            f"function='{self.FUNCTION}'"
            f")"
        )


# Node class mappings for ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "EmptyLatentBatch": EmptyLatentBatchNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmptyLatentBatch": "Empty Latent Batch",
}
