"""
Resolution Calculator ComfyUI Node
Provides ComfyUI interface for calculating upscaled dimensions
"""

import torch
from typing import Dict, Any, Tuple, Optional

from ...base import ComfyAssetsBaseNode
from .logic import calculate_resolution_from_input


class ResolutionCalculatorNode(ComfyAssetsBaseNode):
    """
    ComfyUI node for calculating upscaled resolution from image or latent inputs

    Inputs:
        - scale_factor (FLOAT): Scaling factor (1.0 to 8.0)
        - image (IMAGE, optional): Input image tensor
        - latent (LATENT, optional): Input latent tensor

    Outputs:
        - width (INT): Calculated width
        - height (INT): Calculated height
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """
        Define ComfyUI input interface

        Returns:
            Dict with required and optional input specifications
        """
        return {
            "required": {
                "scale_factor": (
                    "FLOAT",
                    {
                        "default": 2.0,
                        "min": 0.1,
                        "max": 8.0,
                        "step": 0.1,
                        "display": "slider",
                        "tooltip": "Factor to scale the resolution by "
                        "(e.g., 2.0 for 2x, 0.5 for half scale)",
                    },
                ),
            },
            "optional": {
                "image": (
                    "IMAGE",
                    {"tooltip": "Input image to calculate dimensions from"},
                ),
                "latent": (
                    "LATENT",
                    {"tooltip": "Input latent to calculate dimensions from"},
                ),
            },
        }

    RETURN_TYPES = ("INT", "INT")
    CATEGORY = "ComfyAssets/🖼️ Resolution"
    RETURN_NAMES = ("width", "height")
    FUNCTION = "calculate_resolution"

    def calculate_resolution(
        self,
        scale_factor: float,
        image: Optional[torch.Tensor] = None,
        latent: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Tuple[int, int]:
        """
        Calculate upscaled resolution from input tensor and scale factor

        Args:
            scale_factor: Scaling factor to apply
            image: Optional IMAGE tensor [batch, height, width, channels]
            latent: Optional LATENT dict with 'samples' tensor

        Returns:
            Tuple of (width, height) as integers, both divisible by 8

        Raises:
            ValueError: If validation fails or no input provided
        """
        try:
            # Validate inputs using base class
            self.validate_inputs(scale_factor=scale_factor, image=image, latent=latent)

            # Log the operation
            input_type = (
                "IMAGE"
                if image is not None
                else "LATENT" if latent is not None else "NONE"
            )
            self.log_info(
                f"Calculating resolution with scale_factor={scale_factor}, "
                f"input_type={input_type}"
            )

            # Calculate the resolution
            width, height = calculate_resolution_from_input(
                scale_factor=scale_factor, image=image, latent=latent
            )

            # Log the result
            self.log_info(f"Calculated resolution: {width}x{height}")

            return width, height

        except Exception as e:
            # Handle and re-raise with context
            error_msg = f"Failed to calculate resolution: {str(e)}"
            self.handle_error(error_msg, e)

    def validate_inputs(
        self,
        scale_factor: float,
        image: Optional[torch.Tensor] = None,
        latent: Optional[Dict[str, torch.Tensor]] = None,
    ) -> None:
        """
        Validate inputs specific to resolution calculator

        Args:
            scale_factor: Scale factor to validate
            image: Optional image tensor
            latent: Optional latent dict

        Raises:
            ValueError: If validation fails
        """
        # Check that at least one input is provided
        if image is None and latent is None:
            raise ValueError("Either 'image' or 'latent' input must be provided")

        # Validate scale factor type
        if not isinstance(scale_factor, (int, float)):
            raise ValueError(
                f"scale_factor must be a number, got {type(scale_factor).__name__}"
            )

        # Validate tensors using helper methods
        if image is not None:
            self._validate_image_tensor(image)

        if latent is not None:
            self._validate_latent_dict(latent)

    def _validate_image_tensor(self, image: torch.Tensor) -> None:
        """Validate image tensor format"""
        if not isinstance(image, torch.Tensor):
            raise ValueError(
                f"image must be a torch.Tensor, got {type(image).__name__}"
            )

        if len(image.shape) != 4:
            raise ValueError(
                f"image tensor must have 4 dimensions "
                f"[batch, height, width, channels], got {len(image.shape)}"
            )

    def _validate_latent_dict(self, latent: Dict[str, torch.Tensor]) -> None:
        """Validate latent dictionary format"""
        if not isinstance(latent, dict):
            raise ValueError(f"latent must be a dict, got {type(latent).__name__}")

        if "samples" not in latent:
            raise ValueError("latent dict must contain 'samples' key")

        samples = latent["samples"]
        if not isinstance(samples, torch.Tensor):
            raise ValueError(
                f"latent['samples'] must be a torch.Tensor, "
                f"got {type(samples).__name__}"
            )

        if len(samples.shape) != 4:
            raise ValueError(
                f"latent samples tensor must have 4 dimensions "
                f"[batch, channels, height, width], got {len(samples.shape)}"
            )


# Node class mappings for ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "ResolutionCalculator": ResolutionCalculatorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionCalculator": "Resolution Calculator",
}
