"""Empty Latent Batch node for ComfyUI."""

import torch
from typing import Dict, Any, Tuple

from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    create_empty_latent_batch,
    validate_dimensions,
    sanitize_dimensions,
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
        return {
            "required": {
                "width": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 64,
                        "max": 8192,
                        "step": 8,
                        "tooltip": "Width in pixels (must be multiple of 8). "
                        "This will be converted to latent space dimensions.",
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 1024,
                        "min": 64,
                        "max": 8192,
                        "step": 8,
                        "tooltip": "Height in pixels (must be multiple of 8). "
                        "This will be converted to latent space dimensions.",
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

    RETURN_TYPES = ("LATENT",)
    RETURN_NAMES = ("latent",)
    FUNCTION = "create_empty_latent"
    CATEGORY = "ComfyAssets"

    def create_empty_latent(
        self, width: int, height: int, batch_size: int
    ) -> Tuple[Dict[str, torch.Tensor]]:
        """
        Create empty latent tensor with specified dimensions and batch size.

        Args:
            width: Width in pixels
            height: Height in pixels
            batch_size: Number of latents in the batch

        Returns:
            Tuple containing latent dictionary with 'samples' tensor
        """
        try:
            # Sanitize dimensions to ensure they meet requirements
            final_width, final_height = sanitize_dimensions(width, height)

            # Log if dimensions were changed
            if final_width != width or final_height != height:
                self.log_info(
                    f"Dimensions adjusted from {width}×{height} to "
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

            return (latent_dict,)

        except Exception as e:
            # Handle any unexpected errors gracefully
            error_msg = f"Error creating empty latent batch: {str(e)}"
            self.handle_error(error_msg, e)

    def validate_inputs(self, width: int, height: int, batch_size: int) -> bool:
        """
        Validate node inputs.

        Args:
            width: Width value
            height: Height value
            batch_size: Batch size value

        Returns:
            True if inputs are valid
        """
        # Check dimension validity (after sanitization)
        sanitized_width, sanitized_height = sanitize_dimensions(width, height)
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
