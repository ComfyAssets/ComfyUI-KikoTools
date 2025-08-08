import torch
from typing import Dict, Any, Tuple

from ...base import ComfyAssetsBaseNode
from .logic import apply_film_grain


class KikoFilmGrainNode(ComfyAssetsBaseNode):
    """
    Apply realistic film grain effect to images.

    This node simulates the grain patterns found in analog film photography.
    It provides controls for grain size, intensity, color saturation, and
    shadow lifting (toe) to achieve various film looks.

    Improvements over reference implementation:
    - More efficient PyTorch-based blur operations
    - Better memory management for large batches
    - Preserves alpha channel when present
    - Improved grain mixing algorithm
    - ITU-R BT.709 color space conversion
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "image": ("IMAGE",),
                "scale": (
                    "FLOAT",
                    {
                        "default": 0.5,
                        "min": 0.25,
                        "max": 2.0,
                        "step": 0.05,
                        "display": "slider",
                        "description": "Grain size - smaller values create finer grain",
                    },
                ),
                "strength": (
                    "FLOAT",
                    {
                        "default": 0.5,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.01,
                        "display": "slider",
                        "description": "Intensity of the grain effect",
                    },
                ),
                "saturation": (
                    "FLOAT",
                    {
                        "default": 0.7,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.01,
                        "display": "slider",
                        "description": "Color saturation of the grain (0=monochrome)",
                    },
                ),
                "toe": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": -0.2,
                        "max": 0.5,
                        "step": 0.001,
                        "display": "slider",
                        "description": "Lift blacks/shadows for a film-like look",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "description": "Random seed for grain pattern generation",
                    },
                ),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "apply_grain"
    CATEGORY = "ComfyAssets/image"
    DESCRIPTION = "Apply realistic film grain effect with customizable parameters"

    def apply_grain(
        self,
        image: torch.Tensor,
        scale: float,
        strength: float,
        saturation: float,
        toe: float,
        seed: int,
    ) -> Tuple[torch.Tensor]:
        """
        Apply film grain effect to the input image.

        Args:
            image: Input image tensor [B, H, W, C]
            scale: Grain size factor (0.25-2.0)
            strength: Grain intensity (0.0-10.0)
            saturation: Color saturation of grain (0.0-2.0)
            toe: Shadow lifting amount (-0.2-0.5)
            seed: Random seed for reproducibility

        Returns:
            Tuple containing the processed image tensor
        """
        result = apply_film_grain(
            image=image,
            scale=scale,
            strength=strength,
            saturation=saturation,
            toe=toe,
            seed=seed,
        )

        return (result,)
