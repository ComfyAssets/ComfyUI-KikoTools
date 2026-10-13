"""Local Image Loader node for ComfyUI."""

import io
import json
import logging
import os
from typing import Any, Dict, List, Tuple

import torch

from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    create_empty_tensor,
    is_allowed_image_path,
    is_allowed_media_path,
    is_too_broad_root,
    is_within_roots,
    list_subdirectories,
    load_image_from_path,
    resolve_path,
    scan_directory,
)

try:
    from aiohttp import web
except ImportError:  # pragma: no cover - aiohttp ships with ComfyUI
    web = None

logger = logging.getLogger(__name__)

MEDIA_KINDS = ("image", "video", "audio")
MAX_PER_PAGE = 200
DEFAULT_PER_PAGE = 50
MAX_DIRECTORY_SUGGESTIONS = 50

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
        logger.error("Error saving selections: %s", e)


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
        logger.error("Error saving config: %s", e)


def get_allowed_roots() -> List[str]:
    """Directories whose contents may be served: saved paths + ComfyUI in/out."""
    roots: List[str] = []
    saved = load_config().get("saved_paths", [])
    if isinstance(saved, list):
        # Skip broad roots saved before save_paths refused them
        roots.extend(
            p for p in saved if isinstance(p, str) and p and not is_too_broad_root(p)
        )
    try:
        import folder_paths

        for getter in ("get_input_directory", "get_output_directory"):
            value = getattr(folder_paths, getter)()
            if isinstance(value, str) and value:
                roots.append(value)
    except Exception:  # folder_paths missing or misbehaving outside ComfyUI
        pass
    return roots


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
            # Load the resolved path we validated, so a symlink swapped after
            # the check can't redirect the read.
            image_path = resolve_path(image_selection["path"])
            if not is_allowed_image_path(image_path, get_allowed_roots()):
                # selections.json may have been tampered with
                logger.warning("Refusing to load disallowed path: %s", image_path)
            elif os.path.exists(image_path):
                try:
                    image_tensor, metadata = load_image_from_path(image_path)
                    info_string = json.dumps(metadata, indent=4, ensure_ascii=False)
                except Exception as e:
                    logger.error("Error loading image: %s", e)

        return (image_tensor, info_string)


# ---------------------------------------------------------------------------
# API route handlers (module level so they can be tested without a server)
# ---------------------------------------------------------------------------


def _error(status: int, message: str):
    return web.json_response({"status": "error", "error": message}, status=status)


def _check_file(filepath: Any, kinds: Tuple[str, ...] = ("image",)):
    """Validate a requested file. Returns (resolved_path, error_response)."""
    if not isinstance(filepath, str) or not filepath or "\0" in filepath:
        return None, web.Response(status=400)
    real = resolve_path(filepath)
    if not is_allowed_media_path(real, get_allowed_roots(), kinds):
        return None, web.Response(status=403)
    if not os.path.isfile(real):
        return None, web.Response(status=404)
    return real, None


def _parse_paging(query) -> Tuple[int, int]:
    """Parse page/per_page; raises ValueError on garbage."""
    page = int(query.get("page", 1))
    per_page = int(query.get("per_page", DEFAULT_PER_PAGE))
    if page < 1:
        raise ValueError("page must be >= 1")
    return page, max(1, min(per_page, MAX_PER_PAGE))


async def set_node_selection(request):
    """Store the selected image for a node (image files in allowed roots only)."""
    try:
        data = await request.json()
    except Exception:
        return _error(400, "Invalid JSON.")
    if not isinstance(data, dict):
        return _error(400, "Invalid payload.")

    node_id = data.get("node_id")
    path = data.get("path")
    media_type = data.get("type")
    if (
        node_id is None
        or not isinstance(path, str)
        or not path
        or "\0" in path
        or not isinstance(media_type, str)
        or not media_type
    ):
        return _error(400, "Missing required data.")

    # The frontend also selects video/audio; load_media only ever reads images.
    if not is_allowed_media_path(path, get_allowed_roots(), MEDIA_KINDS):
        return _error(403, "Path not allowed.")

    selections = load_selections()
    selections.setdefault(str(node_id), {})[media_type] = {"path": path}
    save_selections(selections)
    return web.json_response({"status": "ok"})


async def get_saved_paths(request):
    """Return saved directory paths."""
    return web.json_response({"saved_paths": load_config().get("saved_paths", [])})


async def save_paths(request):
    """Persist the list of saved directory paths."""
    try:
        data = await request.json()
    except Exception:
        return _error(400, "Invalid JSON.")
    paths = data.get("paths", []) if isinstance(data, dict) else None
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        return _error(400, "paths must be a list of strings.")
    too_broad = [p for p in paths if is_too_broad_root(p)]
    if too_broad:
        return _error(
            400,
            f"Folder too broad to share: {', '.join(too_broad)}. "
            "Pick a folder inside your home directory or another media folder.",
        )
    config = load_config()
    config["saved_paths"] = paths
    save_config(config)
    return web.json_response({"status": "ok"})


