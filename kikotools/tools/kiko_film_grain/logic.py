import torch
import torch.nn.functional as F


def rgb_to_ycbcr(rgb: torch.Tensor) -> torch.Tensor:
    """
    Convert RGB tensor to YCbCr color space.

    Args:
        rgb: Tensor of shape [B, H, W, C] in range [0, 1]

    Returns:
        YCbCr tensor of same shape
    """
    ycbcr = rgb.detach().clone()
    r, g, b = rgb[:, :, :, 0], rgb[:, :, :, 1], rgb[:, :, :, 2]

    # ITU-R BT.709 coefficients
    ycbcr[:, :, :, 0] = 0.2126 * r + 0.7152 * g + 0.0722 * b  # Y
    ycbcr[:, :, :, 1] = -0.1146 * r - 0.3854 * g + 0.5 * b  # Cb
    ycbcr[:, :, :, 2] = 0.5 * r - 0.4542 * g - 0.0458 * b  # Cr

    return ycbcr


def ycbcr_to_rgb(ycbcr: torch.Tensor) -> torch.Tensor:
    """
    Convert YCbCr tensor to RGB color space.

    Args:
        ycbcr: Tensor of shape [B, H, W, C]

    Returns:
        RGB tensor of same shape in range [0, 1]
    """
    rgb = ycbcr.detach().clone()
    y, cb, cr = ycbcr[:, :, :, 0], ycbcr[:, :, :, 1], ycbcr[:, :, :, 2]

    rgb[:, :, :, 0] = y + 1.5748 * cr  # R
    rgb[:, :, :, 1] = y - 0.1873 * cb - 0.4681 * cr  # G
    rgb[:, :, :, 2] = y + 1.8556 * cb  # B

    return torch.clamp(rgb, 0, 1)


def apply_gaussian_blur(tensor: torch.Tensor, kernel_size: int) -> torch.Tensor:
    """
    Apply Gaussian blur to a tensor using PyTorch operations.

    Args:
        tensor: Tensor of shape [B, H, W, C]
        kernel_size: Size of the Gaussian kernel (must be odd)

    Returns:
        Blurred tensor of same shape
    """
    if kernel_size <= 1:
        return tensor

    # Ensure kernel size is odd
    kernel_size = kernel_size if kernel_size % 2 == 1 else kernel_size + 1

    # Create Gaussian kernel
    sigma = kernel_size / 3.0
    x = torch.arange(kernel_size, dtype=torch.float32) - kernel_size // 2
    gauss = torch.exp(-x.pow(2) / (2 * sigma**2))
    gauss = gauss / gauss.sum()

    # Create 2D kernel
    kernel = gauss.unsqueeze(0) * gauss.unsqueeze(1)
    kernel = kernel.unsqueeze(0).unsqueeze(0)

    # Apply blur per channel
    batch_size, h, w, channels = tensor.shape
    tensor_reshaped = tensor.permute(0, 3, 1, 2)  # [B, C, H, W]

    # Expand kernel for all channels
    kernel = kernel.repeat(channels, 1, 1, 1)

    # Apply convolution with padding
    padding = kernel_size // 2
    blurred = F.conv2d(tensor_reshaped, kernel, padding=padding, groups=channels)

    return blurred.permute(0, 2, 3, 1)  # Back to [B, H, W, C]


def generate_grain_texture(
    batch_size: int, height: int, width: int, scale: float, seed: int
) -> torch.Tensor:
    """
    Generate base grain texture at specified scale.

    Args:
        batch_size: Number of images in batch
        height: Target height
        width: Target width
        scale: Scale factor for grain size (larger = coarser grain)
        seed: Random seed for reproducibility

    Returns:
        Grain texture tensor of shape [B, H/scale, W/scale, 3]
    """
    torch.manual_seed(seed)

    grain_height = max(1, int(height / scale))
    grain_width = max(1, int(width / scale))

    # Generate random noise
    grain = torch.rand(batch_size, grain_height, grain_width, 3)

    return grain


