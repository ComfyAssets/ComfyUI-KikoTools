"""Preset definitions for Width Height Selector."""

from typing import Dict, Tuple

# SDXL optimized presets (~1 megapixel, dimensions divisible by 8)
SDXL_PRESETS: Dict[str, Tuple[int, int]] = {
    # Square
    "1024×1024": (1024, 1024),  # 1:1 - Base SDXL resolution
    # Portrait ratios
    "896×1152": (896, 1152),  # 7:9 - Moderate portrait
    "832×1216": (832, 1216),  # 13:19 - Standard portrait
    "768×1344": (768, 1344),  # 4:7 - Tall portrait
    "640×1536": (640, 1536),  # 5:12 - Very tall portrait
    # Landscape ratios
    "1152×896": (1152, 896),  # 9:7 - Moderate landscape
    "1216×832": (1216, 832),  # 19:13 - Standard landscape
    "1344×768": (1344, 768),  # 7:4 - Wide landscape
    "1536×640": (1536, 640),  # 12:5 - Very wide landscape
}

# FLUX optimized presets (higher resolution, flexible ratios)
FLUX_PRESETS: Dict[str, Tuple[int, int]] = {
    # Recommended high-quality resolutions
    "1920×1080": (1920, 1080),  # 16:9 - Full HD landscape
    "1536×1536": (1536, 1536),  # 1:1 - High-res square
    "1280×768": (1280, 768),  # 5:3 - Wide landscape
    "768×1280": (768, 1280),  # 3:5 - Tall portrait
    # Alternative quality resolutions
    "1440×1080": (1440, 1080),  # 4:3 - Classic aspect ratio
    "1080×1440": (1080, 1440),  # 3:4 - Classic portrait
    "1728×1152": (1728, 1152),  # 3:2 - Photography standard
    "1152×1728": (1152, 1728),  # 2:3 - Portrait photography
}

# Ultra-wide and modern aspect ratios
ULTRA_WIDE_PRESETS: Dict[str, Tuple[int, int]] = {
    # Ultra-wide landscape (21:9 and variants)
    "2560×1080": (2560, 1080),  # 64:27 - Ultra-wide gaming
    "2048×768": (2048, 768),  # 8:3 - Wide cinematic
    "1792×768": (1792, 768),  # 7:3 - Panoramic
    # Ultra-wide portrait
    "1080×2560": (1080, 2560),  # 27:64 - Mobile ultra-tall
    "768×2048": (768, 2048),  # 3:8 - Vertical cinematic
    "768×1792": (768, 1792),  # 3:7 - Vertical panoramic
    # Extreme ratios
    "2304×768": (2304, 768),  # 3:1 - Banner landscape
    "768×2304": (768, 2304),  # 1:3 - Banner portrait
}

# Combined preset options for ComfyUI dropdown
PRESET_OPTIONS: Dict[str, Tuple[int, int]] = {
    "custom": (0, 0),  # Special case for custom dimensions
    **SDXL_PRESETS,
    **FLUX_PRESETS,
    **ULTRA_WIDE_PRESETS,
}

# Organized preset categories for better UX
PRESET_CATEGORIES = {
    "Custom": ["custom"],
    "SDXL Square": ["1024×1024"],
    "SDXL Portrait": ["896×1152", "832×1216", "768×1344", "640×1536"],
    "SDXL Landscape": ["1152×896", "1216×832", "1344×768", "1536×640"],
    "FLUX Recommended": ["1920×1080", "1536×1536", "1280×768", "768×1280"],
    "FLUX Alternative": ["1440×1080", "1080×1440", "1728×1152", "1152×1728"],
    "Ultra-Wide Landscape": ["2560×1080", "2048×768", "1792×768", "2304×768"],
    "Ultra-Wide Portrait": ["1080×2560", "768×2048", "768×1792", "768×2304"],
}

# Preset descriptions for tooltips
PRESET_DESCRIPTIONS = {
    # SDXL presets
    "1024×1024": "SDXL base resolution - perfect square",
    "896×1152": "SDXL portrait 7:9 - moderate portrait",
    "832×1216": "SDXL portrait 13:19 - standard portrait",
    "768×1344": "SDXL portrait 4:7 - tall portrait",
    "640×1536": "SDXL portrait 5:12 - very tall portrait",
    "1152×896": "SDXL landscape 9:7 - moderate landscape",
    "1216×832": "SDXL landscape 19:13 - standard landscape",
    "1344×768": "SDXL landscape 7:4 - wide landscape",
    "1536×640": "SDXL landscape 12:5 - very wide landscape",
    # FLUX presets
    "1920×1080": "FLUX Full HD 16:9 - best quality/speed balance",
    "1536×1536": "FLUX high-res square - premium quality",
    "1280×768": "FLUX 5:3 landscape - cinematic wide",
    "768×1280": "FLUX 3:5 portrait - mobile optimized",
    "1440×1080": "FLUX 4:3 classic - traditional aspect ratio",
    "1080×1440": "FLUX 3:4 portrait - classic portrait",
    "1728×1152": "FLUX 3:2 photo - photography standard",
    "1152×1728": "FLUX 2:3 portrait - portrait photography",
    # Ultra-wide presets
    "2560×1080": "Ultra-wide 64:27 - gaming/panoramic",
    "2048×768": "Wide cinematic 8:3 - movie aspect",
    "1792×768": "Panoramic 7:3 - landscape vista",
    "2304×768": "Banner 3:1 - extreme wide banner",
    "1080×2560": "Mobile ultra-tall 27:64 - modern phones",
    "768×2048": "Vertical cinematic 3:8 - portrait video",
    "768×1792": "Vertical panoramic 3:7 - tall vista",
    "768×2304": "Vertical banner 1:3 - extreme tall banner",
}

# Model-specific recommendations
MODEL_RECOMMENDATIONS = {
    "SDXL": list(SDXL_PRESETS.keys()),
    "FLUX": list(FLUX_PRESETS.keys()),
    "Ultra-Wide": list(ULTRA_WIDE_PRESETS.keys()),
}


def get_preset_category(preset_name: str) -> str:
    """Get the category for a given preset name."""
    for category, presets in PRESET_CATEGORIES.items():
        if preset_name in presets:
            return category
    return "Unknown"


def get_model_recommendation(preset_name: str) -> str:
    """Get model recommendation for a given preset."""
    if preset_name in SDXL_PRESETS:
        return "Optimized for SDXL"
    elif preset_name in FLUX_PRESETS:
        return "Optimized for FLUX"
    elif preset_name in ULTRA_WIDE_PRESETS:
        return "Modern ultra-wide ratios"
    else:
        return "Custom dimensions"


def validate_preset_dimensions() -> bool:
    """Validate that all presets meet ComfyUI requirements."""
    all_presets = {**SDXL_PRESETS, **FLUX_PRESETS, **ULTRA_WIDE_PRESETS}

    for preset_name, (width, height) in all_presets.items():
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


# Validate presets on import
if not validate_preset_dimensions():
    raise ValueError("Preset validation failed - check console for details")
