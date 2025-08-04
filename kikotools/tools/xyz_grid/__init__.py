"""XYZ Grid nodes for ComfyUI parameter comparisons."""

from .controller.advanced_node import XYZPlotControllerAdvanced
from .combiner.node import ImageGridCombiner

NODE_CLASS_MAPPINGS = {
    "XYZPlotController": XYZPlotControllerAdvanced,
    "ImageGridCombiner": ImageGridCombiner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "XYZPlotController": "XYZ Plot Controller",
    "ImageGridCombiner": "Image Grid Combiner",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "XYZPlotControllerAdvanced", "ImageGridCombiner"]