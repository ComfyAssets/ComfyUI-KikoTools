"""Model family table for the Model Resolution Picker node.

The data lives in ``families.json`` next to this module; it is loaded and
validated once at import (see ``table.py``). A shipped file that fails
validation is a startup error.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .table import (
    CHIPS,
    MIRROR,
    Family,
    Size,
    build_families,
    load_table,
    validate_table,
)

__all__ = [
    "CHIPS",
    "MIRROR",
    "Family",
    "Size",
    "FAMILIES",
    "DEFAULT_FAMILY",
    "family_labels",
    "resolve_family",
    "families_payload",
    "load_shipped_families",
]

TABLE_PATH = Path(__file__).with_name("families.json")


def load_shipped_families(path: Path = TABLE_PATH) -> Tuple[Tuple[Family, ...], str]:
    """Load and validate ``path``; return its families and default label."""
    data = load_table(path)
    problems = validate_table(data)
    if problems:
        listing = "\n  - ".join(problems)
        raise RuntimeError(f"invalid family table {path}:\n  - {listing}")
    return build_families(data), data["default"]


FAMILIES, DEFAULT_FAMILY = load_shipped_families()


def family_labels() -> List[str]:
    """Return every family label in display order."""
    return [family.label for family in FAMILIES]


def resolve_family(label: str) -> Optional[Family]:
    """Return the family matching ``label`` or one of its aliases, else None."""
    for family in FAMILIES:
        if label == family.label or label in family.aliases:
            return family
    return None


def families_payload() -> Dict[str, Any]:
    """Return the JSON-shaped table the frontend consumes."""
    return {
        "chips": list(CHIPS),
        "mirror": dict(MIRROR),
        "default": DEFAULT_FAMILY,
        "families": [
            {
                "label": family.label,
                "aliases": list(family.aliases),
                "models": family.models,
                "group": family.group,
                "vaeRatio": family.vae_ratio,
                "step": family.step,
                "megapixels": list(family.megapixels),
                "default": list(family.default),
                "sizes": {
                    chip: [list(size) for size in family.sizes.get(chip, ())]
                    for chip in CHIPS
                },
            }
            for family in FAMILIES
        ],
    }
