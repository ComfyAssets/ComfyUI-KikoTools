"""Local Image Loader node for ComfyUI."""

import os
import json
import torch
from typing import Dict, Any, Tuple

from ...base.base_node import ComfyAssetsBaseNode
from .logic import load_image_from_path, create_empty_tensor


NODE_DIR = os.path.dirname(os.path.abspath(__file__))
SELECTIONS_FILE = os.path.join(NODE_DIR, "selections.json")
CONFIG_FILE = os.path.join(NODE_DIR, "config.json")


def load_selections() -> Dict[str, Any]:
    """Load node selections from file."""
    if not os.path.exists(SELECTIONS_FILE):
        return {}
    try:
        with open(SELECTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_selections(data: Dict[str, Any]) -> None:
    """Save node selections to file."""
    try:
        with open(SELECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"KikoLocalImageLoader: Error saving selections: {e}")


def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_config(data: Dict[str, Any]) -> None:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"KikoLocalImageLoader: Error saving config: {e}")


class LocalImageLoaderNode(ComfyAssetsBaseNode):
    """Node for loading images from local filesystem with a visual gallery interface."""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define input types for the node."""
        return {
            "required": {},
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = (
        "IMAGE",
        "STRING",
    )
    RETURN_NAMES = (
        "image",
        "info",
    )
    FUNCTION = "load_media"
    CATEGORY = "🫶 ComfyAssets/💾 Images"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Check if node state has changed."""
        if os.path.exists(SELECTIONS_FILE):
            return os.path.getmtime(SELECTIONS_FILE)
        return float("inf")

    def load_media(self, unique_id: str) -> Tuple[torch.Tensor, str]:
        """
        Load selected media based on node's unique ID.

        Args:
            unique_id: Unique identifier for this node instance

        Returns:
            Tuple of (image tensor, info string)
        """
        image_tensor = create_empty_tensor()
        info_string = ""

        selections = load_selections()
        node_selections = selections.get(str(unique_id), {})

        # Load image if selected
        image_selection = node_selections.get("image")
        if image_selection and image_selection.get("path"):
            image_path = image_selection["path"]
            if os.path.exists(image_path):
                try:
                    image_tensor, metadata = load_image_from_path(image_path)
                    info_string = json.dumps(metadata, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"KikoLocalImageLoader: Error loading image: {e}")

        return (image_tensor, info_string)


