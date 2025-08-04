"""Core logic for ImageScaleDownBy tool."""

import torch.nn.functional as F
from torch import Tensor


def scale_down_image(image: Tensor, scale_by: float) -> Tensor:
    """Scale down an image by a given factor.

    Args:
        image: Input image tensor of shape (batch, height, width, channels)
        scale_by: Scale factor between 0.01 and 1.0

    Returns:
        Scaled down image tensor
    """
    batch, height, width, channels = image.shape

    # Calculate new dimensions
    new_height = int(height * scale_by)
    new_width = int(width * scale_by)

    # Ensure minimum size of 1x1
    new_height = max(1, new_height)
    new_width = max(1, new_width)

    # Convert from BHWC to BCHW for interpolation
    image_chw = image.permute(0, 3, 1, 2)

    # Scale down the image using bilinear interpolation
    scaled = F.interpolate(
        image_chw,
        size=(new_height, new_width),
        mode="bilinear",
        align_corners=False,
        antialias=True,
    )

    # Convert back to BHWC
    return scaled.permute(0, 2, 3, 1)
