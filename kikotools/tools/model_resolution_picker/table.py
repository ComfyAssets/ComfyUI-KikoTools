"""Load, validate and build the Model Resolution Picker family table.

The table is plain JSON (shipped as ``families.json``). ``validate_table`` is a
pure function that returns human-readable problems and never raises for data
problems, so the same check can guard the shipped file and a user override.
Unknown keys, such as a per-family ``"notes"`` string, are ignored.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Tuple

CHIPS: Tuple[str, ...] = (
    "1:1",
    "4:5",
    "5:4",
    "3:4",
    "4:3",
    "2:3",
    "3:2",
    "9:16",
    "16:9",
    "21:9",
    "9:21",
)
MIRROR: Dict[str, str] = {
    "1:1": "1:1",
    "4:5": "5:4",
    "5:4": "4:5",
    "3:4": "4:3",
    "4:3": "3:4",
    "2:3": "3:2",
    "3:2": "2:3",
    "9:16": "16:9",
    "16:9": "9:16",
    "21:9": "9:21",
    "9:21": "21:9",
}
TABLE_VERSION = 1
GROUPS = ("image", "video")
VAE_RATIOS = (8, 16, 32)
CHIP_TOLERANCE = 0.07

Size = Tuple[int, int]


class Family(NamedTuple):
    """One model family: grid constraints, size tiers and the chip size lists."""

    label: str
    aliases: Tuple[str, ...]
    models: str
    group: str
    vae_ratio: int
    step: int
    megapixels: Tuple[float, ...]
    default: Size
    sizes: Dict[str, Tuple[Size, ...]]


def load_table(path: Path) -> Dict[str, Any]:
    """Read ``path`` as JSON; raise ``ValueError`` naming the path on failure."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot read family table {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"family table {path} must be a JSON object")
    return data


def _is_size(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in value)
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _chip_ratio(chip: str) -> float:
    left, right = chip.split(":")
    return int(left) / int(right)


