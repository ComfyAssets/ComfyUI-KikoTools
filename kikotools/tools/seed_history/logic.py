"""Core logic for Seed History tool."""

import random
import time
from typing import List, Dict, Any, Tuple, Optional


def generate_random_seed() -> int:
    """
    Generate a cryptographically strong random seed value.

    Returns:
        Random integer in the valid ComfyUI seed range (0 to 2**32 - 1)
    """
    return random.randint(0, 0xFFFFFFFF)  # 2**32 - 1


def validate_seed_value(seed: Any) -> bool:
    """
    Validate that a seed value is within acceptable range (0 to 2**32 - 1).

    Args:
        seed: Seed value to validate

    Returns:
        True if seed is valid, False otherwise
    """
    if seed is None:
        return False

    try:
        seed_int = int(seed)
        return 0 <= seed_int <= 0xFFFFFFFF  # 2**32 - 1
    except (ValueError, TypeError):
        return False


def sanitize_seed_value(seed: Any) -> int:
    """
    Sanitize and convert seed value to valid integer.

    Args:
        seed: Raw seed value

    Returns:
        Valid seed integer

    Raises:
        ValueError: If seed cannot be converted to valid range
    """
    if seed is None:
        raise ValueError("Seed cannot be None")

    try:
        seed_int = int(seed)

        # Clamp to valid range (0 to 2**32 - 1)
        if seed_int < 0:
            seed_int = 0
        elif seed_int > 0xFFFFFFFF:
            seed_int = 0xFFFFFFFF

        return seed_int

    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid seed value: {seed}") from e


def create_history_entry(
    seed: int, timestamp: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create a standardized history entry for a seed.

    Args:
        seed: Seed value
        timestamp: Optional timestamp (uses current time if None)

    Returns:
        Dictionary containing seed history entry
    """
    if timestamp is None:
        timestamp = time.time()

    return {
        "seed": seed,
        "timestamp": timestamp,
        "dateString": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
    }


def filter_duplicate_seeds(
    history: List[Dict[str, Any]], new_seed: int, dedup_window_ms: int = 500
) -> bool:
    """
    Check if a seed should be filtered as a duplicate.

    Args:
        history: Current seed history
        new_seed: New seed to check
        dedup_window_ms: Deduplication window in milliseconds

    Returns:
        True if seed should be filtered (is duplicate), False otherwise
    """
    if not history:
        return False

    current_time = time.time() * 1000  # Convert to milliseconds

    # Check most recent entry for duplicates within window
    latest_entry = history[0]
    latest_timestamp_ms = latest_entry["timestamp"] * 1000

    time_diff = current_time - latest_timestamp_ms
    is_same_seed = latest_entry["seed"] == new_seed
    is_within_window = time_diff < dedup_window_ms

    return is_same_seed and is_within_window


def add_seed_to_history(
    history: List[Dict[str, Any]],
    seed: int,
    max_history: int = 10,
    dedup_window_ms: int = 500,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Add a seed to the history with deduplication and size management.

    Args:
        history: Current seed history
        seed: Seed to add
        max_history: Maximum number of entries to keep
        dedup_window_ms: Deduplication window in milliseconds

    Returns:
        Tuple of (updated_history, was_added)
    """
    # Validate seed
    if not validate_seed_value(seed):
        return history, False

    # Sanitize seed
    try:
        clean_seed = sanitize_seed_value(seed)
    except ValueError:
        return history, False

    # Check for duplicates
    if filter_duplicate_seeds(history, clean_seed, dedup_window_ms):
        return history, False

    # Create new history list (don't modify original)
    new_history = [entry for entry in history if entry["seed"] != clean_seed]

    # Add new entry at the beginning
    new_entry = create_history_entry(clean_seed)
    new_history.insert(0, new_entry)

    # Trim to max size
    if len(new_history) > max_history:
        new_history = new_history[:max_history]

    return new_history, True


def format_time_ago(timestamp: float) -> str:
    """
    Format a timestamp as a human-readable time ago string.

    Args:
        timestamp: Unix timestamp

    Returns:
        Formatted time ago string
    """
    now = time.time()
    diff = now - timestamp

    days = int(diff // 86400)
    hours = int((diff % 86400) // 3600)
    minutes = int((diff % 3600) // 60)
    seconds = int(diff % 60)

    if days > 0:
        return f"{days}d ago"
    elif hours > 0:
        return f"{hours}h ago"
    elif minutes > 0:
        return f"{minutes}m ago"
    else:
        return f"{seconds}s ago"


def search_history_by_seed(
    history: List[Dict[str, Any]], seed: int
) -> Optional[Dict[str, Any]]:
    """
    Search history for a specific seed value.

    Args:
        history: Seed history to search
        seed: Seed value to find

    Returns:
        History entry if found, None otherwise
    """
    for entry in history:
        if entry["seed"] == seed:
            return entry
    return None


def get_history_statistics(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics about the seed history.

    Args:
        history: Seed history

    Returns:
        Dictionary containing history statistics
    """
    if not history:
        return {
            "total_seeds": 0,
            "oldest_timestamp": None,
            "newest_timestamp": None,
            "time_span_hours": 0,
            "unique_seeds": 0,
        }

    timestamps = [entry["timestamp"] for entry in history]
    oldest = min(timestamps)
    newest = max(timestamps)
    time_span = (newest - oldest) / 3600  # Convert to hours

    unique_seeds = len(set(entry["seed"] for entry in history))

    return {
        "total_seeds": len(history),
        "oldest_timestamp": oldest,
        "newest_timestamp": newest,
        "time_span_hours": time_span,
        "unique_seeds": unique_seeds,
    }


def export_history_to_text(history: List[Dict[str, Any]]) -> str:
    """
    Export seed history to a formatted text string.

    Args:
        history: Seed history to export

    Returns:
        Formatted text representation
    """
    if not history:
        return "# Seed History (Empty)\n\nNo seeds tracked yet."

    lines = ["# ComfyUI Seed History", ""]
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total seeds: {len(history)}")
    lines.append("")

    for i, entry in enumerate(history, 1):
        time_ago = format_time_ago(entry["timestamp"])
        lines.append(f"{i:2d}. {entry['seed']} ({time_ago})")

    return "\n".join(lines)


def import_seeds_from_list(seed_list: List[int]) -> List[Dict[str, Any]]:
    """
    Import a list of seeds as history entries.

    Args:
        seed_list: List of seed integers

    Returns:
        List of history entries
    """
    history = []
    current_time = time.time()

    for i, seed in enumerate(seed_list):
        if validate_seed_value(seed):
            # Spread timestamps by 1 minute intervals (newest first)
            timestamp = current_time - (i * 60)
            entry = create_history_entry(seed, timestamp)
            history.append(entry)

    return history
