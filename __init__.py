"""
ComfyUI-KikoTools: Modular collection of custom ComfyUI nodes
All nodes are grouped under the "ComfyAssets" category
"""

from .kikotools import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Tell ComfyUI where to find our JavaScript extensions
WEB_DIRECTORY = "./web"

# Print startup message with loaded tools
print("\033[94m[ComfyUI-KikoTools]\033[0m")
for node_key, display_name in NODE_DISPLAY_NAME_MAPPINGS.items():
    print(f"🫶 \033[94m[Loaded:\033[0m {display_name}")
print(f"\033[94mTotal: {len(NODE_CLASS_MAPPINGS)} tools loaded\033[0m")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
