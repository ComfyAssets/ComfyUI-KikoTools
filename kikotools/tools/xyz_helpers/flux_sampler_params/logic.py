"""Logic module for Flux Sampler Params node."""

from typing import List, Dict, Any, Tuple, Optional
import math
import random
import logging

logger = logging.getLogger(__name__)


RANDOM_SEED_TOKEN = "?"
MAX_RANDOM_SEED = 999999


def parse_string_to_list(value: str, field: str = "value") -> List[float]:
    """
    Parse a string containing comma-separated values to a list of floats.

    Args:
        value: String with comma-separated values
        field: Name of the input, used in error messages

    Returns:
        List of float values (empty when the string is blank)

    Raises:
        ValueError: If any token is not a finite number
    """
    if not value or not value.strip():
        return []

    values = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            number = float(item)
        except ValueError:
            raise ValueError(f"Invalid {field} value '{item}': expected a number")
        if not math.isfinite(number):
            raise ValueError(f"Invalid {field} value '{item}': must be finite")
        values.append(number)
    return values


def parse_steps_list(value: str, field: str = "steps") -> List[int]:
    """
    Parse comma-separated step counts into positive integers.

    Raises:
        ValueError: If a token is not a positive whole number
    """
    steps = []
    for number in parse_string_to_list(value, field):
        if number != int(number) or number < 1:
            raise ValueError(
                f"Invalid {field} value '{number:g}': expected a positive integer"
            )
        steps.append(int(number))
    return steps


def parse_seed_string(seed_string: str) -> List[int]:
    """
    Parse a seed string of comma or newline separated tokens.

    Each token is either a non-negative integer or the exact token '?',
    which draws a random seed. A blank string yields one random seed.
    Ranges are not supported.

    Raises:
        ValueError: If a token is neither an integer nor '?'
    """
    seeds = []
    for item in seed_string.replace("\n", ",").split(","):
        item = item.strip()
        if not item:
            continue
        if item == RANDOM_SEED_TOKEN:
            seeds.append(random.randint(0, MAX_RANDOM_SEED))
            continue
        try:
            seed = int(item)
        except ValueError:
            raise ValueError(
                f"Invalid seed '{item}': use whole numbers or '?' for a random seed"
            )
        if seed < 0:
            raise ValueError(f"Invalid seed '{item}': seeds cannot be negative")
        seeds.append(seed)

    if not seeds:
        seeds = [random.randint(0, MAX_RANDOM_SEED)]
    return seeds


def seed_string_is_random(seed_string: str) -> bool:
    """Return True if the seed string produces a different result each run."""
    tokens = [t.strip() for t in seed_string.replace("\n", ",").split(",")]
    tokens = [t for t in tokens if t]
    return not tokens or RANDOM_SEED_TOKEN in tokens


def is_schnell_model(model: Any) -> bool:
    """
    Detect Flux Schnell from the unet config.

    Schnell is not guidance distilled (guidance_embed is False) while dev is
    (guidance_embed is True). Anything unrecognised is treated as dev.
    """
    config = getattr(
        getattr(getattr(model, "model", None), "model_config", None),
        "unet_config",
        None,
    )
    if not isinstance(config, dict):
        return False
    return config.get("guidance_embed") is False


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

    Raises:
        ValueError: Naming the offending field and token
    """
    parse_steps_list(steps, "steps")
    parse_string_to_list(guidance, "guidance")
    parse_string_to_list(max_shift, "max_shift")
    parse_string_to_list(base_shift, "base_shift")
    parse_string_to_list(denoise, "denoise")
    return True
