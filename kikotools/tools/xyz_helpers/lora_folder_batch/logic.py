"""Logic module for LoRA Folder Batch node."""

import math
import os
import re
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

MAX_STRENGTH_VALUES = 1000
DEFAULT_RANGE_STEP = 0.1
_RANGE_EPSILON = 1e-4


def get_lora_folders() -> List[str]:
    """
    Get list of available LoRA folders.

    Returns:
        List of folder paths relative to models/loras
    """
    try:
        import folder_paths

        lora_path = folder_paths.folder_names_and_paths["loras"][0][0]

        folders = []
        for root, dirs, _ in os.walk(lora_path):
            for dir_name in dirs:
                rel_path = os.path.relpath(os.path.join(root, dir_name), lora_path)
                folders.append(rel_path)

        # Add root folder option
        folders.insert(0, ".")
        return folders

    except (ImportError, KeyError):
        # Fallback for testing
        return [".", "flux", "sdxl", "sd15"]


def _get_lora_roots() -> List[str]:
    """Return every configured loras root directory (empty if unavailable)."""
    try:
        import folder_paths

        entry = folder_paths.folder_names_and_paths.get("loras")
        return list(entry[0]) if entry else []
    except (ImportError, AttributeError, IndexError, TypeError):
        return []


def _is_within(path: str, root: str) -> bool:
    """True if realpath `path` equals or is inside realpath `root`."""
    try:
        real_path, real_root = os.path.realpath(path), os.path.realpath(root)
        return os.path.commonpath([real_path, real_root]) == real_root
    except ValueError:  # different drives or mixed absolute/relative
        return False


def _resolve_scan_targets(folder_path: str) -> List[Tuple[str, Optional[str]]]:
    """
    Resolve a folder setting to (directory, base_root) pairs to scan.

    base_root is the loras root the directory lives in, or None when the
    directory is an absolute path outside every known root.
    """
    roots = _get_lora_roots()

    if os.path.isabs(folder_path):
        base = next((r for r in roots if _is_within(folder_path, r)), None)
        return [(folder_path, base)]

    targets = []
    for root in roots:
        candidate = os.path.join(root, folder_path)
        if not _is_within(candidate, root):
            logger.warning(f"Folder escapes the loras directory: {folder_path}")
            continue
        targets.append((candidate, root))
    return targets


def _scan_entries(folder_path: str) -> List[Tuple[str, str]]:
    """Return (relative_name, absolute_path) for every .safetensors found."""
    entries: Dict[str, str] = {}
    for directory, base in _resolve_scan_targets(folder_path):
        if not os.path.isdir(directory):
            continue
        for root, _, files in os.walk(directory):
            for file in files:
                if not file.endswith(".safetensors"):
                    continue
                full = os.path.join(root, file)
                try:
                    rel = os.path.relpath(full, base or directory)
                except ValueError:
                    rel = os.path.relpath(full, directory)
                entries.setdefault(rel.replace("\\", "/"), full)
    return [(name, entries[name]) for name in natural_sort(list(entries))]


def scan_folder_for_loras(folder_path: str) -> List[str]:
    """
    Scan a folder for LoRA files (.safetensors).

    Relative folders are searched in every configured loras root. Absolute
    folders are matched to a root by real-path containment (so a sibling like
    ``loras_backup`` is not mistaken for ``loras``).

    Args:
        folder_path: Folder to scan (absolute or relative to the loras roots)

    Returns:
        Naturally sorted LoRA names relative to their loras root (or to the
        scanned folder when it lies outside every root)
    """
    names = [name for name, _ in _scan_entries(folder_path)]
    if not names:
        logger.warning(f"No LoRA files found in {folder_path}")
    else:
        logger.info(f"Found {len(names)} LoRA files in {folder_path}")
    return names


def get_lora_file_mtimes(folder_path: str) -> List[Tuple[str, float]]:
    """Return sorted (name, mtime) pairs for LoRAs in a folder."""
    result = []
    for name, full in _scan_entries(folder_path):
        try:
            result.append((name, os.path.getmtime(full)))
        except OSError:
            result.append((name, -1.0))
    return result


