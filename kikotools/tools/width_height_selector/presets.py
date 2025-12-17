"""Preset definitions for Width Height Selector."""

from typing import Dict, Tuple, NamedTuple
from fractions import Fraction


class PresetMetadata(NamedTuple):
    """Metadata for a resolution preset."""

    width: int
    height: int
    aspect_ratio: str
    aspect_decimal: float
    megapixels: float
    model_group: str
    category: str
    description: str


def calculate_aspect_ratio(width: int, height: int) -> Tuple[str, float]:
    """Calculate aspect ratio as string and decimal."""
    fraction = Fraction(width, height)
    decimal = width / height
    return f"{fraction.numerator}:{fraction.denominator}", decimal


# Enhanced preset definitions with full metadata
PRESET_METADATA: Dict[str, PresetMetadata] = {
    # SDXL Presets - Square
    "1024×1024": PresetMetadata(
        1024,
        1024,
        "1:1",
        1.0,
        1.05,
        "SDXL",
        "Square",
        "SDXL base resolution - perfect square",
    ),
    # SDXL Presets - Portrait
    "896×1152": PresetMetadata(
        896,
        1152,
        "7:9",
        0.778,
        1.03,
        "SDXL",
        "Portrait",
        "SDXL portrait 7:9 - moderate portrait",
    ),
    "832×1216": PresetMetadata(
        832,
        1216,
        "13:19",
        0.684,
        1.01,
        "SDXL",
        "Portrait",
        "SDXL portrait 13:19 - standard portrait",
    ),
    "768×1344": PresetMetadata(
        768,
        1344,
        "4:7",
        0.571,
        1.03,
        "SDXL",
        "Portrait",
        "SDXL portrait 4:7 - tall portrait",
    ),
    "640×1536": PresetMetadata(
        640,
        1536,
        "5:12",
        0.417,
        0.98,
        "SDXL",
        "Portrait",
        "SDXL portrait 5:12 - very tall portrait",
    ),
    "704×1408": PresetMetadata(
        704,
        1408,
        "1:2",
        0.5,
        0.99,
        "SDXL",
        "Portrait",
        "SDXL portrait 1:2 - extreme tall portrait",
    ),
    "960×1024": PresetMetadata(
        960,
        1024,
        "15:16",
        0.938,
        0.98,
        "SDXL",
        "Portrait",
        "SDXL near-square portrait - subtle portrait",
    ),
    "720×1280": PresetMetadata(
        720,
        1280,
        "9:16",
        0.5625,
        0.92,
        "SDXL",
        "Portrait",
        "SDXL portrait 9:16 - vertical video/mobile",
    ),
    # SDXL Presets - Landscape
    "1024×960": PresetMetadata(
        1024,
        960,
        "16:15",
        1.067,
        0.98,
        "SDXL",
        "Landscape",
        "SDXL near-square landscape - subtle landscape",
    ),
    "1152×896": PresetMetadata(
        1152,
        896,
        "9:7",
        1.286,
        1.03,
        "SDXL",
        "Landscape",
        "SDXL landscape 9:7 - moderate landscape",
    ),
    "1216×832": PresetMetadata(
        1216,
        832,
        "19:13",
        1.462,
        1.01,
        "SDXL",
        "Landscape",
        "SDXL landscape 19:13 - standard landscape",
    ),
    "1344×768": PresetMetadata(
        1344,
        768,
        "7:4",
        1.750,
        1.03,
        "SDXL",
        "Landscape",
        "SDXL landscape 7:4 - wide landscape",
    ),
    "1536×640": PresetMetadata(
        1536,
        640,
        "12:5",
        2.400,
        0.98,
        "SDXL",
        "Landscape",
        "SDXL landscape 12:5 - very wide landscape",
    ),
    "1728×576": PresetMetadata(
        1728,
        576,
        "3:1",
        3.0,
        1.0,
        "SDXL",
        "Landscape",
        "SDXL landscape 3:1 - extreme wide panoramic",
    ),
    "1280×720": PresetMetadata(
        1280,
        720,
        "16:9",
        1.778,
        0.92,
        "SDXL",
        "Landscape",
        "SDXL landscape 16:9 - HD widescreen video",
    ),
    # FLUX Presets - High Quality
    "1920×1080": PresetMetadata(
        1920,
        1080,
        "16:9",
        1.778,
        2.07,
        "FLUX",
        "Cinematic",
        "FLUX Full HD 16:9 - best quality/speed balance",
    ),
    "1536×1536": PresetMetadata(
        1536,
        1536,
        "1:1",
        1.0,
        2.36,
        "FLUX",
        "Square",
        "FLUX high-res square - premium quality",
    ),
    "1280×768": PresetMetadata(
        1280,
        768,
        "5:3",
        1.667,
        0.98,
        "FLUX",
        "Cinematic",
        "FLUX 5:3 landscape - cinematic wide",
    ),
    "768×1280": PresetMetadata(
        768,
        1280,
        "3:5",
        0.600,
        0.98,
        "FLUX",
        "Portrait",
        "FLUX 3:5 portrait - mobile optimized",
    ),
    # FLUX Presets - Alternative
    "1440×1080": PresetMetadata(
        1440,
        1080,
        "4:3",
        1.333,
        1.56,
        "FLUX",
        "Classic",
        "FLUX 4:3 classic - traditional aspect ratio",
    ),
    "1080×1440": PresetMetadata(
        1080,
        1440,
        "3:4",
        0.750,
        1.56,
        "FLUX",
        "Portrait",
        "FLUX 3:4 portrait - classic portrait",
    ),
    "1728×1152": PresetMetadata(
        1728,
        1152,
        "3:2",
        1.500,
        1.99,
        "FLUX",
        "Photography",
        "FLUX 3:2 photo - photography standard",
    ),
    "1152×1728": PresetMetadata(
        1152,
        1728,
        "2:3",
        0.667,
        1.99,
        "FLUX",
        "Portrait",
        "FLUX 2:3 portrait - portrait photography",
    ),
    # Ultra-Wide Presets - Landscape
    "2560×1080": PresetMetadata(
        2560,
        1080,
        "64:27",
        2.370,
        2.76,
        "Ultra-Wide",
        "Gaming",
        "Ultra-wide 64:27 - gaming/panoramic",
    ),
    "2048×768": PresetMetadata(
        2048,
        768,
        "8:3",
        2.667,
        1.57,
        "Ultra-Wide",
        "Cinematic",
        "Wide cinematic 8:3 - movie aspect",
    ),
    "1792×768": PresetMetadata(
        1792,
        768,
        "7:3",
        2.333,
        1.38,
        "Ultra-Wide",
        "Panoramic",
        "Panoramic 7:3 - landscape vista",
    ),
    "2304×768": PresetMetadata(
        2304,
        768,
        "3:1",
        3.000,
        1.77,
        "Ultra-Wide",
        "Banner",
        "Banner 3:1 - extreme wide banner",
    ),
    # Ultra-Wide Presets - Portrait
    "1080×2560": PresetMetadata(
        1080,
        2560,
        "27:64",
        0.422,
        2.76,
        "Ultra-Wide",
        "Mobile",
        "Mobile ultra-tall 27:64 - modern phones",
    ),
    "768×2048": PresetMetadata(
        768,
        2048,
        "3:8",
        0.375,
        1.57,
        "Ultra-Wide",
        "Vertical",
        "Vertical cinematic 3:8 - portrait video",
    ),
    "768×1792": PresetMetadata(
        768,
        1792,
        "3:7",
        0.429,
        1.38,
        "Ultra-Wide",
        "Vertical",
        "Vertical panoramic 3:7 - tall vista",
    ),
    "768×2304": PresetMetadata(
        768,
        2304,
        "1:3",
        0.333,
        1.77,
        "Ultra-Wide",
        "Banner",
        "Vertical banner 1:3 - extreme tall banner",
    ),
    # Qwen Presets
    "1328×1328": PresetMetadata(
        1328,
        1328,
        "1:1",
        1.0,
        1.76,
        "Qwen",
        "Square",
        "Qwen square 1:1 - optimized square",
    ),
    "1664×928": PresetMetadata(
        1664,
        928,
        "16:9",
        1.793,
        1.54,
        "Qwen",
        "Landscape",
        "Qwen landscape 16:9 - widescreen format",
    ),
    "928×1664": PresetMetadata(
        928,
        1664,
        "9:16",
        0.558,
        1.54,
        "Qwen",
        "Portrait",
        "Qwen portrait 9:16 - vertical format",
    ),
    "1472×1104": PresetMetadata(
        1472,
        1104,
        "4:3",
        1.333,
        1.62,
        "Qwen",
        "Landscape",
        "Qwen landscape 4:3 - classic landscape",
    ),
    "1104×1472": PresetMetadata(
        1104,
        1472,
        "3:4",
        0.750,
        1.62,
        "Qwen",
        "Portrait",
        "Qwen portrait 3:4 - classic portrait",
    ),
    "1584×1056": PresetMetadata(
        1584,
        1056,
        "3:2",
        1.500,
        1.67,
        "Qwen",
        "Landscape",
        "Qwen landscape 3:2 - photography standard",
    ),
    "1056×1584": PresetMetadata(
        1056,
        1584,
        "2:3",
        0.667,
        1.67,
        "Qwen",
        "Portrait",
        "Qwen portrait 2:3 - portrait photography",
    ),
    "2080×688": PresetMetadata(
        2080,
        688,
        "3:1",
        3.023,
        1.43,
        "Qwen",
        "Landscape",
        "Qwen experimental landscape 3:1 - ultra-wide",
    ),
    "688×2080": PresetMetadata(
        688,
        2080,
        "1:3",
        0.331,
        1.43,
        "Qwen",
        "Portrait",
        "Qwen experimental portrait 1:3 - ultra-tall",
    ),
}

