"""
Core calculation logic for Resolution Calculator
Pure functions for dimension extraction and scaling calculations
"""

import torch
from typing import Tuple, Optional, Dict


def extract_dimensions(
    image: Optional[torch.Tensor] = None,
    latent: Optional[Dict[str, torch.Tensor]] = None,
) -> Tuple[int, int]:
    """
    Extract width and height from IMAGE or LATENT tensor

    Args:
        image: Optional IMAGE tensor in ComfyUI format [batch, height, width, channels]
        latent: Optional LATENT dict with 'samples' tensor
                [batch, channels, height/8, width/8]

    Returns:
        Tuple of (width, height) as integers

    Raises:
        ValueError: If neither image nor latent is provided
    """
    if image is not None:
        # IMAGE tensor format: [batch, height, width, channels]
        if len(image.shape) != 4:
            raise ValueError(
                f"Expected IMAGE tensor with 4 dimensions, got {len(image.shape)}"
            )

        _, height, width, _ = image.shape
        return int(width), int(height)

    elif latent is not None:
        # LATENT format: {"samples": [batch, channels, height/8, width/8]}
        if "samples" not in latent:
            raise ValueError("LATENT dict must contain 'samples' key")

        samples = latent["samples"]
        if len(samples.shape) != 4:
            raise ValueError(
                f"Expected LATENT samples tensor with 4 dimensions, "
                f"got {len(samples.shape)}"
            )

        _, _, latent_height, latent_width = samples.shape

        # Latent dimensions are 1/8 of actual image dimensions
        width = int(latent_width * 8)
        height = int(latent_height * 8)
        return width, height

    else:
        raise ValueError("Either image or latent must be provided")


def ensure_divisible_by_8(width: int, height: int) -> Tuple[int, int]:
    """
    Ensure dimensions are divisible by 8 (ComfyUI requirement)
    Rounds to the nearest multiple of 8

    Args:
        width: Input width
        height: Input height

    Returns:
        Tuple of (width, height) both divisible by 8
    """
    # Round to nearest multiple of 8
    # Formula: ((value + 4) // 8) * 8
    # This rounds 0-3 down, 4-7 up, ensuring nearest multiple
    new_width = ((width + 4) // 8) * 8
    new_height = ((height + 4) // 8) * 8

    return int(new_width), int(new_height)


def calculate_scaled_dimensions(
    width: int, height: int, scale_factor: float
) -> Tuple[int, int]:
    """
    Calculate new dimensions with scale factor and ensure divisible by 8

    Args:
        width: Original width
        height: Original height
        scale_factor: Scaling factor (e.g., 1.5, 2.0, 3.0)

    Returns:
        Tuple of (new_width, new_height) both divisible by 8
    """
    if scale_factor <= 0:
        raise ValueError(f"Scale factor must be positive, got {scale_factor}")

    # Calculate new dimensions
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    # Ensure divisible by 8
    return ensure_divisible_by_8(new_width, new_height)


def validate_scale_factor(
    scale_factor: float, min_scale: float = 0.1, max_scale: float = 8.0
) -> None:
    """
    Validate scale factor is within reasonable bounds

    Args:
        scale_factor: Scale factor to validate
        min_scale: Minimum allowed scale factor
        max_scale: Maximum allowed scale factor

    Raises:
        ValueError: If scale factor is out of bounds
    """
    if not isinstance(scale_factor, (int, float)):
        raise ValueError(
            f"Scale factor must be a number, got {type(scale_factor).__name__}"
        )

    if scale_factor < min_scale:
        raise ValueError(
            f"Scale factor {scale_factor} is too small (minimum: {min_scale})"
        )

    if scale_factor > max_scale:
        raise ValueError(
            f"Scale factor {scale_factor} is too large (maximum: {max_scale})"
        )


def calculate_resolution_from_input(
    scale_factor: float,
    image: Optional[torch.Tensor] = None,
    latent: Optional[Dict[str, torch.Tensor]] = None,
) -> Tuple[int, int]:
    """
    Main function to calculate resolution from input tensor and scale factor
    Combines all the logic steps into a single function

    Args:
        scale_factor: Scaling factor
        image: Optional IMAGE tensor
        latent: Optional LATENT dict

    Returns:
        Tuple of (width, height) scaled and divisible by 8

    Raises:
        ValueError: For various validation errors
    """
    # Validate scale factor
    validate_scale_factor(scale_factor)

    # Extract original dimensions
    original_width, original_height = extract_dimensions(image=image, latent=latent)

    # Calculate scaled dimensions
    new_width, new_height = calculate_scaled_dimensions(
        original_width, original_height, scale_factor
    )

    return new_width, new_height