def sort_lora_files(lora_files: List[str], sort_order: str) -> List[str]:
    """
    Sort LoRA files based on the specified order.

    Args:
        lora_files: List of LoRA file paths
        sort_order: Type of sorting ("natural", "alphabetical", "newest", "oldest")

    Returns:
        Sorted list of LoRA files
    """
    if sort_order == "natural":
        return natural_sort(lora_files)
    elif sort_order == "alphabetical":
        return sorted(lora_files)
    elif sort_order in ["newest", "oldest"]:
        # For time-based sorting, we need the actual file stats
        # Since we only have relative paths, we'll sort by name for now
        # This could be enhanced if we have access to file stats
        sorted_files = natural_sort(lora_files)
        if sort_order == "oldest":
            return sorted_files
        else:  # newest
            return sorted_files[::-1]
    else:
        return lora_files


def natural_sort(items: List[str]) -> List[str]:
    """
    Sort strings naturally, handling numbers properly.

    Args:
        items: List of strings to sort

    Returns:
        Naturally sorted list
    """

    def natural_key(text):
        def atoi(text):
            return int(text) if text.isdigit() else text

        # Split on digits and filter out empty strings
        parts = [atoi(c) for c in re.split(r"(\d+)", text) if c]

        # Convert to tuple of (type_order, value) to ensure consistent comparison
        # Integers get type_order 0, strings get type_order 1
        typed_parts = []
        for part in parts:
            if isinstance(part, int):
                typed_parts.append((0, part))
            else:
                typed_parts.append((1, part))

        return typed_parts

    return sorted(items, key=natural_key)


def filter_loras_by_pattern(
    lora_files: List[str], include_pattern: str = "", exclude_pattern: str = ""
) -> List[str]:
    """
    Filter LoRA files by include/exclude patterns.

    Args:
        lora_files: List of LoRA filenames
        include_pattern: Regex pattern to include (empty = include all)
        exclude_pattern: Regex pattern to exclude (empty = exclude none)

    Returns:
        Filtered list of LoRA files
    """
    filtered = lora_files.copy()

    # Apply include pattern
    if include_pattern:
        try:
            include_re = re.compile(include_pattern)
            filtered = [f for f in filtered if include_re.search(f)]
        except re.error as e:
            logger.error(f"Invalid include pattern: {e}")

    # Apply exclude pattern
    if exclude_pattern:
        try:
            exclude_re = re.compile(exclude_pattern)
            filtered = [f for f in filtered if not exclude_re.search(f)]
        except re.error as e:
            logger.error(f"Invalid exclude pattern: {e}")

    return filtered


def _parse_finite(token: str, what: str, original: str) -> float:
    try:
        value = float(token.strip())
    except ValueError:
        raise ValueError(f"Invalid strength {what} '{token.strip()}' in '{original}'")
    if not math.isfinite(value):
        raise ValueError(f"Invalid strength {what} '{token.strip()}' in '{original}'")
    return value


def _parse_strength_range(text: str) -> List[float]:
    """Parse 'start...end' or 'start...end+step'."""
    parts = text.split("...")
    if len(parts) != 2:
        raise ValueError(f"Invalid strength range '{text}': use start...end[+step]")
    start = _parse_finite(parts[0], "start", text)

    end_part = parts[1]
    if "+" in end_part:
        pieces = end_part.split("+")
        if len(pieces) != 2:
            raise ValueError(f"Invalid strength range '{text}': use start...end[+step]")
        end = _parse_finite(pieces[0], "end", text)
        step = _parse_finite(pieces[1], "step", text)
    else:
        end = _parse_finite(end_part, "end", text)
        step = DEFAULT_RANGE_STEP

    if step <= 0:
        raise ValueError(
            f"Invalid strength range '{text}': step must be greater than 0"
        )
    if end < start:
        raise ValueError(
            f"Invalid strength range '{text}': reversed range "
            f"(start {start:g} is greater than end {end:g})"
        )

    count = int(math.floor((end - start) / step + _RANGE_EPSILON)) + 1
    if count > MAX_STRENGTH_VALUES:
        raise ValueError(
            f"Strength range '{text}' would generate {count} values; "
            f"the maximum is {MAX_STRENGTH_VALUES}"
        )
    return [round(start + i * step, 4) for i in range(count)]


def parse_strength_string(strength_str: str) -> List[float]:
    """
    Parse strength string into list of values.

    Supports:
    - Blank: defaults to [1.0]
    - Single value: "1.0"
    - Multiple values: "0.5, 0.75, 1.0"
    - Range: "0.5...1.0" (default step 0.1) or "0.5...1.0+0.25"

    Raises:
        ValueError: On malformed input, non-positive step, reversed range, or
            more than MAX_STRENGTH_VALUES generated values.
    """
    strength_str = strength_str.strip()
    if not strength_str:
        return [1.0]

    if "..." in strength_str:
        return _parse_strength_range(strength_str)

    values = [
        _parse_finite(item, "value", strength_str)
        for item in strength_str.split(",")
        if item.strip()
    ]
    if not values:
        raise ValueError(f"No strength values found in '{strength_str}'")
    return values