async def get_local_images(request):
    """List images and sub-directories of a directory inside an allowed root."""
    query = request.query
    directory = query.get("directory", "")
    if not directory or "\0" in directory:
        return _error(400, "Directory is required.")
    try:
        page, per_page = _parse_paging(query)
    except ValueError:
        return _error(400, "Invalid page or per_page.")

    if not is_within_roots(directory, get_allowed_roots()):
        return _error(403, "Directory not allowed.")
    real = resolve_path(directory)
    if not os.path.isdir(real):
        return _error(404, "Directory not found.")

    # Normalize path (trailing slashes etc.) but keep the user-visible spelling
    directory = os.path.normpath(directory)

    config = load_config()
    config["last_path"] = directory
    save_config(config)

    show_videos = query.get("show_videos", "false").lower() == "true"
    show_audio = query.get("show_audio", "false").lower() == "true"
    hide_dot_folders = query.get("hide_dot_folders", "true").lower() == "true"

    try:
        items = scan_directory(
            directory,
            show_videos,
            show_audio,
            query.get("sort_by", "name"),
            query.get("sort_order", "asc"),
            hide_dot_folders,
        )
    except Exception:
        logger.exception("Error scanning directory %s", directory)
        return _error(500, "Error reading directory.")

    # Do not offer navigation above the allowed roots
    parent_directory = os.path.dirname(directory)
    if parent_directory == directory or not is_within_roots(
        parent_directory, get_allowed_roots()
    ):
        parent_directory = None

    start = (page - 1) * per_page
    return web.json_response(
        {
            "items": items[start : start + per_page],
            "total_pages": (len(items) + per_page - 1) // per_page,
            "current_page": page,
            "current_directory": directory,
            "parent_directory": parent_directory,
        }
    )


async def get_last_path(request):
    """Return the last used directory path."""
    return web.json_response({"last_path": load_config().get("last_path", "")})


async def list_directories(request):
    """List directory names for the folder-picker autocomplete.

    Trade-off: this is how users browse to a location that is not yet a saved
    root, so it is intentionally NOT restricted to the allowed roots. It only
    ever returns directory paths (never files), capped at
    MAX_DIRECTORY_SUGGESTIONS; file contents stay protected by the root and
    extension checks on every other route.
    """
    path = request.query.get("path", "")
    if "\0" in path:
        return web.json_response({"directories": []})

    try:
        if not path:
            if os.name == "nt":
                import string

                drives = [
                    f"{d}:\\"
                    for d in string.ascii_uppercase
                    if os.path.exists(f"{d}:\\")
                ]
                return web.json_response({"directories": drives})
            return web.json_response({"directories": [os.sep]})

        dirs = list_subdirectories(os.path.expanduser(path), MAX_DIRECTORY_SUGGESTIONS)
        return web.json_response({"directories": dirs})
    except PermissionError:
        return web.json_response({"directories": [], "error": "Permission denied"})
    except Exception:
        logger.exception("Error listing directories for %s", path)
        return web.json_response(
            {"directories": [], "error": "Error listing directories"}
        )


async def get_thumbnail(request):
    """Return a thumbnail of an allowed image."""
    real, error = _check_file(request.query.get("filepath"))
    if error is not None:
        return error

    try:
        from PIL import Image

        with Image.open(real) as img:
            has_alpha = img.mode == "RGBA" or (
                img.mode == "P" and "transparency" in img.info
            )
            img = img.convert("RGBA") if has_alpha else img.convert("RGB")
            img.thumbnail([320, 320], Image.LANCZOS)

            buffer = io.BytesIO()
            fmt, content_type = (
                ("PNG", "image/png") if has_alpha else ("JPEG", "image/jpeg")
            )
            img.save(buffer, format=fmt, quality=90 if fmt == "JPEG" else None)
        return web.Response(body=buffer.getvalue(), content_type=content_type)
    except Exception:
        logger.exception("Error generating thumbnail for %s", real)
        return web.Response(status=500)


async def view_image(request):
    """Serve a full-size allowed media file (image, video or audio)."""
    real, error = _check_file(request.query.get("filepath"), MEDIA_KINDS)
    if error is not None:
        return error
    return web.FileResponse(real)


# Setup API routes
try:
    import server

    prompt_server = server.PromptServer.instance
    _routes = prompt_server.routes
    _prefix = "/kiko_local_image_loader"
    _routes.post(f"{_prefix}/set_node_selection")(set_node_selection)
    _routes.get(f"{_prefix}/get_saved_paths")(get_saved_paths)
    _routes.post(f"{_prefix}/save_paths")(save_paths)
    _routes.get(f"{_prefix}/images")(get_local_images)
    _routes.get(f"{_prefix}/get_last_path")(get_last_path)
    _routes.get(f"{_prefix}/list_directories")(list_directories)
    _routes.get(f"{_prefix}/thumbnail")(get_thumbnail)
    _routes.get(f"{_prefix}/view")(view_image)
except ImportError:
    # Server not available during testing
    pass
