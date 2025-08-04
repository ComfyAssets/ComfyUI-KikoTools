"""ComfyUI node implementation for ImageScaleDownBy."""

from typing import Dict, Any, Tuple

from torch import Tensor

from ...base import ComfyAssetsBaseNode
from .logic import scale_down_image


class ImageScaleDownByNode(ComfyAssetsBaseNode):
    """
    Scales down images by a specified factor.

    Reduces image dimensions proportionally using bilinear interpolation
    with antialiasing for smooth downscaling.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "images": ("IMAGE",),
                "scale_by": (
                    "FLOAT",
                    {
                        "default": 0.5,
                        "min": 0.01,
                        "max": 1.0,
                        "step": 0.01,
                        "display": "number",
                    },
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "scale_down"

    def scale_down(self, images: Tensor, scale_by: float) -> Tuple[Tensor]:
        """
        Scale down images by the specified factor.

        Args:
            images: Input image tensor
            scale_by: Scale factor between 0.01 and 1.0

        Returns:
            Tuple containing scaled down image tensor
        """
        try:
            self.validate_inputs(images=images, scale_by=scale_by)

            # Scale down the images
            scaled_images = scale_down_image(images, scale_by)

            _, new_height, new_width, _ = scaled_images.shape
            _, orig_height, orig_width, _ = images.shape

            self.log_info(
                f"Scaled down images from {orig_height}x{orig_width} "
                f"to {new_height}x{new_width} (scale factor: {scale_by})"
            )

            return (scaled_images,)

        except Exception as e:
            self.handle_error(f"Failed to scale down images: {str(e)}", e)

    def validate_inputs(self, **kwargs) -> None:
        """Validate inputs for ImageScaleDownBy node."""
        images = kwargs.get("images")
        scale_by = kwargs.get("scale_by")

        if images is None:
            raise ValueError("Images input is required")

        if not isinstance(images, Tensor) or len(images.shape) != 4:
            raise ValueError(
                f"Expected image tensor with shape (batch, height, width, channels), "
                f"got shape {images.shape if isinstance(images, Tensor) else 'non-tensor'}"
            )

        if scale_by <= 0 or scale_by > 1.0:
            raise ValueError(f"scale_by must be between 0.01 and 1.0, got {scale_by}")