# Legacy compatibility - maintain old preset dictionaries
SDXL_PRESETS: Dict[str, Tuple[int, int]] = {
    k: (v.width, v.height)
    for k, v in PRESET_METADATA.items()
    if v.model_group == "SDXL"
}

FLUX_PRESETS: Dict[str, Tuple[int, int]] = {
    k: (v.width, v.height)
    for k, v in PRESET_METADATA.items()
    if v.model_group == "FLUX"
}

ULTRA_WIDE_PRESETS: Dict[str, Tuple[int, int]] = {
    k: (v.width, v.height)
    for k, v in PRESET_METADATA.items()
    if v.model_group == "Ultra-Wide"
}

QWEN_PRESETS: Dict[str, Tuple[int, int]] = {
    k: (v.width, v.height)
    for k, v in PRESET_METADATA.items()
    if v.model_group == "Qwen"
}

# Combined preset options for ComfyUI dropdown
PRESET_OPTIONS: Dict[str, Tuple[int, int]] = {
    "custom": (0, 0),  # Special case for custom dimensions
    **{k: (v.width, v.height) for k, v in PRESET_METADATA.items()},
}

# Enhanced preset categories organized by model groups and aspect ratios
PRESET_CATEGORIES = {
    "Custom": ["custom"],
    # SDXL Categories
    "SDXL Square": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "SDXL" and v.category == "Square"
    ],
    "SDXL Portrait": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "SDXL" and v.category == "Portrait"
    ],
    "SDXL Landscape": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "SDXL" and v.category == "Landscape"
    ],
    # FLUX Categories
    "FLUX Square": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "FLUX" and v.category == "Square"
    ],
    "FLUX Portrait": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "FLUX" and v.category == "Portrait"
    ],
    "FLUX Cinematic": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "FLUX" and v.category == "Cinematic"
    ],
    "FLUX Classic": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "FLUX" and v.category == "Classic"
    ],
    "FLUX Photography": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "FLUX" and v.category == "Photography"
    ],
    # Ultra-Wide Categories
    "Ultra-Wide Gaming": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Ultra-Wide" and v.category == "Gaming"
    ],
    "Ultra-Wide Cinematic": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Ultra-Wide" and v.category == "Cinematic"
    ],
    "Ultra-Wide Panoramic": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Ultra-Wide" and v.category == "Panoramic"
    ],
    "Ultra-Wide Mobile": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Ultra-Wide" and v.category == "Mobile"
    ],
    "Ultra-Wide Vertical": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Ultra-Wide" and v.category == "Vertical"
    ],
    "Ultra-Wide Banner": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Ultra-Wide" and v.category == "Banner"
    ],
    # Qwen Categories
    "Qwen Square": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Qwen" and v.category == "Square"
    ],
    "Qwen Portrait": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Qwen" and v.category == "Portrait"
    ],
    "Qwen Landscape": [
        k
        for k, v in PRESET_METADATA.items()
        if v.model_group == "Qwen" and v.category == "Landscape"
    ],
}

