"""XYZ Grid nodes for ComfyUI parameter comparisons."""

from .controller.simple_node import XYZPlotController
from .combiner.node import ImageGridCombiner

NODE_CLASS_MAPPINGS = {
    "XYZPlotController": XYZPlotController,
    "ImageGridCombiner": ImageGridCombiner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "XYZPlotController": "XYZ Plot Controller",
    "ImageGridCombiner": "Image Grid Combiner",
}

__all__ = ["XYZPlotController", "ImageGridCombiner"]