"""
ComfyUI-KikoTools: Modular collection of custom ComfyUI nodes
All nodes are grouped under the "ComfyAssets" category
"""

import re
from pathlib import Path

try:
    from .kikotools import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
except ImportError:
    # Fallback for testing environment
    from kikotools import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# Tell ComfyUI where to find our JavaScript extensions
import os

WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# Import server components at module level to ensure they're available
try:
    from aiohttp import web
    from server import PromptServer
    import folder_paths

    print("[KikoTools] Server imports successful")

    # Register autocomplete endpoints directly
    @PromptServer.instance.routes.get("/kikotools/autocomplete/embeddings")
    async def get_embeddings(request):
        """API endpoint for getting list of embeddings with full paths."""
        print("[KikoTools] Embeddings endpoint called")
        try:
            embedding_files = folder_paths.get_filename_list("embeddings")
            print(f"[KikoTools] Found {len(embedding_files)} embedding files")
            # Return embeddings with their subdirectory paths, without extensions
            embeddings = []
            for f in embedding_files:
                # Remove extension but keep subdirectory path
                clean_path = os.path.splitext(f)[0]
                embeddings.append(
                    {
                        "file_name": clean_path,
                        "model_name": clean_path,
                        "name": os.path.basename(clean_path),
                        "path": clean_path,
                    }
                )
            if len(embeddings) > 0:
                print(f"[KikoTools] Sample embedding: {embeddings[0]}")
            print(f"[KikoTools] Returning {len(embeddings)} embeddings with paths")
            return web.json_response(embeddings)
        except Exception as e:
            print(f"[KikoTools] Error getting embeddings: {e}")
            import traceback

            traceback.print_exc()
            return web.json_response([])

    @PromptServer.instance.routes.get("/kikotools/autocomplete/loras")
    async def get_loras(request):
        """API endpoint for getting list of LoRAs."""
        print("[KikoTools] LoRA endpoint called")
        try:
            lora_files = folder_paths.get_filename_list("loras")
            print(f"[KikoTools] Found {len(lora_files)} LoRA files")
            # Return LoRAs with paths
            loras = []
            for f in lora_files:
                clean_path = os.path.splitext(f)[0]
                loras.append(
                    {
                        "name": os.path.basename(clean_path),
                        "path": clean_path,
                        "file": f,
                    }
                )
            print(f"[KikoTools] Returning {len(loras)} LoRAs")
            return web.json_response(loras)
        except Exception as e:
            print(f"[KikoTools] Error getting LoRAs: {e}")
            import traceback

            traceback.print_exc()
            return web.json_response([])

    print("[KikoTools] Autocomplete API endpoints registered successfully")
    print(
        "[KikoTools] Routes available: /kikotools/autocomplete/embeddings and /kikotools/autocomplete/loras"
    )

except ImportError as e:
    print(f"[KikoTools] Could not import server components: {e}")
except Exception as e:
    print(f"[KikoTools] Unexpected error setting up API: {e}")
    import traceback

    traceback.print_exc()

# API endpoints are registered above at module import time


def get_version():
    """Parse version from pyproject.toml"""
    try:
        pyproject_path = Path(__file__).parent / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return "unknown"


# Print startup message with loaded tools
print()
print(f"\033[94m[ComfyUI-KikoTools] Version:\033[0m {get_version()}")
for node_key, display_name in NODE_DISPLAY_NAME_MAPPINGS.items():
    print(f"🫶 \033[94mLoaded:\033[0m {display_name}")
print(f"\033[94mTotal: {len(NODE_CLASS_MAPPINGS)} tools loaded\033[0m")
print()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
