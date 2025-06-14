"""
ComfyUI-KikoTools: Modular collection of custom ComfyUI nodes
All nodes are grouped under the "ComfyAssets" category
"""

from .kikotools import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Tell ComfyUI where to find our JavaScript extensions
WEB_DIRECTORY = "./web"

# Print startup message
print("\033[94m[ComfyUI-KikoTools] Loaded with swap button support!\033[0m")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
