"""Plot Parameters node for ComfyUI."""

from typing import Tuple, Any, List, Dict
import os
import math
import torch
import torch.nn.functional as F
import logging
from PIL import Image, ImageDraw, ImageFont

try:
    import torchvision.transforms.v2 as T
except ImportError:
    try:
        import torchvision.transforms as T
    except ImportError:
        # Fallback for test environment without torchvision
        class T:
            @staticmethod
            def ToTensor():
                def to_tensor(img):
                    import numpy as np

                    if isinstance(img, Image.Image):
                        img = np.array(img)
                    img = torch.from_numpy(img).float() / 255.0
                    if len(img.shape) == 3:
                        img = img.permute(2, 0, 1)
                    return img

                return to_tensor


from ....base.base_node import ComfyAssetsBaseNode
from .logic import (
    sort_parameters,
    group_by_value,
    filter_changing_params,
    format_parameter_text,
    wrap_prompt_text,
    calculate_text_dimensions,
    calculate_grid_dimensions,
    validate_plot_parameters,
)

logger = logging.getLogger(__name__)


class PlotParametersNode(ComfyAssetsBaseNode):
    """
    Plot Parameters node for visualizing batch sampling results.

    Creates a grid layout of images with parameter annotations,
    useful for comparing results across different sampling parameters.
    Supports sorting, grouping, and filtering display options.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        order_options = [
            "none",
            "time",
            "seed",
            "steps",
            "denoise",
            "sampler",
            "scheduler",
            "guidance",
            "max_shift",
            "base_shift",
            "lora_strength",
        ]

        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "Batch of images to arrange"}),
                "params": (
                    "SAMPLER_PARAMS",
                    {"tooltip": "Parameters from FluxSamplerParams"},
                ),
                "order_by": (
                    order_options,
                    {"default": "none", "tooltip": "Sort images by this parameter"},
                ),
                "cols_value": (
                    order_options,
                    {
                        "default": "none",
                        "tooltip": "Group into columns by this parameter",
                    },
                ),
                "cols_num": (
                    "INT",
                    {
                        "default": -1,
                        "min": -1,
                        "max": 1024,
                        "tooltip": "Number of columns (-1 for auto, 0 for square)",
                    },
                ),
                "add_prompt": (
                    ["false", "true", "excerpt"],
                    {"default": "false", "tooltip": "Add prompt text to images"},
                ),
                "add_params": (
                    ["false", "true", "changes only"],
                    {"default": "true", "tooltip": "Add parameter text to images"},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "plot_parameters"
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def plot_parameters(
        self,
        images: torch.Tensor,
        params: List[Dict[str, Any]],
        order_by: str,
        cols_value: str,
        cols_num: int,
        add_prompt: str,
        add_params: str,
    ) -> Tuple[torch.Tensor]:
        """
        Create a plot grid with parameter annotations.

        Args:
            images: Tensor of images [B, H, W, C]
            params: List of parameter dictionaries
            order_by: Parameter to sort by
            cols_value: Parameter to group columns by
            cols_num: Number of columns
            add_prompt: Whether to add prompt text
            add_params: Whether to add parameter text

        Returns:
            Tuple containing the plotted image grid
        """
        try:
            if not validate_plot_parameters(
                images.shape, len(params), order_by, cols_value, cols_num
            ):
                self.handle_error("Invalid plot parameters configuration")

            # Copy params to avoid modifying original
            _params = params.copy()

            # Sort if requested
            if order_by != "none":
                _params, indices = sort_parameters(_params, order_by)
                images = images[torch.tensor(indices)]
                self.log_info(f"Sorted by {order_by}")

            # Group by value if requested
            if cols_value != "none" and cols_num > -1:
                _params, indices, num_groups = group_by_value(_params, cols_value)
                if num_groups > 0:
                    cols_num = num_groups
                    images = images[torch.tensor(indices)]
                    self.log_info(f"Grouped into {num_groups} columns by {cols_value}")
            elif cols_num == 0:
                # Auto square layout
                cols_num = int(math.sqrt(images.shape[0]))
                cols_num = max(1, min(cols_num, 1024))

            # Filter params if showing changes only
            if add_params == "changes only":
                _params = filter_changing_params(_params)

            # Get font
            font_path = self._get_font_path()
            width = images.shape[2]
            font_size = min(48, int(32 * (width / 1024)))

            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                logger.warning(f"Could not load font from {font_path}, using default")
                font = ImageFont.load_default()

            # Calculate text dimensions
            text_padding = 3
            line_height = (
                font.getmask("Q").getbbox()[3] + font.getmetrics()[1] + text_padding * 2
            )
            char_width = font.getbbox("M")[2] + 1  # Monospace approximation

            # Process each image
            out_images = []
            for image, param in zip(images, _params):
                image = image.permute(2, 0, 1)  # [C, H, W]

                # Add parameter text
                if add_params != "false":
                    param_text = format_parameter_text(
                        param,
                        "changes only" if add_params == "changes only" else "full",
                    )

                    lines = param_text.split("\n")
                    text_height = line_height * len(lines)
                    text_image = Image.new("RGB", (width, text_height), color=(0, 0, 0))
                    draw = ImageDraw.Draw(text_image)

                    for i, line in enumerate(lines):
                        draw.text(
                            (text_padding, i * line_height + text_padding),
                            line,
                            font=font,
                            fill=(255, 255, 255),
                        )

                    text_tensor = T.ToTensor()(text_image).to(image.device)
                    image = torch.cat([image, text_tensor], 1)

                # Add prompt text
                if add_prompt != "false" and "prompt" in param and param["prompt"]:
                    cols = math.ceil(width / char_width)
                    prompt_lines = wrap_prompt_text(
                        param["prompt"],
                        cols,
                        "excerpt" if add_prompt == "excerpt" else "full",
                    )

                    prompt_height = line_height * len(prompt_lines)
                    prompt_image = Image.new(
                        "RGB", (width, prompt_height), color=(0, 0, 0)
                    )
                    draw = ImageDraw.Draw(prompt_image)

                    for i, line in enumerate(prompt_lines):
                        draw.text(
                            (text_padding, i * line_height + text_padding),
                            line,
                            font=font,
                            fill=(255, 255, 255),
                        )

                    prompt_tensor = T.ToTensor()(prompt_image).to(image.device)
                    image = torch.cat([image, prompt_tensor], 1)

                # Clean up NaN values
                image = torch.nan_to_num(image, nan=0.0).clamp(0.0, 1.0)
                out_images.append(image)

            # Ensure all images have same height
            if add_prompt != "false" or add_params == "changes only":
                max_height = max([img.shape[1] for img in out_images])
                out_images = [
                    F.pad(img, (0, 0, 0, max_height - img.shape[1]))
                    for img in out_images
                ]

            # Stack images
            out_image = torch.stack(out_images, 0).permute(0, 2, 3, 1)  # [B, H, W, C]

            # Create grid if columns specified
            if cols_num > -1:
                rows, cols = calculate_grid_dimensions(out_image.shape[0], cols_num)
                b, h, w, c = out_image.shape

                # Pad if necessary
                if b % cols != 0:
                    padding = cols - (b % cols)
                    out_image = F.pad(out_image, (0, 0, 0, 0, 0, 0, 0, padding))
                    b = out_image.shape[0]

                # Reshape into grid
                out_image = out_image.reshape(rows, cols, h, w, c)
                out_image = out_image.permute(0, 2, 1, 3, 4)  # [rows, h, cols, w, c]
                out_image = out_image.reshape(rows * h, cols * w, c).unsqueeze(0)

                self.log_info(f"Created {rows}x{cols} grid")

            return (out_image,)

        except Exception as e:
            self.handle_error(f"Error creating parameter plot: {str(e)}", e)
            return (images,)

    def _get_font_path(self) -> str:
        """
        Get the path to the font file.

        Returns:
            Path to font file
        """
        # Try to find a monospace font
        possible_paths = [
            # Check if ComfyUI_essentials font exists
            os.path.join(
                os.path.dirname(__file__),
                "../../../../referance/ComfyUI_essentials/fonts/ShareTechMono-Regular.ttf",
            ),
            # System fonts
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/System/Library/Fonts/Courier.dfont",
            "C:\\Windows\\Fonts\\cour.ttf",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Return a default that PIL will handle
        return "arial.ttf"
