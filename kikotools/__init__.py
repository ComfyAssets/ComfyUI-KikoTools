"""
KikoTools package initialization and node registry
Handles automatic discovery and registration of all ComfyAssets tools
"""

from .tools.resolution_calculator import ResolutionCalculatorNode
from .tools.width_height_selector import WidthHeightSelectorNode
from .tools.seed_history import SeedHistoryNode
from .tools.sampler_combo import SamplerComboNode, SamplerComboCompactNode
from .tools.empty_latent_batch import EmptyLatentBatchNode
from .tools.kiko_save_image import KikoSaveImageNode
from .tools.image_to_multiple_of import ImageToMultipleOfNode
from .tools.image_scale_down_by import ImageScaleDownByNode
from .tools.gemini_prompt import GeminiPromptNode
from .tools.display_any import DisplayAnyNode
from .tools.display_text import DisplayTextNode

# ComfyUI node registration mappings
NODE_CLASS_MAPPINGS = {
    "ResolutionCalculator": ResolutionCalculatorNode,
    "WidthHeightSelector": WidthHeightSelectorNode,
    "SeedHistory": SeedHistoryNode,
    "SamplerCombo": SamplerComboNode,
    "SamplerComboCompact": SamplerComboCompactNode,
    "EmptyLatentBatch": EmptyLatentBatchNode,
    "KikoSaveImage": KikoSaveImageNode,
    "ImageToMultipleOf": ImageToMultipleOfNode,
    "ImageScaleDownBy": ImageScaleDownByNode,
    "GeminiPrompt": GeminiPromptNode,
    "DisplayAny": DisplayAnyNode,
    "DisplayText": DisplayTextNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionCalculator": "Resolution Calculator",
    "WidthHeightSelector": "Width Height Selector",
    "SeedHistory": "Seed History",
    "SamplerCombo": "Sampler Combo",
    "SamplerComboCompact": "Sampler Combo (Compact)",
    "EmptyLatentBatch": "Empty Latent Batch",
    "KikoSaveImage": "Kiko Save Image",
    "ImageToMultipleOf": "Image to Multiple of",
    "ImageScaleDownBy": "Image Scale Down By",
    "GeminiPrompt": "Gemini Prompt Engineer",
    "DisplayAny": "Display Any",
    "DisplayText": "Display Text",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
