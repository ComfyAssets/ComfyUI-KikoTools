"""
KikoSaveImage ComfyUI Node
Enhanced image saving with format selection, quality control, and clickable previews
"""

import torch
from typing import Dict, Any, Optional

from ...base import ComfyAssetsBaseNode
from .logic import process_image_batch, validate_save_inputs


class KikoSaveImageNode(ComfyAssetsBaseNode):
    """
    Enhanced ComfyUI image saving node with multiple format support

    Features:
    - Multiple format support (PNG, JPEG, WebP)
    - Quality/compression controls
    - Clickable image previews
    - Metadata preservation
    - Batch processing

    Inputs:
        - images (IMAGE): Images to save
        - filename_prefix (STRING): Prefix for saved filenames
        - format (COMBO): Output format (PNG, JPEG, WebP)
        - quality (INT): JPEG/WebP quality (1-100)
        - png_compress_level (INT): PNG compression level (0-9)
        - webp_lossless (BOOLEAN): Use lossless WebP compression
        - subfolder (STRING): Optional subfolder for organization

    Outputs:
        - UI: Image preview data for ComfyUI interface
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """
        Define ComfyUI input interface with enhanced save options

        Returns:
            Dict with required and optional input specifications
        """
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save"}),
                "filename_prefix": (
                    "STRING",
                    {"default": "KikoSave", "tooltip": "Prefix for saved filenames"},
                ),
                "format": (
                    ["PNG", "JPEG", "WEBP"],
                    {"default": "PNG", "tooltip": "Output image format"},
                ),
            },
            "optional": {
                "quality": (
                    "INT",
                    {
                        "default": 90,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "tooltip": "JPEG/WebP quality (1-100, higher = better quality)",
                    },
                ),
                "png_compress_level": (
                    "INT",
                    {
                        "default": 4,
                        "min": 0,
                        "max": 9,
                        "step": 1,
                        "tooltip": "PNG compression level (0-9, higher = smaller file)",
                    },
                ),
                "webp_lossless": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Use lossless WebP compression "
                        "(ignores quality setting)",
                    },
                ),
                "popup": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Enable popup windows when clicking on images in the viewer",
                    },
                ),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    CATEGORY = "ComfyAssets/💾 Images"
    FUNCTION = "save_images"
    OUTPUT_NODE = True

    def save_images(
        self,
        images: torch.Tensor,
        filename_prefix: str = "KikoSave",
        format: str = "PNG",
        quality: int = 90,
        png_compress_level: int = 4,
        webp_lossless: bool = False,
        popup: bool = True,
        prompt: Optional[Dict] = None,
        extra_pnginfo: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Save images with enhanced format and quality options

        Args:
            images: Batch of image tensors to save
            filename_prefix: Prefix for saved filenames
            format: Output format (PNG, JPEG, WebP)
            quality: JPEG/WebP quality setting
            png_compress_level: PNG compression level
            webp_lossless: Use lossless WebP compression
            popup: Enable popup windows when clicking on images
            prompt: ComfyUI prompt data for metadata
            extra_pnginfo: Additional PNG metadata

        Returns:
            Dict with UI data for image previews

        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate inputs
            self.validate_inputs(
                images=images,
                format=format,
                quality=quality,
                png_compress_level=png_compress_level,
                webp_lossless=webp_lossless,
                popup=popup,
            )

            # Log the save operation
            self.log_info(
                f"Saving {len(images)} images as {format} "
                f"(quality={quality if format != 'PNG' else 'N/A'}, "
                f"png_compress={png_compress_level if format == 'PNG' else 'N/A'})"
            )

            # Process and save images
            results, enhanced_data = process_image_batch(
                images=images,
                filename_prefix=filename_prefix,
                format_type=format,
                quality=quality,
                png_compress_level=png_compress_level,
                webp_lossless=webp_lossless,
                popup=popup,
                prompt=prompt,
                extra_pnginfo=extra_pnginfo,
            )

            # Log results
            total_size = sum(data["file_size"] for data in enhanced_data)
            self.log_info(
                f"Successfully saved {len(results)} images "
                f"(total size: {total_size / 1024:.1f} KB)"
            )

            # Return UI data for ComfyUI preview (clean) + enhanced data for our JS
            return {
                "ui": {
                    "images": results,  # Clean data for ComfyUI
                    "kiko_enhanced": enhanced_data,  # Enhanced data for our JavaScript
                }
            }

        except Exception as e:
            error_msg = f"Failed to save images: {str(e)}"
            self.handle_error(error_msg, e)

    def validate_inputs(
        self,
        images: torch.Tensor,
        format: str,
        quality: int,
        png_compress_level: int,
        webp_lossless: bool,
        popup: bool,
    ) -> None:
        """
        Validate inputs specific to KikoSaveImage

        Args:
            images: Image tensor batch
            format: Image format
            quality: Quality setting
            png_compress_level: PNG compression level
            webp_lossless: WebP lossless setting
            popup: Enable popup windows

        Raises:
            ValueError: If validation fails
        """
        # Use logic module validation
        validate_save_inputs(images, format, quality, png_compress_level)

        # Additional node-specific validation
        if not isinstance(webp_lossless, bool):
            raise ValueError(
                f"webp_lossless must be a boolean, got {type(webp_lossless).__name__}"
            )

        if not isinstance(popup, bool):
            raise ValueError(f"popup must be a boolean, got {type(popup).__name__}")


# Node class mappings for ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "KikoSaveImage": KikoSaveImageNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KikoSaveImage": "Kiko Save Image",
}
