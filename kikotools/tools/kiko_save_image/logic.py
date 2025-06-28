"""
KikoSaveImage core logic
Enhanced image saving functionality with multiple format support
"""

import os
import json
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import torch
from typing import Dict, List, Any, Optional, Tuple
import time

try:
    import folder_paths
except ImportError:
    # Fallback for testing without ComfyUI
    class folder_paths:
        @staticmethod
        def get_output_directory():
            return "./output"


def get_save_image_path(
    filename_prefix: str,
    batch_number: int,
    format_ext: str,
    output_dir: str,
    subfolder: str = "",
) -> Tuple[str, str]:
    """
    Generate save path for image with proper filename handling

    Args:
        filename_prefix: Base filename prefix
        batch_number: Batch index for multiple images
        format_ext: File extension (.png, .jpg, .webp)
        output_dir: Output directory path
        subfolder: Optional subfolder within output directory

    Returns:
        Tuple of (full_path, relative_filename)
    """
    # Sanitize filename prefix to remove invalid characters
    # Replace path separators and other problematic characters
    safe_prefix = filename_prefix.replace("/", "_").replace("\\", "_").replace(":", "_")
    safe_prefix = "".join(c for c in safe_prefix if c.isalnum() or c in "._-")

    # Create unique filename with timestamp to avoid conflicts
    timestamp = int(time.time())
    filename = f"{safe_prefix}_{timestamp:010d}_{batch_number:05d}{format_ext}"

    # Handle subfolder
    if subfolder:
        full_output_folder = os.path.join(output_dir, subfolder)
    else:
        full_output_folder = output_dir

    # Ensure directory exists
    os.makedirs(full_output_folder, exist_ok=True)

    full_path = os.path.join(full_output_folder, filename)

    # For the preview, ComfyUI needs the filename and subfolder separately
    # The subfolder needs to be relative to the output directory root
    # `os.path.relpath` is not suitable here as it might resolve symbolic links
    # and produce `../` in paths, which is not what we want.
    # A simple string replacement or careful path joining is more robust.
    if subfolder:
        # Ensure subfolder is a relative path structure
        relative_subfolder = subfolder.strip("/\\")
        # The filename for the preview should not contain the subfolder path
        preview_filename = filename
    else:
        relative_subfolder = ""
        preview_filename = filename

    return full_path, preview_filename, relative_subfolder


def convert_tensor_to_pil(image_tensor: torch.Tensor) -> Image.Image:
    """
    Convert ComfyUI image tensor to PIL Image

    Args:
        image_tensor: Tensor in format [height, width, channels] with values 0-1

    Returns:
        PIL Image in RGB/RGBA format
    """
    # Convert tensor (0-1 float) to 0-255 numpy array
    i = 255.0 * image_tensor.cpu().numpy()
    img_array = np.clip(i, 0, 255).astype(np.uint8)

    # Create PIL image from numpy array
    img = Image.fromarray(img_array)

    return img


def create_png_metadata(
    prompt: Optional[Dict] = None, extra_pnginfo: Optional[Dict] = None
) -> Optional[PngInfo]:
    """
    Create PNG metadata with workflow information

    Args:
        prompt: ComfyUI prompt data
        extra_pnginfo: Additional PNG metadata

    Returns:
        PngInfo object or None if no metadata
    """
    if prompt is None and extra_pnginfo is None:
        return None

    metadata = PngInfo()

    if prompt is not None:
        metadata.add_text("prompt", json.dumps(prompt))

    if extra_pnginfo is not None:
        for key, value in extra_pnginfo.items():
            metadata.add_text(key, json.dumps(value))

    return metadata


def save_image_with_format(
    img: Image.Image,
    filepath: str,
    format_type: str,
    quality: int = 90,
    png_compress_level: int = 4,
    webp_lossless: bool = False,
    metadata: Optional[PngInfo] = None,
) -> Dict[str, Any]:
    """
    Save PIL image with specified format and quality settings

    Args:
        img: PIL Image to save
        filepath: Full path to save file
        format_type: Image format (PNG, JPEG, WEBP)
        quality: JPEG/WebP quality (1-100)
        png_compress_level: PNG compression level (0-9)
        webp_lossless: Use lossless WebP compression
        metadata: PNG metadata to embed

    Returns:
        Dict with save information
    """
    save_kwargs = {}

    if format_type == "PNG":
        if metadata:
            save_kwargs["pnginfo"] = metadata
        save_kwargs["compress_level"] = png_compress_level

    elif format_type == "JPEG":
        # Convert RGBA to RGB for JPEG (no transparency support)
        if img.mode == "RGBA":
            # Create white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True

    elif format_type == "WEBP":
        save_kwargs["quality"] = quality if not webp_lossless else 100
        save_kwargs["lossless"] = webp_lossless

    else:
        raise ValueError(f"Unsupported format: {format_type}")

    # Save the image
    img.save(filepath, **save_kwargs)

    # Get file size for info
    file_size = os.path.getsize(filepath)

    return {
        "filepath": filepath,
        "format": format_type,
        "file_size": file_size,
        "quality": quality if format_type != "PNG" else None,
        "compress_level": png_compress_level if format_type == "PNG" else None,
        "lossless": webp_lossless if format_type == "WEBP" else None,
    }


