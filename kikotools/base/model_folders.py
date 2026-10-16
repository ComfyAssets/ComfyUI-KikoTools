"""Scan ComfyUI model folders (loras, checkpoints, ...) for .safetensors files."""

import logging
import os
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def get_model_roots(folder_key: str) -> List[str]:
    """Return every configured root directory for a folder_paths key."""
    try:
        import folder_paths

        entry = folder_paths.folder_names_and_paths.get(folder_key)
        return list(entry[0]) if entry else []
    except (ImportError, AttributeError, IndexError, TypeError):
        return []


def is_within(path: str, root: str) -> bool:
    """True if realpath `path` equals or is inside realpath `root`."""
    try:
        real_path, real_root = os.path.realpath(path), os.path.realpath(root)
        return os.path.commonpath([real_path, real_root]) == real_root
    except ValueError:  # different drives or mixed absolute/relative
        return False


def resolve_scan_targets(
    folder_path: str, folder_key: str
) -> List[Tuple[str, Optional[str]]]:
    """
    Resolve a folder setting to (directory, base_root) pairs to scan.

    base_root is the model root the directory lives in, or None when the
    directory is an absolute path outside every known root.
    """
    roots = get_model_roots(folder_key)

    if os.path.isabs(folder_path):
        base = next((r for r in roots if is_within(folder_path, r)), None)
        return [(folder_path, base)]

    targets = []
    for root in roots:
        candidate = os.path.join(root, folder_path)
        if not is_within(candidate, root):
            logger.warning(f"Folder escapes the {folder_key} directory: {folder_path}")
            continue
        targets.append((candidate, root))
    return targets


def scan_model_entries(folder_path: str, folder_key: str) -> List[Tuple[str, str]]:
    """Return naturally sorted (relative_name, absolute_path) for every .safetensors."""
    entries: Dict[str, str] = {}
    for directory, base in resolve_scan_targets(folder_path, folder_key):
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


def natural_sort(items: List[str]) -> List[str]:
    """Sort strings so embedded numbers compare numerically (v2 < v10)."""

    def natural_key(text):
        parts = []
        for part in re.split(r"(\d+)", text):
            if not part:
                continue
            parts.append((0, int(part)) if part.isdigit() else (1, part.lower()))
        return parts

    return sorted(items, key=natural_key)


def filter_by_pattern(
    names: List[str], include_pattern: str = "", exclude_pattern: str = ""
) -> List[str]:
    """Keep names matching include_pattern (if set) and not exclude_pattern (if set)."""
    filtered = list(names)
    if include_pattern:
        try:
            include_re = re.compile(include_pattern)
            filtered = [f for f in filtered if include_re.search(f)]
        except re.error as e:
            logger.error(f"Invalid include pattern: {e}")
    if exclude_pattern:
        try:
            exclude_re = re.compile(exclude_pattern)
            filtered = [f for f in filtered if not exclude_re.search(f)]
        except re.error as e:
            logger.error(f"Invalid exclude pattern: {e}")
    return filtered
