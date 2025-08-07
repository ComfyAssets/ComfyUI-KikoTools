"""Logic module for Plot Parameters node."""

from typing import List, Dict, Any, Tuple, Optional
import math
import textwrap
import logging
import torch

logger = logging.getLogger(__name__)


def sort_parameters(params: List[Dict], order_by: str) -> Tuple[List[Dict], List[int]]:
    """
    Sort parameters by a specified key.

    Args:
        params: List of parameter dictionaries
        order_by: Key to sort by

    Returns:
        Tuple of (sorted_params, original_indices)
    """
    if order_by == "none":
        return params, list(range(len(params)))

    try:
        # Create indexed list
        indexed_params = [(i, p) for i, p in enumerate(params)]

        # Sort by the specified key
        sorted_indexed = sorted(indexed_params, key=lambda x: x[1].get(order_by, 0))

        # Extract sorted params and indices
        indices = [i for i, _ in sorted_indexed]
        sorted_params = [p for _, p in sorted_indexed]

        return sorted_params, indices
    except Exception as e:
        logger.error(f"Error sorting parameters: {e}")
        return params, list(range(len(params)))


def group_by_value(
    params: List[Dict], group_key: str
) -> Tuple[List[Dict], List[int], int]:
    """
    Group parameters by a specific value and arrange in columns.

    Args:
        params: List of parameter dictionaries
        group_key: Key to group by

    Returns:
        Tuple of (rearranged_params, indices, num_groups)
    """
    if group_key == "none":
        return params, list(range(len(params))), -1

    try:
        # Group parameters by the specified key
        groups = {}
        for i, p in enumerate(params):
            value = p.get(group_key, "unknown")
            if value not in groups:
                groups[value] = []
            groups[value].append((i, p))

        num_groups = len(groups)

        # Rearrange for column layout
        sorted_params = []
        indices = []

        # Convert groups to list
        group_lists = list(groups.values())

        # Zip groups together for column arrangement
        max_len = max(len(g) for g in group_lists)
        for i in range(max_len):
            for group in group_lists:
                if i < len(group):
                    idx, param = group[i]
                    indices.append(idx)
                    sorted_params.append(param)

        return sorted_params, indices, num_groups

    except Exception as e:
        logger.error(f"Error grouping parameters: {e}")
        return params, list(range(len(params))), -1


def identify_changing_parameters(params: List[Dict]) -> Dict[str, bool]:
    """
    Identify which parameters change across the batch.

    Args:
        params: List of parameter dictionaries

    Returns:
        Dictionary mapping parameter names to whether they change
    """
    if not params:
        return {}

    changing = {}

    # Track unique values for each parameter
    value_tracker = {}

    for p in params:
        for key, value in p.items():
            if key == "time":  # Skip time as it always changes
                continue

            if key not in value_tracker:
                value_tracker[key] = set()

            # Handle different value types
            if isinstance(value, (list, tuple)):
                value = str(value)
            elif isinstance(value, dict):
                value = str(sorted(value.items()))

            value_tracker[key].add(value)

    # Mark parameters as changing if they have multiple values
    for key, values in value_tracker.items():
        changing[key] = len(values) > 1

    # Always include prompt if present
    if any("prompt" in p for p in params):
        changing["prompt"] = True

    return changing


def filter_changing_params(params: List[Dict]) -> List[Dict]:
    """
    Filter parameters to only show those that change.

    Args:
        params: List of parameter dictionaries

    Returns:
        List of filtered parameter dictionaries
    """
    changing = identify_changing_parameters(params)

    filtered = []
    for p in params:
        filtered_param = {}
        for key, value in p.items():
            if changing.get(key, False):
                filtered_param[key] = value
        filtered.append(filtered_param)

    return filtered


