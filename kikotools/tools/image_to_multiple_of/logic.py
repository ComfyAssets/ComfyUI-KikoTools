"""Core logic for ImageToMultipleOf tool."""

from typing import Tuple

import torch.nn.functional as F
from torch import Tensor


def calculate_dimensions_to_multiple(
    height: int, width: int, multiple_of: int
) -> Tuple[int, int]:
    """Calculate new dimensions that are multiples of the specified value.

    Args:
        height: Original height
        width: Original width
        multiple_of: Value that dimensions should be multiple of

    Returns:
        Tuple of (new_height, new_width)
    """
    new_height = height - (height % multiple_of)
    new_width = width - (width % multiple_of)
    return new_height, new_width


def process_image_to_multiple_of(
    image: Tensor, multiple_of: int, method: str
) -> Tensor:
    """Process image to ensure dimensions are multiples of specified value.

    Args:
        image: Input image tensor of shape (batch, height, width, channels)
        multiple_of: Value that dimensions should be multiple of
        method: Processing method - "center crop" or "rescale"

    Returns:
        Processed image tensor
    """
    _, height, width, _ = image.shape
    new_height, new_width = calculate_dimensions_to_multiple(height, width, multiple_of)

    if method == "rescale":
        # Rescale the image to the new dimensions
        # Convert from BHWC to BCHW for interpolation
        image_chw = image.permute(0, 3, 1, 2)
        rescaled = F.interpolate(
            image_chw,
            size=(new_height, new_width),
            mode="bilinear",
            align_corners=False,
        )
        # Convert back to BHWC
        return rescaled.permute(0, 2, 3, 1)
    else:  # center crop
        # Calculate crop offsets to center the crop
        top = (height - new_height) // 2
        left = (width - new_width) // 2
        bottom = top + new_height
        right = left + new_width
        return image[:, top:bottom, left:right, :]