# Legacy compatibility - preset descriptions
PRESET_DESCRIPTIONS = {k: v.description for k, v in PRESET_METADATA.items()}

# Model-specific recommendations with metadata
MODEL_RECOMMENDATIONS = {
    "SDXL": [k for k, v in PRESET_METADATA.items() if v.model_group == "SDXL"],
    "FLUX": [k for k, v in PRESET_METADATA.items() if v.model_group == "FLUX"],
    "Ultra-Wide": [
        k for k, v in PRESET_METADATA.items() if v.model_group == "Ultra-Wide"
    ],
    "Qwen": [k for k, v in PRESET_METADATA.items() if v.model_group == "Qwen"],
}


# New metadata-aware helper functions
def get_presets_by_model_group(model_group: str) -> Dict[str, PresetMetadata]:
    """Get all presets for a specific model group."""
    return {k: v for k, v in PRESET_METADATA.items() if v.model_group == model_group}


def get_presets_by_aspect_ratio(aspect_ratio: str) -> Dict[str, PresetMetadata]:
    """Get all presets with a specific aspect ratio."""
    return {k: v for k, v in PRESET_METADATA.items() if v.aspect_ratio == aspect_ratio}


def get_presets_by_category(category: str) -> Dict[str, PresetMetadata]:
    """Get all presets in a specific category."""
    return {k: v for k, v in PRESET_METADATA.items() if v.category == category}


