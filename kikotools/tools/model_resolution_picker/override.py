"""User override file for the Model Resolution Picker family table.

``<user dir>/kikotools/model_resolutions.json`` may replace families by label,
append new ones, remove shipped ones and change the default. The merged table
is validated as a whole; an override that fails to load, merge or validate is
ignored entirely and reported as a warning.
"""

import copy
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .table import load_table, validate_table

logger = logging.getLogger(__name__)

OVERRIDE_DIR = "kikotools"
OVERRIDE_NAME = "model_resolutions.json"
MAX_REPORTED_PROBLEMS = 3

Table = Dict[str, Any]
_CacheKey = Tuple[Path, int, int]

_cache: Optional[Tuple[_CacheKey, Tuple[Table, List[str]]]] = None


def _reset_cache() -> None:
    """Forget the cached merge result (used by tests)."""
    global _cache
    _cache = None


def override_path() -> Optional[Path]:
    """Return the override file location, or None when no user dir is known."""
    try:
        import folder_paths

        user_dir = folder_paths.get_user_directory()
        return Path(user_dir) / OVERRIDE_DIR / OVERRIDE_NAME
    except Exception:  # ImportError, AttributeError, or a broken host
        return None


def _check_override_shape(override: Any) -> None:
    """Raise ValueError unless ``override`` has the minimal expected shape."""
    if not isinstance(override, dict):
        raise ValueError("override must be a JSON object")
    fams = override.get("families", [])
    if not isinstance(fams, list):
        raise ValueError("'families' must be a list")
    for index, fam in enumerate(fams):
        if not isinstance(fam, dict) or not isinstance(fam.get("label"), str):
            raise ValueError(f"families[{index}] must be an object with a string label")
    remove = override.get("remove", [])
    if not isinstance(remove, list) or not all(isinstance(r, str) for r in remove):
        raise ValueError("'remove' must be a list of strings")
    default = override.get("default")
    if default is not None and not isinstance(default, str):
        raise ValueError("'default' must be a string")


def merge_override(shipped: Table, override: Table) -> Table:
    """Return a new table: ``shipped`` with ``override`` applied (no mutation)."""
    _check_override_shape(override)
    merged = copy.deepcopy(shipped)
    replacements = {f["label"]: f for f in override.get("families", [])}
    removed = set(override.get("remove", []))
    result: List[Any] = []
    for fam in merged.get("families", []):
        label = fam.get("label") if isinstance(fam, dict) else None
        if label in removed:
            continue
        result.append(
            copy.deepcopy(replacements.pop(label)) if label in replacements else fam
        )
    result.extend(
        copy.deepcopy(f) for label, f in replacements.items() if label not in removed
    )
    merged["families"] = result
    if isinstance(override.get("default"), str):
        merged["default"] = override["default"]
    return merged


def _ignored(path: Path, reason: str, shipped: Table) -> Tuple[Table, List[str]]:
    message = f"Override ignored: {path}: {reason}"
    logger.warning(message)
    return shipped, [message]


def _build(path: Path, shipped: Table) -> Tuple[Table, List[str]]:
    """Load, merge and validate the override at ``path``."""
    try:
        merged = merge_override(shipped, load_table(path))
        problems = validate_table(merged)
    except (ValueError, RecursionError) as exc:
        reason = "nested too deeply" if isinstance(exc, RecursionError) else str(exc)
        return _ignored(path, reason, shipped)
    if problems:
        return _ignored(path, "; ".join(problems[:MAX_REPORTED_PROBLEMS]), shipped)
    return merged, []


def current_table() -> Tuple[Table, List[str]]:
    """Return ``(table, warnings)``: shipped data merged with a valid override."""
    global _cache
    from .families import SHIPPED_DATA

    path = override_path()
    if path is None:
        return SHIPPED_DATA, []
    try:
        stat = path.stat()
        key: _CacheKey = (path, stat.st_mtime_ns, stat.st_size)
    except OSError:
        return SHIPPED_DATA, []
    if _cache is not None and _cache[0] == key:
        return _cache[1]
    result = _build(path, SHIPPED_DATA)
    _cache = (key, result)
    return result
