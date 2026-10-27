"""Pure size math for the Model Resolution Picker node."""

import math
import re
from typing import Optional

MEGAPIXEL = 1_048_576

_ALIASES = {
    "8:5": "16:10",
    "5:8": "10:16",
    "7:3": "21:9",
    "3:7": "9:21",
}


def round_to_step(value: float, step: int, minimum: int = 64) -> int:
    """Round ``value`` to the nearest multiple of ``step``, never below ``minimum``.

    The result is also raised to the smallest multiple of ``step`` that is at
    least ``minimum``.
    """
    nearest = math.floor(value / step + 0.5) * step
    floor_multiple = math.ceil(minimum / step) * step
    return max(nearest, floor_multiple)


def generate_size(
    ratio_w: int, ratio_h: int, megapixels: float, step: int
) -> tuple[int, int]:
    """Return a ``(width, height)`` near ``megapixels`` with the given aspect ratio.

    Uses the core Resolution Selector scale ``sqrt(mp * MEGAPIXEL / (w * h))``
    and snaps each side to ``step`` via :func:`round_to_step`.
    """
    scale = math.sqrt(megapixels * MEGAPIXEL / (ratio_w * ratio_h))
    width = round_to_step(ratio_w * scale, step)
    height = round_to_step(ratio_h * scale, step)
    return width, height


def ratio_label(width: int, height: int) -> str:
    """Return the reduced ``W:H`` label for a size, with common aliases applied."""
    divisor = math.gcd(width, height)
    label = f"{width // divisor}:{height // divisor}"
    return _ALIASES.get(label, label)


_SIZE_LABEL = re.compile(r"^(\d+)×(\d+) - \S+ \(\d+\.\dMP\)$")


def size_label(width: int, height: int, ratio_text: str) -> str:
    """Return the dropdown label ``W×H - ratio (X.XMP)`` for a size."""
    return f"{width}×{height} - {ratio_text} ({width * height / 1_000_000:.1f}MP)"


def parse_size_label(text: object) -> Optional[tuple[int, int]]:
    """Return ``(width, height)`` from a :func:`size_label` string, else None."""
    if not isinstance(text, str):
        return None
    match = _SIZE_LABEL.match(text)
    if match is None:
        return None
    width, height = int(match.group(1)), int(match.group(2))
    return (width, height) if width > 0 and height > 0 else None
