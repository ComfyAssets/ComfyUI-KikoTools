"""XYZ Grid nodes for ComfyUI parameter comparisons."""

from .controller.power_node import XYZPlotController
from .combiner.node import ImageGridCombiner
from .prompt.node import XYZPrompt

NODE_CLASS_MAPPINGS = {
    "XYZPlotController": XYZPlotController,
    "ImageGridCombiner": ImageGridCombiner,
    "XYZPrompt": XYZPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "XYZPlotController": "XYZ Plot Controller",
    "ImageGridCombiner": "Image Grid Combiner",
    "XYZPrompt": "XYZ Prompt",
}

__all__ = ["XYZPlotController", "ImageGridCombiner", "XYZPrompt"]