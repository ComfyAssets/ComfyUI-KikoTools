"""
KikoTools package initialization and node registry
Handles automatic discovery and registration of all ComfyAssets tools
"""

from .tools.resolution_calculator import ResolutionCalculatorNode
from .tools.width_height_selector import WidthHeightSelectorNode
from .tools.seed_history import SeedHistoryNode

# ComfyUI node registration mappings
NODE_CLASS_MAPPINGS = {
    "ResolutionCalculator": ResolutionCalculatorNode,
    "WidthHeightSelector": WidthHeightSelectorNode,
    "SeedHistory": SeedHistoryNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionCalculator": "Resolution Calculator",
    "WidthHeightSelector": "Width Height Selector",
    "SeedHistory": "Seed History",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