def apply_film_grain(
    image: torch.Tensor,
    scale: float = 0.5,
    strength: float = 0.5,
    saturation: float = 0.7,
    toe: float = 0.0,
    seed: int = 0,
) -> torch.Tensor:
    """
    Apply film grain effect to an image with improved algorithms.

    Improvements over original:
    - Better color space conversion using ITU-R BT.709 coefficients
    - More efficient Gaussian blur using PyTorch convolutions
    - Improved grain mixing with better channel weighting
    - Preserves alpha channel if present
    - Better memory efficiency

    Args:
        image: Input tensor of shape [B, H, W, C] in range [0, 1]
        scale: Grain size (0.25-2.0, higher = coarser grain)
        strength: Grain intensity (0.0-10.0)
        saturation: Color saturation of grain (0.0-2.0)
        toe: Lift blacks/shadows (-0.2-0.5)
        seed: Random seed for reproducibility

    Returns:
        Image with film grain applied
    """
    if strength == 0.0:
        return image

    # Handle empty batch
    if image.shape[0] == 0:
        return image

    result = image.detach().clone()
    has_alpha = image.shape[-1] == 4

    # Generate grain texture
    grain = generate_grain_texture(
        image.shape[0], image.shape[1], image.shape[2], scale, seed
    )

    # Convert to YCbCr for better grain application
    grain_ycbcr = rgb_to_ycbcr(grain)

    # Apply different blur kernels to each channel for more realistic grain
    # Y channel - fine detail
    grain_ycbcr[:, :, :, 0] = apply_gaussian_blur(
        grain_ycbcr[:, :, :, 0:1], kernel_size=3
    ).squeeze(-1)

    # Cb channel - medium blur for color noise
    grain_ycbcr[:, :, :, 1] = apply_gaussian_blur(
        grain_ycbcr[:, :, :, 1:2], kernel_size=15
    ).squeeze(-1)

    # Cr channel - slightly less blur
    grain_ycbcr[:, :, :, 2] = apply_gaussian_blur(
        grain_ycbcr[:, :, :, 2:3], kernel_size=11
    ).squeeze(-1)

    # Convert back to RGB
    grain = ycbcr_to_rgb(grain_ycbcr)

    # Center grain around 0 and apply strength
    grain = (grain - 0.5) * strength

    # Apply channel-specific weighting for more realistic film grain
    # Film grain is typically stronger in blue channel, moderate in red
    grain[:, :, :, 0] *= 2.0  # Red channel
    grain[:, :, :, 1] *= 1.0  # Green channel (reference)
    grain[:, :, :, 2] *= 3.0  # Blue channel

    # Add 1 to make it multiplicative
    grain = grain + 1.0

    # Apply saturation control
    # Extract luminance for desaturation mixing
    luminance = grain[:, :, :, 1:2]  # Use green channel as approximation
    grain = grain * saturation + luminance * (1 - saturation)

    # Interpolate grain to match image size if needed
    if grain.shape[1] != image.shape[1] or grain.shape[2] != image.shape[2]:
        grain = F.interpolate(
            grain.permute(0, 3, 1, 2),
            size=(image.shape[1], image.shape[2]),
            mode="bilinear",
            align_corners=False,
        ).permute(0, 2, 3, 1)

    # Apply grain using screen blend mode: 1 - (1 - image) * grain
    # This preserves highlights better than multiply
    if has_alpha:
        # Only apply to RGB channels
        result[:, :, :, :3] = 1 - (1 - result[:, :, :, :3]) * grain
    else:
        result = 1 - (1 - result[:, :, :, :3]) * grain

    # Apply toe adjustment (lift blacks)
    if has_alpha:
        result[:, :, :, :3] = result[:, :, :, :3] * (1 - toe) + toe
    else:
        result = result * (1 - toe) + toe

    # Ensure output is in valid range
    return torch.clamp(result, 0, 1)
