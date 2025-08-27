"""Local Image Loader tool for KikoTools."""

from .node import LocalImageLoaderNode

NODE_CLASS_MAPPINGS = {
    "KikoLocalImageLoader": LocalImageLoaderNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KikoLocalImageLoader": "Local Image Loader",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