def format_parameter_text(param: Dict, mode: str = "full") -> str:
    """
    Format parameter dictionary as display text.

    Args:
        param: Parameter dictionary
        mode: Display mode ("full", "changes only")

    Returns:
        Formatted text string
    """
    if mode == "changes only":
        lines = []
        for key, value in param.items():
            if key != "prompt":
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    else:
        # Full format
        lines = []

        # First line: time, seed, steps, size
        if "time" in param:
            lines.append(
                f"time: {param['time']:.2f}s, seed: {param.get('seed', 'N/A')}, "
                f"steps: {param.get('steps', 'N/A')}, "
                f"size: {param.get('width', 'N/A')}×{param.get('height', 'N/A')}"
            )

        # Second line: denoise, sampler, scheduler
        lines.append(
            f"denoise: {param.get('denoise', 'N/A')}, "
            f"sampler: {param.get('sampler', 'N/A')}, "
            f"sched: {param.get('scheduler', 'N/A')}"
        )

        # Third line: guidance, shifts
        lines.append(
            f"guidance: {param.get('guidance', 'N/A')}, "
            f"max/base shift: {param.get('max_shift', 'N/A')}/{param.get('base_shift', 'N/A')}"
        )

        # Optional LoRA line
        if "lora" in param and param["lora"]:
            lora_name = param["lora"][:32] if len(param["lora"]) > 32 else param["lora"]
            lines.append(f"LoRA: {lora_name}, str: {param.get('lora_strength', 'N/A')}")

        return "\n".join(lines)


def wrap_prompt_text(prompt: str, width_chars: int, mode: str = "full") -> List[str]:
    """
    Wrap prompt text to fit within character width.

    Args:
        prompt: Prompt text to wrap
        width_chars: Maximum characters per line
        mode: Display mode ("full", "excerpt")

    Returns:
        List of wrapped lines
    """
    if not prompt:
        return []

    original_words = prompt.split()

    if mode == "excerpt":
        # Take first 64 words
        words = original_words[:64]
        prompt = " ".join(words)
        # Add ellipsis if we truncated
        if len(words) < len(original_words):
            prompt += "..."

    # Use textwrap to break into lines
    lines = textwrap.wrap(prompt, width=width_chars)

    return lines


def calculate_text_dimensions(
    text: str, font_size: int, image_width: int
) -> Tuple[int, int, int]:
    """
    Calculate text rendering dimensions.

    Args:
        text: Text to render
        font_size: Font size in pixels
        image_width: Width of the image

    Returns:
        Tuple of (line_height, char_width, num_lines)
    """
    # Approximate calculations (adjust based on actual font metrics)
    line_height = int(font_size * 1.5)  # Line height with padding
    char_width = int(font_size * 0.6)  # Approximate monospace char width

    lines = text.split("\n")
    num_lines = len(lines)

    return line_height, char_width, num_lines


def calculate_grid_dimensions(num_images: int, cols_num: int) -> Tuple[int, int]:
    """
    Calculate grid dimensions for image layout.

    Args:
        num_images: Total number of images
        cols_num: Number of columns (-1 for auto)

    Returns:
        Tuple of (rows, cols)
    """
    if cols_num == 0 or cols_num == -1:
        # Auto-calculate columns
        cols = int(math.sqrt(num_images))
        cols = max(1, min(cols, 1024))
    else:
        cols = min(cols_num, num_images)

    rows = math.ceil(num_images / cols)

    return rows, cols


def validate_plot_parameters(
    images_shape: tuple,
    params_length: int,
    order_by: str,
    cols_value: str,
    cols_num: int,
) -> bool:
    """
    Validate plot parameters configuration.

    Args:
        images_shape: Shape of the images tensor
        params_length: Length of parameters list
        order_by: Ordering key
        cols_value: Column grouping key
        cols_num: Number of columns

    Returns:
        True if configuration is valid
    """
    if images_shape[0] != params_length:
        logger.error(
            f"Image count ({images_shape[0]}) doesn't match parameters ({params_length})"
        )
        return False

    valid_keys = [
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

    if order_by not in valid_keys:
        logger.warning(f"Invalid order_by value: {order_by}")

    if cols_value not in valid_keys:
        logger.warning(f"Invalid cols_value: {cols_value}")

    if cols_num < -1 or cols_num > 1024:
        logger.warning(f"Invalid cols_num: {cols_num}")

    return True