def _validate_top_level(data: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    if data.get("version") != TABLE_VERSION:
        problems.append(f"version must be {TABLE_VERSION}")
    if data.get("chips") != list(CHIPS):
        problems.append(f"chips must equal {list(CHIPS)}")
    if data.get("mirror") != MIRROR:
        problems.append("mirror must pair every chip with its mirrored chip")
    if not isinstance(data.get("families"), list) or not data["families"]:
        problems.append("families must be a non-empty list")
    return problems


def _validate_names(families: List[Any]) -> List[str]:
    problems: List[str] = []
    seen: Dict[str, str] = {}
    for index, fam in enumerate(families):
        label = fam.get("label")
        if not isinstance(label, str) or not label:
            problems.append(f"family #{index + 1}: label must be a non-empty string")
            continue
        aliases = fam.get("aliases", [])
        if not isinstance(aliases, list) or not all(
            isinstance(a, str) for a in aliases
        ):
            problems.append(f"family {label!r}: aliases must be a list of strings")
            aliases = []
        for name in [label, *aliases]:
            if name in seen:
                problems.append(
                    f"family {label!r}: duplicate label or alias {name!r} "
                    f"(already used by {seen[name]!r})"
                )
            else:
                seen[name] = label
    return problems


def _validate_scalars(label: str, fam: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    if not isinstance(fam.get("models"), str):
        problems.append(f"family {label!r}: models must be a string")
    if fam.get("group") not in GROUPS:
        problems.append(f"family {label!r}: group must be one of {list(GROUPS)}")
    if fam.get("vaeRatio") not in VAE_RATIOS:
        problems.append(f"family {label!r}: vaeRatio must be one of {list(VAE_RATIOS)}")
    step = fam.get("step")
    if not _is_number(step) or step <= 0 or int(step) != step:
        problems.append(f"family {label!r}: step must be a positive integer")
    mp = fam.get("megapixels")
    if not isinstance(mp, list) or not mp or not all(_is_number(m) for m in mp):
        problems.append(f"family {label!r}: megapixels must be a non-empty number list")
    return problems


def _validate_chip(
    label: str, chip: str, entries: Any, fam: Dict[str, Any]
) -> List[str]:
    where = f"family {label!r}, chip {chip}"
    if not isinstance(entries, list) or not all(_is_size(s) for s in entries):
        return [f"{where}: sizes must be a list of [width, height] integer pairs"]
    problems: List[str] = []
    step = fam.get("step")
    step_ok = _is_number(step) and step > 0 and int(step) == step
    target = _chip_ratio(chip)
    for w, h in entries:
        if step_ok and (w % step or h % step):
            problems.append(f"{where}: {w}x{h} is not a multiple of step {int(step)}")
        if abs(w / h - target) / target > CHIP_TOLERANCE:
            problems.append(f"{where}: {w}x{h} is more than 7% off the {chip} ratio")
    areas = [w * h for w, h in entries]
    if areas != sorted(areas):
        problems.append(f"{where}: sizes must be in ascending pixel order")
    return problems


def _validate_sizes(label: str, fam: Dict[str, Any]) -> List[str]:
    sizes = fam.get("sizes")
    if not isinstance(sizes, dict):
        return [f"family {label!r}: sizes must be an object keyed by chip"]
    problems: List[str] = []
    for chip in CHIPS:
        if chip not in sizes:
            problems.append(f"family {label!r}: sizes is missing chip {chip}")
        else:
            problems.extend(_validate_chip(label, chip, sizes[chip], fam))
    valid = {
        chip: [tuple(s) for s in sizes[chip]]
        for chip in CHIPS
        if chip in sizes
        and isinstance(sizes[chip], list)
        and all(_is_size(s) for s in sizes[chip])
    }
    problems.extend(_validate_mirrors(label, valid))
    problems.extend(_validate_default(label, fam, valid))
    return problems


def _validate_mirrors(label: str, sizes: Dict[str, List[Size]]) -> List[str]:
    problems: List[str] = []
    owner: Dict[Size, str] = {}
    for chip, entries in sizes.items():
        mirrored = sizes.get(MIRROR[chip])
        for w, h in entries:
            if mirrored is not None and (h, w) not in mirrored:
                problems.append(
                    f"family {label!r}, chip {chip}: {w}x{h} has no mirror "
                    f"{h}x{w} under {MIRROR[chip]}"
                )
            if (w, h) in owner:
                problems.append(
                    f"family {label!r}, chip {chip}: {w}x{h} is listed under more "
                    f"than one chip (also {owner[(w, h)]})"
                )
            else:
                owner[(w, h)] = chip
    return problems


def _validate_default(
    label: str, fam: Dict[str, Any], sizes: Dict[str, Any]
) -> List[str]:
    default = fam.get("default")
    if not _is_size(default):
        return [f"family {label!r}: default must be a [width, height] pair"]
    if not any(tuple(default) in entries for entries in sizes.values()):
        return [f"family {label!r}: default {list(default)} is not in its sizes"]
    return []


def validate_table(data: Any) -> List[str]:
    """Return every problem found in ``data``; an empty list means it is valid."""
    if not isinstance(data, dict):
        return ["table must be a JSON object"]
    problems = _validate_top_level(data)
    families = data.get("families")
    if not isinstance(families, list):
        return problems
    entries = [f for f in families if isinstance(f, dict)]
    for index, fam in enumerate(families):
        if not isinstance(fam, dict):
            problems.append(f"family #{index + 1}: must be an object")
    problems.extend(_validate_names(entries))
    for fam in entries:
        label = fam.get("label")
        if not isinstance(label, str) or not label:
            continue
        problems.extend(_validate_scalars(label, fam))
        problems.extend(_validate_sizes(label, fam))
    labels = {f.get("label") for f in entries}
    aliases = {
        a for f in entries if isinstance(f.get("aliases"), list) for a in f["aliases"]
    }
    if data.get("default") not in labels | aliases:
        problems.append(f"default {data.get('default')!r} is not a family label")
    return problems


def build_families(data: Dict[str, Any]) -> Tuple[Family, ...]:
    """Build ``Family`` records from a table that passed ``validate_table``."""
    return tuple(
        Family(
            label=fam["label"],
            aliases=tuple(fam.get("aliases", ())),
            models=fam["models"],
            group=fam["group"],
            vae_ratio=fam["vaeRatio"],
            step=int(fam["step"]),
            megapixels=tuple(fam["megapixels"]),
            default=(fam["default"][0], fam["default"][1]),
            sizes={
                chip: tuple((w, h) for w, h in fam["sizes"].get(chip, ()))
                for chip in CHIPS
            },
        )
        for fam in data["families"]
    )
