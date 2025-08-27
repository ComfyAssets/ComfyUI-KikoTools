"""Logic module for Batch Prompts node."""

import os
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


def load_prompts_from_file(file_path: str) -> List[str]:
    """
    Load prompts from a text file where prompts are separated by '---'.

    Args:
        file_path: Path to the text file containing prompts

    Returns:
        List of prompts (each prompt may be multi-line)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by --- separator
        prompts = content.split("---")

        # Clean up prompts - remove leading/trailing whitespace but preserve internal formatting
        cleaned_prompts = []
        for prompt in prompts:
            prompt = prompt.strip()
            if prompt:  # Only add non-empty prompts
                cleaned_prompts.append(prompt)

        logger.info(f"Loaded {len(cleaned_prompts)} prompts from {file_path}")
        return cleaned_prompts

    except Exception as e:
        logger.error(f"Error loading prompts from {file_path}: {e}")
        return []


def get_prompt_at_index(
    prompts: List[str], index: int, wrap: bool = True
) -> Tuple[str, int]:
    """
    Get prompt at specified index with optional wrapping.

    Args:
        prompts: List of prompts
        index: Index to retrieve
        wrap: Whether to wrap around to beginning when index exceeds list length

    Returns:
        Tuple of (prompt text, actual index used)
    """
    if not prompts:
        return ("", 0)

    if wrap:
        actual_index = index % len(prompts)
    else:
        actual_index = min(index, len(prompts) - 1)

    return (prompts[actual_index], actual_index)


def get_next_prompt(
    prompts: List[str], current_index: int, wrap: bool = True
) -> Tuple[str, int]:
    """
    Get the next prompt in sequence.

    Args:
        prompts: List of prompts
        current_index: Current prompt index
        wrap: Whether to wrap around to beginning

    Returns:
        Tuple of (next prompt text, next index)
    """
    if not prompts:
        return ("", 0)

    next_index = current_index + 1

    if wrap:
        next_index = next_index % len(prompts)
    else:
        next_index = min(next_index, len(prompts) - 1)

    return (prompts[next_index], next_index)


def get_prompt_preview(prompt: str, max_length: int = 100) -> str:
    """
    Get a preview of a prompt, truncated if necessary.

    Args:
        prompt: Full prompt text
        max_length: Maximum length for preview

    Returns:
        Preview string
    """
    if len(prompt) <= max_length:
        return prompt

    return prompt[:max_length] + "..."


def parse_prompt_file_list(file_list_str: str) -> List[str]:
    """
    Parse a comma-separated list of prompt file paths.

    Args:
        file_list_str: Comma-separated file paths

    Returns:
        List of file paths
    """
    if not file_list_str:
        return []

    files = []
    for file_path in file_list_str.split(","):
        file_path = file_path.strip()
        if file_path:
            files.append(file_path)

    return files


def merge_prompts_from_multiple_files(file_paths: List[str]) -> List[str]:
    """
    Load and merge prompts from multiple files.

    Args:
        file_paths: List of file paths

    Returns:
        Combined list of all prompts
    """
    all_prompts = []

    for file_path in file_paths:
        prompts = load_prompts_from_file(file_path)
        all_prompts.extend(prompts)

    logger.info(f"Merged {len(all_prompts)} prompts from {len(file_paths)} files")
    return all_prompts


def get_batch_info(prompts: List[str], current_index: int) -> Dict[str, Any]:
    """
    Get information about current batch processing state.

    Args:
        prompts: List of prompts
        current_index: Current prompt index

    Returns:
        Dictionary with batch information
    """
    total = len(prompts)

    return {
        "current_index": current_index,
        "total_prompts": total,
        "progress": f"{current_index + 1}/{total}" if total > 0 else "0/0",
        "percentage": (current_index / total * 100) if total > 0 else 0,
        "remaining": total - current_index - 1 if total > 0 else 0,
        "is_complete": current_index >= total - 1 if total > 0 else True,
    }


def validate_prompt_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate that a prompt file exists and is readable.

    Args:
        file_path: Path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path:
        return (False, "No file path provided")

    if not os.path.exists(file_path):
        return (False, f"File not found: {file_path}")

    if not os.path.isfile(file_path):
        return (False, f"Path is not a file: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read(1)  # Try to read one character
        return (True, "")
    except Exception as e:
        return (False, f"Cannot read file: {str(e)}")


def format_prompt_for_display(prompt: str, index: int, total: int) -> str:
    """
    Format a prompt for display with index information.

    Args:
        prompt: Prompt text
        index: Current index
        total: Total number of prompts

    Returns:
        Formatted display string
    """
    header = f"[Prompt {index + 1}/{total}]"
    separator = "-" * len(header)

    return f"{header}\n{separator}\n{prompt}"


def split_prompt_into_positive_negative(
    prompt: str, negative_prefix: str = "Negative:"
) -> Tuple[str, str]:
    """
    Split a prompt into positive and negative parts.

    Args:
        prompt: Full prompt text
        negative_prefix: Prefix that marks the negative prompt section

    Returns:
        Tuple of (positive_prompt, negative_prompt)
    """
    # Look for negative prompt marker
    negative_lower = negative_prefix.lower()
    prompt_lower = prompt.lower()

    if negative_lower in prompt_lower:
        # Find the actual position (case-insensitive search)
        idx = prompt_lower.index(negative_lower)
        positive = prompt[:idx].strip()
        negative = prompt[idx + len(negative_prefix) :].strip()
        return (positive, negative)

    # No negative prompt found
    return (prompt, "")


def create_batch_queue(
    prompts: List[str], batch_size: int = 1, randomize: bool = False
) -> List[List[int]]:
    """
    Create a queue of prompt indices for batch processing.

    Args:
        prompts: List of prompts
        batch_size: Number of prompts per batch
        randomize: Whether to randomize the order

    Returns:
        List of batches, where each batch is a list of prompt indices
    """
    if not prompts:
        return []

    indices = list(range(len(prompts)))

    if randomize:
        import random

        random.shuffle(indices)

    batches = []
    for i in range(0, len(indices), batch_size):
        batch = indices[i : i + batch_size]
        batches.append(batch)

    return batches
