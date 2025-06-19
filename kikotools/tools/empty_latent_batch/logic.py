"""Logic for creating empty latent tensors with batch support."""

import torch
from typing import Dict, Tuple, Any


def create_empty_latent_batch(
    width: int, height: int, batch_size: int = 1
) -> Dict[str, torch.Tensor]:
    """
    Create empty latent tensor with batch support.

    Args:
        width: Width in pixels (will be divided by 8 for latent space)
        height: Height in pixels (will be divided by 8 for latent space)
        batch_size: Number of latents in the batch

    Returns:
        Dictionary containing the latent samples tensor

    Raises:
        ValueError: If dimensions are invalid
    """
    # Validate inputs
    if width <= 0 or height <= 0:
        raise ValueError(f"Width and height must be positive, got {width}x{height}")

    if batch_size <= 0:
        raise ValueError(f"Batch size must be positive, got {batch_size}")

    # Ensure dimensions are divisible by 8 (VAE requirement)
    if width % 8 != 0 or height % 8 != 0:
        raise ValueError(
            f"Width and height must be divisible by 8, got {width}x{height}"
        )

    # Convert pixel dimensions to latent space (divide by 8)
    latent_width = width // 8
    latent_height = height // 8

    # Create empty latent tensor
    # ComfyUI latent format: [batch, channels, height, width]
    # Standard VAE uses 4 channels
    latent_tensor = torch.zeros(batch_size, 4, latent_height, latent_width)

    return {"samples": latent_tensor}


def validate_dimensions(width: int, height: int) -> bool:
    """
    Validate that dimensions are suitable for latent creation.

    Args:
        width: Width in pixels
        height: Height in pixels

    Returns:
        True if dimensions are valid
    """
    # Check basic constraints
    if width <= 0 or height <= 0:
        return False

    # Check divisibility by 8
    if width % 8 != 0 or height % 8 != 0:
        return False

    # Check reasonable size limits (64x64 to 8192x8192)
    if width < 64 or height < 64:
        return False

    if width > 8192 or height > 8192:
        return False

    return True


def sanitize_dimensions(width: int, height: int) -> Tuple[int, int]:
    """
    Sanitize dimensions to ensure they meet latent requirements.

    Args:
        width: Input width
        height: Input height

    Returns:
        Tuple of (sanitized_width, sanitized_height)
    """
    # Ensure minimum dimensions
    width = max(64, width)
    height = max(64, height)

    # Ensure maximum dimensions
    width = min(8192, width)
    height = min(8192, height)

    # Round to nearest multiple of 8
    width = (width + 7) // 8 * 8
    height = (height + 7) // 8 * 8

    return width, height
