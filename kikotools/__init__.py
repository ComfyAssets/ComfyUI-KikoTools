"""
KikoTools package initialization and node registry
Handles automatic discovery and registration of all ComfyAssets tools
"""

from .tools.resolution_calculator import ResolutionCalculatorNode
from .tools.width_height_selector import WidthHeightSelectorNode

# ComfyUI node registration mappings
NODE_CLASS_MAPPINGS = {
    "ResolutionCalculator": ResolutionCalculatorNode,
    "WidthHeightSelector": WidthHeightSelectorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionCalculator": "Resolution Calculator",
    "WidthHeightSelector": "Width Height Selector",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