# Setup API routes
try:
    import server
    from aiohttp import web
    import urllib.parse
    import io
    from PIL import Image
    from .logic import scan_directory

    prompt_server = server.PromptServer.instance

    @prompt_server.routes.post("/kiko_local_image_loader/set_node_selection")
    async def set_node_selection(request):
        """API endpoint to set node selection."""
        try:
            data = await request.json()
            node_id = str(data.get("node_id"))
            path = data.get("path")
            media_type = data.get("type")

            if not all([node_id, path, media_type]):
                return web.json_response(
                    {"status": "error", "message": "Missing required data."}, status=400
                )

            selections = load_selections()
            if node_id not in selections:
                selections[node_id] = {}

            selections[node_id][media_type] = {"path": path}
            save_selections(selections)

            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    @prompt_server.routes.get("/kiko_local_image_loader/get_saved_paths")
    async def get_saved_paths(request):
        """API endpoint to get saved directory paths."""
        config = load_config()
        return web.json_response({"saved_paths": config.get("saved_paths", [])})

    @prompt_server.routes.post("/kiko_local_image_loader/save_paths")
    async def save_paths(request):
        """API endpoint to save directory paths."""
        try:
            data = await request.json()
            paths = data.get("paths", [])
            config = load_config()
            config["saved_paths"] = paths
            save_config(config)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    @prompt_server.routes.get("/kiko_local_image_loader/images")
    async def get_local_images(request):
        """API endpoint to get images from a directory."""
        directory = request.query.get("directory", "")

        if not directory or not os.path.isdir(directory):
            return web.json_response({"error": "Directory not found."}, status=404)

        # Normalize path to remove trailing slashes and resolve relative paths
        directory = os.path.normpath(directory)

        # Save last path
        config = load_config()
        config["last_path"] = directory
        save_config(config)

        show_videos = request.query.get("show_videos", "false").lower() == "true"
        show_audio = request.query.get("show_audio", "false").lower() == "true"
        hide_dot_folders = (
            request.query.get("hide_dot_folders", "true").lower() == "true"
        )

        page = int(request.query.get("page", 1))
        per_page = int(request.query.get("per_page", 50))
        sort_by = request.query.get("sort_by", "name")
        sort_order = request.query.get("sort_order", "asc")

        try:
            items = scan_directory(
                directory,
                show_videos,
                show_audio,
                sort_by,
                sort_order,
                hide_dot_folders,
            )

            # Get parent directory
            parent_directory = os.path.dirname(directory)
            if parent_directory == directory:
                parent_directory = None

            # Paginate results
            start = (page - 1) * per_page
            end = start + per_page
            paginated_items = items[start:end]

            return web.json_response(
                {
                    "items": paginated_items,
                    "total_pages": (len(items) + per_page - 1) // per_page,
                    "current_page": page,
                    "current_directory": directory,
                    "parent_directory": parent_directory,
                }
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @prompt_server.routes.get("/kiko_local_image_loader/get_last_path")
    async def get_last_path(request):
        """API endpoint to get last used directory path."""
        return web.json_response({"last_path": load_config().get("last_path", "")})

    @prompt_server.routes.get("/kiko_local_image_loader/list_directories")
    async def list_directories(request):
        """API endpoint to list directories for autocomplete."""
        path = request.query.get("path", "")

        try:
            # Handle empty path - show root or common starting points
            if not path:
                # Return filesystem root
                if os.name == "nt":  # Windows
                    import string

                    drives = [
                        f"{d}:\\"
                        for d in string.ascii_uppercase
                        if os.path.exists(f"{d}:\\")
                    ]
                    return web.json_response({"directories": drives})
                else:  # Unix/Linux/Mac
                    return web.json_response({"directories": ["/"]})

            # Normalize the path
            path = os.path.expanduser(path)  # Handle ~ for home directory

            # If path ends with separator, list contents of that directory
            if path.endswith(os.sep) or (os.name == "nt" and path.endswith("/")):
                if os.path.isdir(path):
                    try:
                        entries = os.listdir(path)
                        dirs = []
                        for entry in entries:
                            full_path = os.path.join(path, entry)
                            if os.path.isdir(full_path):
                                dirs.append(full_path)
                        dirs.sort(key=lambda x: x.lower())
                        return web.json_response(
                            {"directories": dirs[:50]}
                        )  # Limit results
                    except PermissionError:
                        return web.json_response(
                            {"directories": [], "error": "Permission denied"}
                        )
                else:
                    return web.json_response({"directories": []})

            # Otherwise, find matching directories in parent
            parent_dir = os.path.dirname(path)
            basename = os.path.basename(path).lower()

            if not parent_dir:
                # Handle root level on Unix
                if path.startswith("/"):
                    parent_dir = "/"
                    basename = path[1:].lower()
                else:
                    return web.json_response({"directories": []})

            if os.path.isdir(parent_dir):
                try:
                    entries = os.listdir(parent_dir)
                    dirs = []
                    for entry in entries:
                        full_path = os.path.join(parent_dir, entry)
                        if os.path.isdir(full_path) and entry.lower().startswith(
                            basename
                        ):
                            dirs.append(full_path)
                    dirs.sort(key=lambda x: x.lower())
                    return web.json_response(
                        {"directories": dirs[:50]}
                    )  # Limit results
                except PermissionError:
                    return web.json_response(
                        {"directories": [], "error": "Permission denied"}
                    )

            return web.json_response({"directories": []})
        except Exception as e:
            return web.json_response({"directories": [], "error": str(e)})

    @prompt_server.routes.get("/kiko_local_image_loader/thumbnail")
    async def get_thumbnail(request):
        """API endpoint to get image thumbnail."""
        filepath = request.query.get("filepath")
        if not filepath or ".." in filepath:
            return web.Response(status=400)

        filepath = urllib.parse.unquote(filepath)
        if not os.path.exists(filepath):
            return web.Response(status=404)

        try:
            img = Image.open(filepath)
            has_alpha = img.mode == "RGBA" or (
                img.mode == "P" and "transparency" in img.info
            )
            img = img.convert("RGBA") if has_alpha else img.convert("RGB")
            img.thumbnail([320, 320], Image.LANCZOS)

            buffer = io.BytesIO()
            format, content_type = (
                ("PNG", "image/png") if has_alpha else ("JPEG", "image/jpeg")
            )
            img.save(buffer, format=format, quality=90 if format == "JPEG" else None)
            buffer.seek(0)

            return web.Response(body=buffer.read(), content_type=content_type)
        except Exception as e:
            print(f"KikoLocalImageLoader: Error generating thumbnail: {e}")
            return web.Response(status=500)

    @prompt_server.routes.get("/kiko_local_image_loader/view")
    async def view_image(request):
        """API endpoint to view full image."""
        filepath = request.query.get("filepath")
        if not filepath or ".." in filepath:
            return web.Response(status=400)

        filepath = urllib.parse.unquote(filepath)
        if not os.path.exists(filepath):
            return web.Response(status=404)

        try:
            return web.FileResponse(filepath)
        except Exception:
            return web.Response(status=500)

except ImportError:
    # Server not available during testing
    pass