def create_lora_params(
    lora_files: List[str], strengths: List[float], batch_mode: str = "sequential"
) -> Dict[str, Any]:
    """
    Create LORA_PARAMS structure for FluxSamplerParams.

    Args:
        lora_files: List of LoRA file paths
        strengths: List of strength values to test
        batch_mode: How to batch ("sequential" or "combinatorial")

    Returns:
        LORA_PARAMS dictionary
    """
    if not lora_files:
        logger.warning("No LoRA files provided")
        return {"loras": [], "strengths": []}

    if not strengths:
        raise ValueError("At least one strength value is required")

    if batch_mode == "combinatorial":
        # Each LoRA gets tested with each strength
        # This creates len(loras) * len(strengths) combinations
        return {"loras": lora_files, "strengths": [strengths for _ in lora_files]}
    else:
        # Sequential mode - cycle through strengths for each LoRA
        # If fewer strengths than LoRAs, repeat the strength list
        strength_lists = []
        for i, lora in enumerate(lora_files):
            strength_idx = i % len(strengths)
            strength_lists.append([strengths[strength_idx]])

        return {"loras": lora_files, "strengths": strength_lists}


def create_lora_params_batched(
    lora_files: List[str],
    strengths: List[float],
    batch_mode: str = "sequential",
    batch_size: int = 25,
) -> List[Dict[str, Any]]:
    """
    Create multiple LORA_PARAMS structures for FluxSamplerParams, batched for stability.

    Args:
        lora_files: List of LoRA file paths
        strengths: List of strength values to test
        batch_mode: How to batch ("sequential" or "combinatorial")
        batch_size: Maximum number of LoRAs per batch

    Returns:
        List of LORA_PARAMS dictionaries, each with batch info
    """
    if not lora_files:
        logger.warning("No LoRA files provided")
        return [{"loras": [], "strengths": [], "batch_info": {"index": 0, "total": 0}}]

    # Split lora_files into batches
    batches = []
    total_batches = (len(lora_files) + batch_size - 1) // batch_size

    for i in range(0, len(lora_files), batch_size):
        batch_loras = lora_files[i : i + batch_size]
        batch_index = i // batch_size

        # Create params for this batch
        params = create_lora_params(batch_loras, strengths, batch_mode)

        # Add batch tracking info
        params["batch_info"] = {
            "index": batch_index,
            "total": total_batches,
            "start_idx": i,
            "end_idx": min(i + batch_size, len(lora_files)),
            "size": len(batch_loras),
        }

        batches.append(params)

    logger.info(f"Created {total_batches} batches of LoRAs (batch size: {batch_size})")
    for i, batch in enumerate(batches):
        logger.info(f"  Batch {i}: {batch['batch_info']['size']} LoRAs")

    return batches


def get_lora_info(lora_file: str) -> Dict[str, Any]:
    """
    Extract information from LoRA filename.

    Args:
        lora_file: LoRA filename

    Returns:
        Dictionary with extracted info (name, epoch, version, etc.)
    """
    info = {
        "filename": lora_file,
        "name": os.path.splitext(os.path.basename(lora_file))[0],
        "epoch": None,
        "version": None,
    }

    # Try to extract epoch number
    epoch_match = re.search(r"[-_](\d{6}|\d{5}|\d{4}|\d{3})", info["name"])
    if epoch_match:
        info["epoch"] = int(epoch_match.group(1))

    # Try to extract version
    version_match = re.search(r"v(\d+(?:\.\d+)?)", info["name"], re.IGNORECASE)
    if version_match:
        info["version"] = f"v{version_match.group(1)}"

    return info


def validate_folder_path(folder_path: str) -> bool:
    """
    Validate that the folder path exists and is accessible.

    Relative paths are accepted if they exist inside any loras root.
    """
    try:
        if os.path.isabs(folder_path):
            return os.path.isdir(folder_path)

        return any(
            os.path.isdir(directory)
            for directory, _ in _resolve_scan_targets(folder_path)
        )
    except Exception:
        return False
