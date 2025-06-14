"""Logic module for Sampler Combo node."""

from typing import Tuple, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Import ComfyUI samplers - will be available when running in ComfyUI
try:
    import comfy.samplers

    SAMPLERS = comfy.samplers.KSampler.SAMPLERS
    SCHEDULERS = comfy.samplers.KSampler.SCHEDULERS
except ImportError:
    # Fallback for testing/development environment
    SAMPLERS = [
        "euler",
        "euler_ancestral",
        "heun",
        "dpm_2",
        "dpm_2_ancestral",
        "lms",
        "dpm_fast",
        "dpm_adaptive",
        "dpmpp_2s_ancestral",
        "dpmpp_sde",
        "dpmpp_2m",
        "ddim",
        "uni_pc",
        "uni_pc_bh2",
    ]
    SCHEDULERS = [
        "normal",
        "karras",
        "exponential",
        "sgm_uniform",
        "simple",
        "ddim_uniform",
        "beta",
    ]


def validate_sampler_settings(
    sampler_name: str, scheduler: str, steps: int, cfg: float
) -> bool:
    """
    Validate sampler configuration settings.

    Args:
        sampler_name: The sampler algorithm name
        scheduler: The scheduler algorithm name
        steps: Number of sampling steps
        cfg: CFG (classifier-free guidance) scale value

    Returns:
        True if all settings are valid
    """
    try:
        # Validate sampler
        if sampler_name not in SAMPLERS:
            logger.error(f"Invalid sampler: {sampler_name}")
            return False

        # Validate scheduler
        if scheduler not in SCHEDULERS:
            logger.error(f"Invalid scheduler: {scheduler}")
            return False

        # Validate steps
        if not isinstance(steps, int) or steps < 1 or steps > 1000:
            logger.error(f"Invalid steps: {steps} (must be 1-1000)")
            return False

        # Validate CFG
        if not isinstance(cfg, (int, float)) or cfg < 0 or cfg > 30:
            logger.error(f"Invalid CFG: {cfg} (must be 0-30)")
            return False

        return True

    except Exception as e:
        logger.error(f"Error validating sampler settings: {e}")
        return False


def get_sampler_combo(
    sampler_name: str, scheduler: str, steps: int, cfg: float
) -> Tuple[str, str, int, float]:
    """
    Process and return sampler combo settings.

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
            # Return safe defaults if validation fails
            logger.warning("Invalid settings provided, using safe defaults")
            return ("euler", "normal", 20, 7.0)

        # Sanitize values
        steps = max(1, min(1000, int(steps)))
        cfg = max(0.0, min(30.0, float(cfg)))

        return (sampler_name, scheduler, steps, cfg)

    except Exception as e:
        logger.error(f"Error processing sampler combo: {e}")
        # Return safe defaults on any error
        return ("euler", "normal", 20, 7.0)


def get_compatible_scheduler_suggestions(sampler_name: str) -> List[str]:
    """
    Get scheduler suggestions that work well with specific samplers.

    Args:
        sampler_name: The sampler algorithm name

    Returns:
        List of recommended scheduler names
    """
    # Scheduler compatibility recommendations
    compatibility_map = {
        "euler": ["normal", "simple", "sgm_uniform"],
        "euler_ancestral": ["normal", "karras", "exponential"],
        "heun": ["normal", "karras"],
        "dpm_2": ["normal", "karras"],
        "dpm_2_ancestral": ["normal", "karras", "exponential"],
        "dpmpp_2s_ancestral": ["normal", "karras", "exponential"],
        "dpmpp_sde": ["normal", "karras", "exponential"],
        "dpmpp_2m": ["normal", "karras", "sgm_uniform"],
        "ddim": ["ddim_uniform", "normal"],
        "uni_pc": ["normal", "sgm_uniform"],
        "uni_pc_bh2": ["normal", "sgm_uniform"],
    }

    return compatibility_map.get(sampler_name, ["normal", "karras"])


def get_recommended_steps_range(sampler_name: str) -> Tuple[int, int, int]:
    """
    Get recommended steps range for specific samplers.

    Args:
        sampler_name: The sampler algorithm name

    Returns:
        Tuple of (min_steps, max_steps, default_steps)
    """
    # Steps recommendations by sampler
    steps_map = {
        "euler": (10, 30, 20),
        "euler_ancestral": (15, 40, 25),
        "heun": (10, 25, 15),
        "dpm_2": (10, 30, 22),
        "dpm_2_ancestral": (15, 35, 25),
        "dpmpp_2s_ancestral": (15, 40, 28),
        "dpmpp_sde": (15, 35, 25),
        "dpmpp_2m": (15, 30, 20),
        "ddim": (20, 50, 30),
        "uni_pc": (10, 25, 15),
        "uni_pc_bh2": (10, 25, 15),
    }

    return steps_map.get(sampler_name, (10, 50, 20))


def get_recommended_cfg_range(sampler_name: str) -> Tuple[float, float, float]:
    """
    Get recommended CFG range for specific samplers.

    Args:
        sampler_name: The sampler algorithm name

    Returns:
        Tuple of (min_cfg, max_cfg, default_cfg)
    """
    # CFG recommendations by sampler
    cfg_map = {
        "euler": (3.0, 15.0, 7.0),
        "euler_ancestral": (5.0, 20.0, 8.0),
        "heun": (3.0, 12.0, 6.0),
        "dpm_2": (4.0, 15.0, 7.5),
        "dpm_2_ancestral": (5.0, 18.0, 8.5),
        "dpmpp_2s_ancestral": (6.0, 20.0, 9.0),
        "dpmpp_sde": (5.0, 18.0, 8.0),
        "dpmpp_2m": (4.0, 15.0, 7.0),
        "ddim": (3.0, 12.0, 6.0),
        "uni_pc": (3.0, 12.0, 6.5),
        "uni_pc_bh2": (3.0, 12.0, 6.5),
    }

    return cfg_map.get(sampler_name, (1.0, 20.0, 7.0))


def get_sampler_info() -> Dict[str, Any]:
    """
    Get information about available samplers and schedulers.

    Returns:
        Dictionary containing sampler/scheduler information
    """
    return {
        "samplers": SAMPLERS,
        "schedulers": SCHEDULERS,
        "sampler_count": len(SAMPLERS),
        "scheduler_count": len(SCHEDULERS),
        "default_sampler": "euler",
        "default_scheduler": "normal",
        "default_steps": 20,
        "default_cfg": 7.0,
    }
