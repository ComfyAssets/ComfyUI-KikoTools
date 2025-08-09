"""ComfyUI node implementation for ImageToMultipleOf."""

from typing import Dict, Any, Tuple

from torch import Tensor

from ...base import ComfyAssetsBaseNode
from .logic import process_image_to_multiple_of


class ImageToMultipleOfNode(ComfyAssetsBaseNode):
    """
    Adjusts image dimensions to be multiples of a specified value.

    Useful for models that require specific dimension constraints.
    Supports both center cropping and rescaling methods.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "image": ("IMAGE",),
                "multiple_of": (
                    "INT",
                    {
                        "default": 64,
                        "min": 1,
                        "max": 256,
                        "step": 16,
                        "display": "number",
                    },
                ),
                "method": (["center crop", "rescale"],),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    CATEGORY = "🫶 ComfyAssets/🖼️ Resolution"
    RETURN_NAMES = ("image",)
    FUNCTION = "process"

    def process(self, image: Tensor, multiple_of: int, method: str) -> Tuple[Tensor]:
        """
        Process image to ensure dimensions are multiples of specified value.

        Args:
            image: Input image tensor
            multiple_of: Value that dimensions should be multiple of
            method: Processing method - "center crop" or "rescale"

        Returns:
            Tuple containing processed image tensor
        """
        try:
            self.validate_inputs(image=image, multiple_of=multiple_of, method=method)

            # Process the image
            processed_image = process_image_to_multiple_of(image, multiple_of, method)

            _, new_height, new_width, _ = processed_image.shape
            self.log_info(
                f"Processed image from {image.shape[1]}x{image.shape[2]} "
                f"to {new_height}x{new_width} (multiple of {multiple_of}) "
                f"using {method}"
            )

            return (processed_image,)

        except Exception as e:
            self.handle_error(f"Failed to process image: {str(e)}", e)

    def validate_inputs(self, **kwargs) -> None:
        """Validate inputs for ImageToMultipleOf node."""
        image = kwargs.get("image")
        multiple_of = kwargs.get("multiple_of")
        method = kwargs.get("method")

        if image is None:
            raise ValueError("Image input is required")

        if not isinstance(image, Tensor) or len(image.shape) != 4:
            raise ValueError(
                f"Expected image tensor with shape (batch, height, width, channels), "
                f"got shape {image.shape if isinstance(image, Tensor) else 'non-tensor'}"
            )

        if multiple_of <= 0:
            raise ValueError(f"multiple_of must be positive, got {multiple_of}")

        if method not in ["center crop", "rescale"]:
            raise ValueError(f"Invalid method: {method}")

        # Check if resulting dimensions would be too small
        _, height, width, _ = image.shape
        new_height = height - (height % multiple_of)
        new_width = width - (width % multiple_of)

        if new_height <= 0 or new_width <= 0:
            raise ValueError(
                f"Image dimensions ({height}x{width}) are too small "
                f"to be adjusted to multiple of {multiple_of}"
            )
