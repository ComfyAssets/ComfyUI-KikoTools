"""Logic module for Scheduler Select Helper node."""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

try:
    import comfy.samplers

    SCHEDULERS = comfy.samplers.KSampler.SCHEDULERS
except ImportError:
    SCHEDULERS = [
        "normal",
        "karras",
        "exponential",
        "sgm_uniform",
        "simple",
        "ddim_uniform",
        "beta",
        "linear",
        "aligned",
        "ays",
    ]


def process_scheduler_selection(**scheduler_flags: bool) -> str:
    """
    Process boolean flags for each scheduler and return selected ones.

    Args:
        **scheduler_flags: Keyword arguments where keys are scheduler names
                          and values are boolean selection states

    Returns:
        Comma-separated string of selected scheduler names
    """
    try:
        selected_schedulers = [
            scheduler_name
            for scheduler_name, is_selected in scheduler_flags.items()
            if is_selected
        ]

        if not selected_schedulers:
            logger.warning("No schedulers selected, returning empty string")
            return ""

        result = ", ".join(selected_schedulers)
        logger.info(f"Selected schedulers: {result}")
        return result

    except Exception as e:
        logger.error(f"Error processing scheduler selection: {e}")
        return ""


def validate_scheduler_names(scheduler_names: str) -> List[str]:
    """
    Validate and clean a comma-separated string of scheduler names.

    Args:
        scheduler_names: Comma-separated string of scheduler names

    Returns:
        List of valid scheduler names
    """
    if not scheduler_names:
        return []

    try:
        names = [name.strip() for name in scheduler_names.split(",")]
        valid_names = [name for name in names if name in SCHEDULERS]

        invalid_names = [name for name in names if name not in SCHEDULERS]
        if invalid_names:
            logger.warning(f"Invalid scheduler names ignored: {invalid_names}")

        return valid_names

    except Exception as e:
        logger.error(f"Error validating scheduler names: {e}")
        return []


def get_scheduler_categories() -> Dict[str, List[str]]:
    """
    Get schedulers organized by category.

    Returns:
        Dictionary mapping categories to scheduler names
    """
    categories = {
        "Standard": ["normal", "karras", "exponential", "simple"],
        "Uniform": ["sgm_uniform", "ddim_uniform"],
        "Advanced": ["beta", "linear", "aligned", "ays"],
    }

    return {
        category: [s for s in schedulers if s in SCHEDULERS]
        for category, schedulers in categories.items()
    }


def get_default_schedulers() -> List[str]:
    """
    Get a list of commonly used default schedulers.

    Returns:
        List of default scheduler names
    """
    defaults = ["normal", "karras", "exponential", "simple"]
    return [s for s in defaults if s in SCHEDULERS]


def get_scheduler_description(scheduler_name: str) -> str:
    """
    Get a description of what a scheduler does.

    Args:
        scheduler_name: Name of the scheduler

    Returns:
        Description string
    """
    descriptions = {
        "normal": "Standard linear timestep spacing",
        "karras": "Karras et al. noise schedule for improved quality",
        "exponential": "Exponential timestep spacing for smoother transitions",
        "sgm_uniform": "Stable Diffusion uniform spacing",
        "simple": "Simple linear schedule for fast sampling",
        "ddim_uniform": "DDIM-optimized uniform spacing",
        "beta": "Beta schedule with variance preservation",
        "linear": "Linear timestep reduction",
        "aligned": "Aligned schedule for consistent results",
        "ays": "Align Your Steps schedule",
    }

    return descriptions.get(scheduler_name, "Custom scheduler")
