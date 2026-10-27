"""Pure size math for the Model Resolution Picker node."""

import math

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