def process_image_batch(
    images: torch.Tensor,
    filename_prefix: str = "KikoSave",
    format_type: str = "PNG",
    quality: int = 90,
    png_compress_level: int = 4,
    webp_lossless: bool = False,
    popup: bool = True,
    prompt: Optional[Dict] = None,
    extra_pnginfo: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    Process and save a batch of images with specified format settings

    Args:
        images: Batch of image tensors [batch, height, width, channels]
        filename_prefix: Prefix for saved filenames
        format_type: Image format (PNG, JPEG, WEBP)
        quality: JPEG/WebP quality (1-100)
        png_compress_level: PNG compression level (0-9)
        webp_lossless: Use lossless WebP compression
        popup: Enable popup windows in UI
        prompt: ComfyUI prompt data for metadata
        extra_pnginfo: Additional PNG metadata

    Returns:
        List of saved image information dicts
    """
    # Get output directory
    output_dir = folder_paths.get_output_directory()

    # Determine file extension
    format_extensions = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}

    if format_type not in format_extensions:
        raise ValueError(
            f"Unsupported format: {format_type}. "
            f"Supported: {list(format_extensions.keys())}"
        )

    format_ext = format_extensions[format_type]

    # Create metadata for PNG
    metadata = None
    if format_type == "PNG":
        metadata = create_png_metadata(prompt, extra_pnginfo)

    # Process each image in the batch
    results = []
    enhanced_data = []

    for batch_number, image_tensor in enumerate(images):
        # Convert tensor to PIL Image
        img = convert_tensor_to_pil(image_tensor)

        # Generate save path
        filepath, preview_filename, relative_subfolder = get_save_image_path(
            filename_prefix, batch_number, format_ext, output_dir, ""
        )

        # Save with format-specific settings
        save_info = save_image_with_format(
            img,
            filepath,
            format_type,
            quality,
            png_compress_level,
            webp_lossless,
            metadata,
        )

        # Build result info for ComfyUI preview
        # ONLY the core fields that ComfyUI expects - no extra metadata
        result = {
            "filename": preview_filename,
            "subfolder": relative_subfolder,
            "type": "output",
        }

        # Store enhanced data separately
        enhanced_info = {
            "filename": preview_filename,
            "popup": popup,
            "type": "output",
            "format": format_type,
            "file_size": save_info["file_size"],
            "dimensions": f"{img.width}x{img.height}",
        }

        # Add format-specific info to enhanced data
        if format_type == "PNG":
            enhanced_info["compress_level"] = png_compress_level
        elif format_type in ["JPEG", "WEBP"]:
            enhanced_info["quality"] = quality
            if format_type == "WEBP":
                enhanced_info["lossless"] = webp_lossless

        results.append(result)
        enhanced_data.append(enhanced_info)

    return results, enhanced_data


def validate_save_inputs(
    images: torch.Tensor, format_type: str, quality: int, png_compress_level: int
) -> None:
    """
    Validate inputs for image saving

    Args:
        images: Image tensor batch to validate
        format_type: Image format to validate
        quality: Quality setting to validate
        png_compress_level: PNG compression level to validate

    Raises:
        ValueError: If validation fails
    """
    # Validate images tensor
    if not isinstance(images, torch.Tensor):
        raise ValueError(f"images must be a torch.Tensor, got {type(images).__name__}")

    if len(images.shape) != 4:
        raise ValueError(
            f"images tensor must have 4 dimensions [batch, height, width, channels], "
            f"got {len(images.shape)}"
        )

    # Validate format
    supported_formats = ["PNG", "JPEG", "WEBP"]
    if format_type not in supported_formats:
        raise ValueError(
            f"format must be one of {supported_formats}, got {format_type}"
        )

    # Validate quality (for JPEG/WebP)
    if format_type in ["JPEG", "WEBP"]:
        if not isinstance(quality, int) or not (1 <= quality <= 100):
            raise ValueError(
                f"quality must be an integer between 1 and 100, got {quality}"
            )

    # Validate PNG compression level
    if format_type == "PNG":
        if not isinstance(png_compress_level, int) or not (
            0 <= png_compress_level <= 9
        ):
            raise ValueError(
                f"png_compress_level must be an integer between 0 and 9, "
                f"got {png_compress_level}"
            )
