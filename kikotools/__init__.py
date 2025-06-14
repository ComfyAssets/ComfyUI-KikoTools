"""
KikoTools package initialization and node registry
Handles automatic discovery and registration of all ComfyAssets tools
"""

from .tools.resolution_calculator import ResolutionCalculatorNode

# ComfyUI node registration mappings
NODE_CLASS_MAPPINGS = {
    "ResolutionCalculator": ResolutionCalculatorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionCalculator": "Resolution Calculator",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
