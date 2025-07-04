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

# ComfyUI node registration mappings
NODE_CLASS_MAPPINGS = {
    "ResolutionCalculator": ResolutionCalculatorNode,
    "WidthHeightSelector": WidthHeightSelectorNode,
    "SeedHistory": SeedHistoryNode,
    "SamplerCombo": SamplerComboNode,
    "SamplerComboCompact": SamplerComboCompactNode,
    "EmptyLatentBatch": EmptyLatentBatchNode,
    "KikoSaveImage": KikoSaveImageNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionCalculator": "Resolution Calculator",
    "WidthHeightSelector": "Width Height Selector",
    "SeedHistory": "Seed History",
    "SamplerCombo": "Sampler Combo",
    "SamplerComboCompact": "Sampler Combo (Compact)",
    "EmptyLatentBatch": "Empty Latent Batch",
    "KikoSaveImage": "Kiko Save Image",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