def get_preset_metadata(preset_name: str) -> PresetMetadata:
    """Get metadata for a specific preset."""
    return PRESET_METADATA.get(
        preset_name,
        PresetMetadata(0, 0, "1:1", 1.0, 0.0, "Custom", "Custom", "Custom dimensions"),
    )


def get_preset_category(preset_name: str) -> str:
    """Get the category for a given preset name."""
    metadata = PRESET_METADATA.get(preset_name)
    if metadata:
        return metadata.category
    for category, presets in PRESET_CATEGORIES.items():
        if preset_name in presets:
            return category
    return "Unknown"


def get_model_recommendation(preset_name: str) -> str:
    """Get model recommendation for a given preset."""
    metadata = PRESET_METADATA.get(preset_name)
    if metadata:
        return f"Optimized for {metadata.model_group}"
    return "Custom dimensions"


def validate_preset_dimensions() -> bool:
    """Validate that all presets meet ComfyUI requirements."""
    for preset_name, metadata in PRESET_METADATA.items():
        width, height = metadata.width, metadata.height

        # Check divisible by 8
        if width % 8 != 0 or height % 8 != 0:
            print(
                f"ERROR: {preset_name} dimensions not divisible by 8: {width}×{height}"
            )
            return False

        # Check reasonable bounds
        if not (64 <= width <= 8192) or not (64 <= height <= 8192):
            print(f"ERROR: {preset_name} dimensions out of bounds: {width}×{height}")
            return False

    return True


# Additional validation for metadata consistency
def validate_metadata_consistency() -> bool:
    """Validate metadata consistency and completeness."""
    for preset_name, metadata in PRESET_METADATA.items():
        # Verify aspect ratio calculation
        expected_ratio, expected_decimal = calculate_aspect_ratio(
            metadata.width, metadata.height
        )
        if abs(metadata.aspect_decimal - expected_decimal) > 0.001:
            print(
                f"ERROR: {preset_name} aspect ratio mismatch: "
                f"expected {expected_decimal:.3f}, got {metadata.aspect_decimal}"
            )
            return False

        # Verify megapixel calculation
        expected_mp = (metadata.width * metadata.height) / 1_000_000
        if abs(metadata.megapixels - expected_mp) > 0.1:
            print(
                f"ERROR: {preset_name} megapixel mismatch: "
                f"expected {expected_mp:.2f}, got {metadata.megapixels}"
            )
            return False

    return True


# Validate presets on import
if not validate_preset_dimensions():
    raise ValueError("Preset validation failed - check console for details")

if not validate_metadata_consistency():
    raise ValueError("Metadata validation failed - check console for details")
