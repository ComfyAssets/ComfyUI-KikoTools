"""Sampler Combo node for ComfyUI."""

from typing import Tuple
from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    get_sampler_combo,
    validate_sampler_settings,
    get_compatible_scheduler_suggestions,
    get_recommended_steps_range,
    get_recommended_cfg_range,
    SAMPLERS,
    SCHEDULERS,
)


class SamplerComboNode(ComfyAssetsBaseNode):
    """
    Sampler Combo node for selecting sampling configuration.

    Provides a unified interface for selecting sampler, scheduler, steps,
    and CFG settings in a single node, reducing workflow complexity and
    ensuring compatible parameter combinations.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        return {
            "required": {
                "sampler_name": (
                    SAMPLERS,
                    {
                        "default": "euler",
                        "tooltip": "Sampling algorithm",
                    },
                ),
                "scheduler": (
                    SCHEDULERS,
                    {
                        "default": "normal",
                        "tooltip": "Step distribution schedule",
                    },
                ),
                "steps": (
                    "INT",
                    {
                        "default": 20,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "tooltip": "Sampling steps (1-100)",
                    },
                ),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 7.0,
                        "min": 0.0,
                        "max": 20.0,
                        "step": 0.5,
                        "display": "slider",
                        "tooltip": "CFG scale (0-20)",
                    },
                ),
            }
        }

    RETURN_TYPES = (SAMPLERS, SCHEDULERS, "INT", "FLOAT")
    RETURN_NAMES = ("sampler_name", "scheduler", "steps", "cfg")
    FUNCTION = "get_sampler_combo"
    CATEGORY = "ComfyAssets"

    def get_sampler_combo(
        self, sampler_name: str, scheduler: str, steps: int, cfg: float
    ) -> Tuple[str, str, int, float]:
        """
        Get sampler combo configuration.

        Args:
            sampler_name: The sampler algorithm name
            scheduler: The scheduler algorithm name
            steps: Number of sampling steps
            cfg: CFG scale value

        Returns:
            Tuple of (sampler_name, scheduler, steps, cfg)
        """
        try:
            # Validate inputs
            if not validate_sampler_settings(sampler_name, scheduler, steps, cfg):
                # Log the validation error but don't raise
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"{self.__class__.__name__}: Invalid sampler settings: "
                    f"sampler={sampler_name}, scheduler={scheduler}, "
                    f"steps={steps}, cfg={cfg}. "
                    f"Using safe defaults: euler, normal, 20 steps, CFG 7.0"
                )
                return ("euler", "normal", 20, 7.0)

            # Process and return the combo
            result = get_sampler_combo(sampler_name, scheduler, steps, cfg)

            self.log_info(
                f"Configured sampler combo: {result[0]}, {result[1]}, "
                f"{result[2]} steps, CFG {result[3]}"
            )

            return result

        except Exception as e:
            # Handle any unexpected errors gracefully
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"{self.__class__.__name__}: Error processing sampler combo: {str(e)}. "
                f"Using safe defaults: euler, normal, 20 steps, CFG 7.0"
            )
            return ("euler", "normal", 20, 7.0)

    def validate_inputs(
        self, sampler_name: str, scheduler: str, steps: int, cfg: float
    ) -> None:
        """
        Validate sampler combo inputs.

        Args:
            sampler_name: The sampler algorithm name
            scheduler: The scheduler algorithm name
            steps: Number of sampling steps
            cfg: CFG scale value

        Raises:
            ValueError: If validation fails
        """
        if not validate_sampler_settings(sampler_name, scheduler, steps, cfg):
            self.handle_error(
                f"Invalid sampler settings: sampler={sampler_name}, "
                f"scheduler={scheduler}, steps={steps}, cfg={cfg}"
            )

    def get_scheduler_suggestions(self, sampler_name: str) -> list:
        """
        Get scheduler suggestions compatible with the selected sampler.

        Args:
            sampler_name: The sampler algorithm name

        Returns:
            List of recommended scheduler names
        """
        return get_compatible_scheduler_suggestions(sampler_name)

    def get_steps_recommendation(self, sampler_name: str) -> dict:
        """
        Get steps recommendation for the selected sampler.

        Args:
            sampler_name: The sampler algorithm name

        Returns:
            Dictionary with min, max, and default steps
        """
        min_steps, max_steps, default_steps = get_recommended_steps_range(sampler_name)
        return {
            "min": min_steps,
            "max": max_steps,
            "default": default_steps,
            "recommendation": f"Range: {min_steps}-{max_steps} steps",
        }

    def get_cfg_recommendation(self, sampler_name: str) -> dict:
        """
        Get CFG recommendation for the selected sampler.

        Args:
            sampler_name: The sampler algorithm name

        Returns:
            Dictionary with min, max, and default CFG values
        """
        min_cfg, max_cfg, default_cfg = get_recommended_cfg_range(sampler_name)
        return {
            "min": min_cfg,
            "max": max_cfg,
            "default": default_cfg,
            "recommendation": f"Recommended range: {min_cfg}-{max_cfg} CFG",
        }

    def get_combo_analysis(
        self, sampler_name: str, scheduler: str, steps: int, cfg: float
    ) -> dict:
        """
        Analyze the sampler combo configuration and provide recommendations.

        Args:
            sampler_name: The sampler algorithm name
            scheduler: The scheduler algorithm name
            steps: Number of sampling steps
            cfg: CFG scale value

        Returns:
            Dictionary containing analysis and recommendations
        """
        analysis = {
            "sampler": sampler_name,
            "scheduler": scheduler,
            "steps": steps,
            "cfg": cfg,
            "valid": validate_sampler_settings(sampler_name, scheduler, steps, cfg),
            "scheduler_suggestions": self.get_scheduler_suggestions(sampler_name),
            "steps_rec": self.get_steps_recommendation(sampler_name),
            "cfg_rec": self.get_cfg_recommendation(sampler_name),
        }

        # Add compatibility assessment
        suggested_schedulers = self.get_scheduler_suggestions(sampler_name)
        analysis["scheduler_compatible"] = scheduler in suggested_schedulers

        # Add performance assessment
        steps_rec = self.get_steps_recommendation(sampler_name)
        analysis["steps_optimal"] = steps_rec["min"] <= steps <= steps_rec["max"]

        cfg_rec = self.get_cfg_recommendation(sampler_name)
        analysis["cfg_optimal"] = cfg_rec["min"] <= cfg <= cfg_rec["max"]

        return analysis

    @classmethod
    def get_available_samplers(cls) -> list:
        """
        Get list of available samplers.

        Returns:
            List of sampler names
        """
        return list(SAMPLERS)

    @classmethod
    def get_available_schedulers(cls) -> list:
        """
        Get list of available schedulers.

        Returns:
            List of scheduler names
        """
        return list(SCHEDULERS)

    def __str__(self) -> str:
        """String representation of the node."""
        return (
            f"SamplerComboNode(samplers={len(SAMPLERS)}, "
            f"schedulers={len(SCHEDULERS)})"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the node."""
        return (
            f"SamplerComboNode("
            f"samplers={len(SAMPLERS)}, "
            f"schedulers={len(SCHEDULERS)}, "
            f"category='{self.CATEGORY}', "
            f"function='{self.FUNCTION}'"
            f")"
        )
