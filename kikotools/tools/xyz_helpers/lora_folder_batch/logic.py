"""Logic module for LoRA Folder Batch node."""

import os
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


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


def scan_folder_for_loras(folder_path: str) -> List[str]:  # noqa: C901
    """
    Scan a folder for LoRA files (.safetensors).

    Args:
        folder_path: Path to folder to scan (absolute or relative to models/loras)

    Returns:
        List of LoRA filenames relative to models/loras directory
    """
    try:
        import folder_paths

        # Get all LoRA paths from ComfyUI (includes extra_model_paths)
        lora_paths = folder_paths.folder_names_and_paths.get("loras", [[]])[0]

        # Determine the full path and base lora path
        full_path = None
        base_lora_path = None

        # Check if this is an absolute path
        if os.path.isabs(folder_path):
            full_path = folder_path

            # Check if this path is inside any of the known lora directories
            for lora_base in lora_paths:
                # Normalize paths for comparison
                norm_full = os.path.normpath(full_path)
                norm_base = os.path.normpath(lora_base)

                # Check if full_path starts with this lora_base
                if norm_full.startswith(norm_base):
                    base_lora_path = lora_base
                    break

                # Also check if the path is a subdirectory under lora/loras
                if "lora" in norm_full.lower():
                    # Find the lora or loras directory in the path
                    path_parts = norm_full.replace("\\", "/").split("/")
                    for i, part in enumerate(path_parts):
                        if part.lower() in ["lora", "loras"]:
                            # Check if this matches our lora_base
                            potential_base = "/".join(path_parts[: i + 1])
                            if os.path.normpath(potential_base) == norm_base:
                                base_lora_path = lora_base
                                break
                    if base_lora_path:
                        break
        else:
            # Relative path provided
            base_lora_path = lora_paths[0] if lora_paths else ""
            full_path = os.path.join(base_lora_path, folder_path)

        if not os.path.exists(full_path):
            logger.warning(f"Folder does not exist: {full_path}")
            return []

        # Scan for .safetensors files recursively
        lora_files = []
        for root, _, files in os.walk(full_path):
            for file in files:
                if file.endswith(".safetensors"):
                    # Get the full path to the file
                    file_full_path = os.path.join(root, file)

                    # Calculate the correct relative path for ComfyUI
                    if base_lora_path:
                        # Path is inside a known lora directory
                        try:
                            rel_path = os.path.relpath(file_full_path, base_lora_path)
                            lora_files.append(rel_path.replace("\\", "/"))
                        except ValueError:
                            # Different drives on Windows, use path relative to scan folder
                            rel_path = os.path.relpath(file_full_path, full_path)
                            if rel_path == ".":
                                lora_files.append(file)
                            else:
                                lora_files.append(rel_path.replace("\\", "/"))
                    else:
                        # Path is outside known lora directories
                        # Return path relative to the scanned folder
                        rel_path = os.path.relpath(file_full_path, full_path)
                        if rel_path == ".":
                            lora_files.append(file)
                        else:
                            lora_files.append(rel_path.replace("\\", "/"))

        # Sort naturally (handles epoch numbers properly)
        lora_files = natural_sort(lora_files)

        logger.info(f"Found {len(lora_files)} LoRA files in {folder_path}")
        if lora_files and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Base lora path: {base_lora_path}")
            logger.debug(f"Full scan path: {full_path}")
            logger.debug(f"First few LoRA paths returned: {lora_files[:3]}")
        return lora_files

    except Exception as e:
        logger.error(f"Error scanning folder {folder_path}: {e}")
        return []


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


def parse_strength_string(strength_str: str) -> List[float]:  # noqa: C901
    """
    Parse strength string into list of values.

    Supports:
    - Single value: "1.0"
    - Multiple values: "0.5, 0.75, 1.0"
    - Range: "0.5...1.0" (with optional step)

    Args:
        strength_str: String representation of strengths

    Returns:
        List of strength values
    """
    strength_str = strength_str.strip()

    if not strength_str:
        return [1.0]

    # Check for range notation
    if "..." in strength_str:
        parts = strength_str.split("...")
        if len(parts) == 2:
            try:
                start = float(parts[0].strip())
                end_part = parts[1].strip()

                # Check for step
                if "+" in end_part:
                    end_str, step_str = end_part.split("+")
                    end = float(end_str.strip())
                    step = float(step_str.strip())
                else:
                    end = float(end_part)
                    step = 0.1  # Default step

                # Generate range
                values = []
                current = start
                while current <= end + 0.0001:  # Small epsilon for float comparison
                    values.append(round(current, 4))
                    current += step

                return values
            except ValueError as e:
                logger.error(f"Invalid range format: {e}")
                return [1.0]

    # Parse comma-separated values
    try:
        values = []
        for item in strength_str.split(","):
            item = item.strip()
            if item:
                values.append(float(item))
        return values if values else [1.0]
    except ValueError as e:
        logger.error(f"Invalid strength values: {e}")
        return [1.0]


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

    Args:
        folder_path: Folder path to validate (absolute or relative)

    Returns:
        True if valid
    """
    try:
        # Handle absolute paths
        if os.path.isabs(folder_path):
            return os.path.exists(folder_path) and os.path.isdir(folder_path)

        # Handle relative paths
        import folder_paths

        lora_paths = folder_paths.folder_names_and_paths.get("loras", [[]])[0]

        if not lora_paths:
            return False

        lora_base_path = lora_paths[0]

        if folder_path == ".":
            full_path = lora_base_path
        else:
            full_path = os.path.join(lora_base_path, folder_path)

        return os.path.exists(full_path) and os.path.isdir(full_path)

    except Exception:
        return False
