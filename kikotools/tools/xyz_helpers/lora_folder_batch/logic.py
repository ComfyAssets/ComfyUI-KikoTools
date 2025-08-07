"""Logic module for LoRA Folder Batch node."""

import os
import re
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
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


def scan_folder_for_loras(folder_path: str) -> List[str]:
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

        # Check if this is an absolute path
        if os.path.isabs(folder_path):
            full_path = folder_path

            # Try to find which lora base path this belongs to
            rel_folder = None
            for lora_base in lora_paths:
                try:
                    potential_rel = os.path.relpath(full_path, lora_base)
                    if not potential_rel.startswith(".."):
                        # This path is inside this lora base
                        rel_folder = potential_rel
                        break
                except ValueError:
                    # Different drives on Windows
                    continue

            if rel_folder is None:
                # Path is outside all known lora directories
                # Try to extract a relative path that might work
                # Check if path contains common lora folder structures
                path_parts = full_path.replace("\\", "/").split("/")
                if "lora" in path_parts or "loras" in path_parts:
                    # Find index after lora/loras
                    for i, part in enumerate(path_parts):
                        if part in ["lora", "loras"]:
                            # Use everything after lora/loras as relative path
                            rel_folder = "/".join(path_parts[i + 1 :])
                            break

                if rel_folder is None:
                    # Last resort: use last two directories as relative path
                    rel_folder = (
                        "/".join(path_parts[-2:])
                        if len(path_parts) >= 2
                        else path_parts[-1]
                    )
        else:
            # Relative path provided
            full_path = (
                os.path.join(lora_paths[0], folder_path) if lora_paths else folder_path
            )
            rel_folder = folder_path if folder_path != "." else ""

        if not os.path.exists(full_path):
            logger.warning(f"Folder does not exist: {full_path}")
            return []

        # Scan for .safetensors files
        lora_files = []
        for file in os.listdir(full_path):
            if file.endswith(".safetensors"):
                # Store relative path from lora base
                if rel_folder and rel_folder != ".":
                    lora_files.append(os.path.join(rel_folder, file).replace("\\", "/"))
                else:
                    lora_files.append(file)

        # Sort naturally (handles epoch numbers properly)
        lora_files = natural_sort(lora_files)

        logger.info(
            f"Found {len(lora_files)} LoRA files in {folder_path}, returning paths relative to lora base"
        )
        return lora_files

    except Exception as e:
        logger.error(f"Error scanning folder {folder_path}: {e}")
        return []


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
        # Put files without numbers first
        if not any(isinstance(p, int) for p in parts):
            return [0] + parts
        return parts

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


def parse_strength_string(strength_str: str) -> List[float]:
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
        folder_path: Folder path to validate

    Returns:
        True if valid
    """
    try:
        import folder_paths

        lora_base_path = folder_paths.folder_names_and_paths["loras"][0][0]

        if folder_path == ".":
            full_path = lora_base_path
        else:
            full_path = os.path.join(lora_base_path, folder_path)

        return os.path.exists(full_path) and os.path.isdir(full_path)

    except Exception:
        return False
