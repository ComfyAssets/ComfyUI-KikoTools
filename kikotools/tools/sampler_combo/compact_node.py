"""Compact Sampler Combo node for ComfyUI with minimal interface."""

from typing import Tuple
from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    get_sampler_combo,
    SAMPLERS,
    SCHEDULERS,
)


class SamplerComboCompactNode(ComfyAssetsBaseNode):
    """
    Compact Sampler Combo node with minimal interface.

    Provides essential sampling parameters in a space-efficient layout
    with shorter parameter names and reduced visual footprint.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define compact input types for the ComfyUI node."""
        return {
            "required": {
                "sampler": (
                    SAMPLERS,
                    {
                        "default": "euler",
                        "tooltip": "Sampler",
                    },
                ),
                "sched": (
                    SCHEDULERS,
                    {
                        "default": "normal",
                        "tooltip": "Scheduler",
                    },
                ),
                "steps": (
                    "INT",
                    {
                        "default": 20,
                        "min": 1,
                        "max": 50,
                        "step": 1,
                        "tooltip": "Steps",
                    },
                ),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 7.0,
                        "min": 1.0,
                        "max": 15.0,
                        "step": 0.5,
                        "display": "slider",
                        "tooltip": "CFG",
                    },
                ),
            }
        }

    RETURN_TYPES = ("SAMPLER", SCHEDULERS, "INT", "FLOAT")
    RETURN_NAMES = ("sampler", "scheduler", "steps", "cfg")
    FUNCTION = "get_combo"
    CATEGORY = "ComfyAssets"

    def get_combo(self, sampler: str, sched: str, steps: int, cfg: float) -> Tuple[object, str, int, float]:
        """
        Get compact sampler combo configuration.

        Args:
            sampler: The sampler algorithm name
            sched: The scheduler algorithm name
            steps: Number of sampling steps
            cfg: CFG scale value

        Returns:
            Tuple of (sampler_object, scheduler, steps, cfg)
        """
        try:
            # Use the same validation logic but with compact interface
            result = get_sampler_combo(sampler, sched, steps, cfg)
            # Create the sampler object
            try:
                import comfy.samplers

                sampler_obj = comfy.samplers.sampler_object(result[0])
            except ImportError:
                # Return sampler name for testing
                sampler_obj = result[0]
            return (sampler_obj, result[1], result[2], result[3])

        except Exception as e:
            # Graceful fallback
            self.handle_error(f"Error in compact combo: {str(e)}")
            try:
                import comfy.samplers

                sampler_obj = comfy.samplers.sampler_object("euler")
            except ImportError:
                # Return sampler name for testing
                sampler_obj = "euler"
            return (sampler_obj, "normal", 20, 7.0)

    def __str__(self) -> str:
        """String representation of the compact node."""
        return "SamplerComboCompactNode"

    def __repr__(self) -> str:
        """Detailed string representation of the compact node."""
        return f"SamplerComboCompactNode(category='{self.CATEGORY}')"
