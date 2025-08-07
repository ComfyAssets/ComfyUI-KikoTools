"""Logic module for Flux Sampler Params node."""

from typing import List, Dict, Any, Tuple, Optional
import random
import time
import logging

logger = logging.getLogger(__name__)


def parse_string_to_list(value: str) -> List[float]:
    """
    Parse a string containing comma-separated values to a list of floats.

    Args:
        value: String with comma-separated values

    Returns:
        List of float values
    """
    if not value or not value.strip():
        return []

    try:
        values = []
        for item in value.split(","):
            item = item.strip()
            if item:
                try:
                    values.append(float(item))
                except ValueError:
                    logger.warning(f"Could not parse '{item}' as float")
        return values
    except Exception as e:
        logger.error(f"Error parsing string to list: {e}")
        return []


def parse_seed_string(seed_string: str) -> List[int]:
    """
    Parse seed string which can contain numbers, '?', or ranges.

    Args:
        seed_string: String with seeds (e.g., "123,?,456")

    Returns:
        List of integer seeds
    """
    seeds = []

    try:
        for item in seed_string.replace("\n", ",").split(","):
            item = item.strip()
            if not item:
                continue

            if "?" in item:
                seeds.append(random.randint(0, 999999))
            else:
                try:
                    seeds.append(int(item))
                except ValueError:
                    logger.warning(f"Could not parse seed '{item}'")
                    seeds.append(random.randint(0, 999999))

        if not seeds:
            seeds = [random.randint(0, 999999)]

    except Exception as e:
        logger.error(f"Error parsing seeds: {e}")
        seeds = [random.randint(0, 999999)]

    return seeds


def parse_sampler_string(
    sampler_string: str, available_samplers: List[str]
) -> List[str]:
    """
    Parse sampler string which can contain names, '*', or '!' exclusions.

    Args:
        sampler_string: String with sampler specifications
        available_samplers: List of available sampler names

    Returns:
        List of sampler names
    """
    if sampler_string == "*":
        return available_samplers.copy()

    if sampler_string.startswith("!"):
        excluded = sampler_string.replace("\n", ",").split(",")
        excluded = [s.strip("! ") for s in excluded]
        return [s for s in available_samplers if s not in excluded]

    samplers = sampler_string.replace("\n", ",").split(",")
    samplers = [s.strip() for s in samplers if s.strip() in available_samplers]

    if not samplers:
        return ["euler"]

    return samplers


def parse_scheduler_string(
    scheduler_string: str, available_schedulers: List[str]
) -> List[str]:
    """
    Parse scheduler string which can contain names, '*', or '!' exclusions.

    Args:
        scheduler_string: String with scheduler specifications
        available_schedulers: List of available scheduler names

    Returns:
        List of scheduler names
    """
    if scheduler_string == "*":
        return available_schedulers.copy()

    if scheduler_string.startswith("!"):
        excluded = scheduler_string.replace("\n", ",").split(",")
        excluded = [s.strip("! ") for s in excluded]
        return [s for s in available_schedulers if s not in excluded]

    schedulers = scheduler_string.replace("\n", ",").split(",")
    schedulers = [s.strip() for s in schedulers if s.strip() in available_schedulers]

    if not schedulers:
        return ["simple"]

    return schedulers


def get_default_flux_params(is_schnell: bool) -> Dict[str, Any]:
    """
    Get default parameters for Flux models.

    Args:
        is_schnell: Whether this is a Schnell model

    Returns:
        Dictionary of default parameters
    """
    if is_schnell:
        return {
            "steps": 4,
            "guidance": 3.5,
            "max_shift": 0,
            "base_shift": 1.0,
        }
    else:
        return {
            "steps": 20,
            "guidance": 3.5,
            "max_shift": 1.15,
            "base_shift": 0.5,
        }


def create_batch_params(
    seeds: List[int],
    samplers: List[str],
    schedulers: List[str],
    steps: List[int],
    guidances: List[float],
    max_shifts: List[float],
    base_shifts: List[float],
    denoises: List[float],
    conditioning_count: int,
    lora_strength_count: int = 1,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Create batch parameters for all combinations.

    Returns:
        Tuple of (total_samples, list of parameter combinations)
    """
    total = (
        len(seeds)
        * len(samplers)
        * len(schedulers)
        * len(steps)
        * len(guidances)
        * len(max_shifts)
        * len(base_shifts)
        * len(denoises)
        * conditioning_count
        * lora_strength_count
    )

    params = []
    for seed in seeds:
        for sampler in samplers:
            for scheduler in schedulers:
                for step in steps:
                    for guidance in guidances:
                        for max_shift in max_shifts:
                            for base_shift in base_shifts:
                                for denoise in denoises:
                                    params.append(
                                        {
                                            "seed": seed,
                                            "sampler": sampler,
                                            "scheduler": scheduler,
                                            "steps": step,
                                            "guidance": guidance,
                                            "max_shift": max_shift,
                                            "base_shift": base_shift,
                                            "denoise": denoise,
                                        }
                                    )

    return total, params


def process_conditioning_input(
    conditioning: Any,
) -> Tuple[Optional[List[str]], List[Any]]:
    """
    Process conditioning input which can be a dict or regular conditioning.

    Args:
        conditioning: Input conditioning (dict or tensor)

    Returns:
        Tuple of (text_list, encoded_list)
    """
    if isinstance(conditioning, dict) and "encoded" in conditioning:
        return conditioning.get("text"), conditioning["encoded"]
    else:
        return None, [conditioning]


def validate_flux_params(
    steps: str, guidance: str, max_shift: str, base_shift: str, denoise: str
) -> bool:
    """
    Validate Flux sampler parameters.

    Returns:
        True if all parameters are valid
    """
    try:
        parse_string_to_list(steps)
        parse_string_to_list(guidance)
        parse_string_to_list(max_shift)
        parse_string_to_list(base_shift)
        parse_string_to_list(denoise)
        return True
    except Exception as e:
        logger.error(f"Invalid parameters: {e}")
        return False
