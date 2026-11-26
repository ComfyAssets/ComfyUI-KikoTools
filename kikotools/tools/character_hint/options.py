"""Option tables for the Character Hint nodes.

The tables live in ``options.json`` next to this file. Every table maps the
label shown in the node to the phrase written into the hint (``makeup`` maps a
label to a ``{"look", "lips"}`` object). The shipped options were checked
against MiniMax H3 Image.

An optional user file, ``<ComfyUI user dir>/kikotools/character_hint.json``,
can add, replace or remove entries. It survives pack updates. ``UNSET`` and
the age limits stay in code.
"""

import copy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

UNSET = "-"

MIN_AGE = 18
MAX_AGE = 90
DEFAULT_AGE = 25

TABLE_NAMES: Tuple[str, ...] = (
    "heritage",
    "female_body",
    "male_body",
    "breast_size",
    "butt_size",
    "face_shape",
    "facial_structure",
    "eye_color",
    "eye_shape",
    "eye_detail",
    "eyebrows",
    "nose",
    "female_lip_shape",
    "male_lip_shape",
    "lip_color",
    "makeup",
    "eyewear",
    "facial_hair",
    "expression",
    "head_angle",
    "gaze",
    "hair_color",
    "hair_texture",
    "hair_length",
    "female_hair_style",
    "male_hair_style",
    "bangs",
    "skin_tone",
    "tan",
    "freckles",
    "acne",
    "beauty_mark",
    "dimples",
    "tattoo",
    "nipples",
    "areola",
)

USER_FILE = "kikotools/character_hint.json"
SHIPPED_PATH = Path(__file__).with_name("options.json")
LOG_PREFIX = "Character Hint options"
MAKEUP = "makeup"

Tables = Dict[str, Dict[str, Any]]
_CacheKey = Tuple[Path, int, int]

_shipped: Optional[Tables] = None
_user_cache: Optional[Tuple[_CacheKey, Tables]] = None


def _reset_cache() -> None:
    """Forget cached data (used by tests)."""
    global _shipped, _user_cache
    _shipped = None
    _user_cache = None


def _label_problem(label: Any) -> Optional[str]:
    if not isinstance(label, str) or not label.strip():
        return "the label must be a non-empty text"
    if label == UNSET:
        return f"the label '{UNSET}' is reserved"
    return None


def _text_ok(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _makeup_ok(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and _text_ok(value.get("look"))
        and _text_ok(value.get("lips"))
    )


def _clean_makeup(value: Dict[str, Any]) -> Dict[str, str]:
    return {"look": value["look"].strip(), "lips": value["lips"].strip()}


def _validate_shipped(data: Any) -> Tables:
    if not isinstance(data, dict) or list(data) != list(TABLE_NAMES):
        raise ValueError("options.json must hold exactly the known tables")
    for name, table in data.items():
        if not isinstance(table, dict) or not table:
            raise ValueError(f"options.json: table '{name}' must not be empty")
        for label, phrase in table.items():
            problem = _label_problem(label)
            if problem:
                raise ValueError(f"options.json: {name}: {problem}")
            valid = _makeup_ok(phrase) if name == MAKEUP else _text_ok(phrase)
            if not valid:
                raise ValueError(f"options.json: {name}: bad entry '{label}'")
    return data


def load_shipped() -> Tables:
    """The shipped tables (cached). A broken shipped file raises."""
    global _shipped
    if _shipped is None:
        with open(SHIPPED_PATH, encoding="utf-8") as handle:
            _shipped = _validate_shipped(json.load(handle))
    return _shipped


def _apply_entry(
    table: Dict[str, Any], name: str, label: Any, value: Any
) -> Optional[str]:
    """Apply one entry to ``table`` in place; return a problem or None."""
    problem = _label_problem(label)
    if problem:
        return f"{name}: skipped {label!r}: {problem}"
    if value is None:
        if label not in table:
            return f"{name}: cannot remove '{label}': no such option"
        del table[label]
        return None
    if name == MAKEUP:
        if not _makeup_ok(value):
            return (
                f"{name}: skipped '{label}': expected "
                'null or {"look": "...", "lips": "..."} with both filled in'
            )
        table[label] = _clean_makeup(value)
    elif _text_ok(value):
        table[label] = value.strip()
    else:
        return f"{name}: skipped '{label}': the phrase must be a non-empty text"
    return None


def apply_override(base: Tables, override: Any) -> Tuple[Tables, List[str]]:
    """Apply a parsed user file to ``base``; never raises or mutates ``base``.

    Returns ``(tables, problems)``. Bad entries are skipped and described in
    ``problems``; valid entries still apply.
    """
    result = copy.deepcopy(base)
    problems: List[str] = []
    if not isinstance(override, dict):
        return result, ["the top level must be a JSON object"]
    for name, entries in override.items():
        if name not in result:
            problems.append(f"unknown table '{name}'")
            continue
        if not isinstance(entries, dict):
            problems.append(f"{name}: skipped: expected an object of label: phrase")
            continue
        table = copy.deepcopy(result[name])
        for label, value in entries.items():
            problem = _apply_entry(table, name, label, value)
            if problem:
                problems.append(problem)
        if table:
            result[name] = table
        else:
            problems.append(f"{name}: kept the shipped list: it cannot be empty")
    return result, problems


def user_file_path() -> Optional[Path]:
    """The user file location, or None when no user directory is known."""
    try:
        import folder_paths

        return Path(folder_paths.get_user_directory()) / USER_FILE
    except Exception:  # ImportError, AttributeError, or a broken host
        return None


def _warn(path: Path, message: str) -> None:
    logger.warning("%s: %s: %s", LOG_PREFIX, path, message)


def _load_user(path: Path, shipped: Tables) -> Tables:
    try:
        with open(path, encoding="utf-8") as handle:
            override = json.load(handle)
    except (OSError, ValueError, RecursionError) as exc:
        _warn(path, f"ignored, could not read it ({exc})")
        return shipped
    if not isinstance(override, dict):
        _warn(path, "ignored, the top level must be a JSON object")
        return shipped
    merged, problems = apply_override(shipped, override)
    for problem in problems:
        _warn(path, problem)
    return merged


def tables() -> Tables:
    """Shipped tables with the user file applied (cached on the file's stamp).

    Treat the result as read-only.
    """
    global _user_cache
    shipped = load_shipped()
    path = user_file_path()
    if path is None:
        return shipped
    try:
        stat = path.stat()
    except OSError:
        return shipped
    key: _CacheKey = (path, stat.st_mtime_ns, stat.st_size)
    if _user_cache is None or _user_cache[0] != key:
        _user_cache = (key, _load_user(path, shipped))
    return _user_cache[1]
