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
WEB_DIRECTORY = "./web"

def setup_autocomplete_api():
    """Setup API routes for embedding autocomplete."""
    try:
        from aiohttp import web
        from server import PromptServer
        from kikotools.tools.embedding_autocomplete.node import KikoEmbeddingAutocompleteAPI
        
        @PromptServer.instance.routes.get("/kikotools/autocomplete/suggestions")
        async def get_suggestions(request):
            """API endpoint for getting autocomplete suggestions."""
            prefix = request.query.get("prefix", "")
            max_results = int(request.query.get("max", 20))
            include_embeddings = request.query.get("embeddings", "true").lower() == "true"
            include_loras = request.query.get("loras", "true").lower() == "true"
            case_sensitive = request.query.get("case_sensitive", "false").lower() == "true"
            
            suggestions = KikoEmbeddingAutocompleteAPI.get_suggestions(
                prefix=prefix,
                max_results=max_results,
                include_embeddings=include_embeddings,
                include_loras=include_loras,
                case_sensitive=case_sensitive
            )
            
            return web.json_response(suggestions)
            
    except ImportError:
        pass  # Server not available when not in ComfyUI

# Setup API if available
setup_autocomplete_api()


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
