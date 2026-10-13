"""Core logic for Local Image Loader."""

import os
import json
import torch
import numpy as np
from PIL import Image
from typing import Tuple, Dict, Any, List, Optional, Iterable


def get_supported_extensions() -> Dict[str, List[str]]:
    """Get supported file extensions by type."""
    return {
        "image": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"],
        "video": [".mp4", ".webm", ".mov", ".mkv", ".avi"],
        "audio": [".mp3", ".wav", ".ogg", ".flac"],
    }


def resolve_path(path: Any) -> Optional[str]:
    """Resolve a user supplied path with realpath (symlinks and ``..``).

    Returns None for anything that is not a usable non-empty string.
    """
    if not isinstance(path, str) or not path or "\0" in path:
        return None
    return os.path.realpath(path)


def is_within_roots(path: Any, roots: Iterable[Any]) -> bool:
    """Return True if the resolved path is inside (or equal to) one of the roots.

    Uses os.path.commonpath on realpath-resolved values, so sibling
    directories sharing a string prefix, ``..`` and symlinks cannot escape.
    """
    real = resolve_path(path)
    if real is None:
        return False
    for root in roots:
        real_root = resolve_path(root)
        if real_root is None:
            continue
        try:
            if os.path.commonpath([real, real_root]) == real_root:
                return True
        except ValueError:  # different drives / mixed absolute and relative
            continue
    return False


def is_too_broad_root(path: Any, home: Optional[str] = None) -> bool:
    """Return True if path is unusable or too broad to be a saved root.

    Refuses filesystem/drive roots, the home directory itself and any
    ancestor of it (e.g. /home), since those would expose every media file
    a user owns. Folders inside home are fine.
    """
    real = resolve_path(path)
    if real is None:
        return True
    if os.path.dirname(real) == real:  # "/" or a drive root like "C:\\"
        return True
    real_home = os.path.realpath(home or os.path.expanduser("~"))
    try:
        return os.path.commonpath([real, real_home]) == real
    except ValueError:  # different drives
        return False


def is_allowed_media_path(
    path: Any, roots: Iterable[Any], kinds: Iterable[str] = ("image",)
) -> bool:
    """Return True if path is a media file of the given kinds inside a root.

    ``kinds`` are keys of get_supported_extensions() (image/video/audio).
    The extension is checked on the resolved path so a symlink named
    ``x.png`` pointing at a non-media file is refused.
    """
    real = resolve_path(path)
    if real is None:
        return False
    extensions = get_supported_extensions()
    allowed = {e for k in kinds for e in extensions.get(k, [])}
    if os.path.splitext(real)[1].lower() not in allowed:
        return False
    return is_within_roots(real, roots)


def is_allowed_image_path(path: Any, roots: Iterable[Any]) -> bool:
    """Return True if path is an image file located inside one of the roots."""
    return is_allowed_media_path(path, roots, ("image",))


def list_subdirectories(path: str, limit: int = 50) -> List[str]:
    """List sub-directory paths (never files) for the folder picker.

    If ``path`` ends with a separator, its child directories are returned;
    otherwise sibling directories whose name starts with the last component.
    May raise PermissionError.
    """
    if path.endswith(os.sep) or (os.name == "nt" and path.endswith("/")):
        parent_dir, prefix = path, ""
    else:
        parent_dir = os.path.dirname(path)
        prefix = os.path.basename(path).lower()
        if not parent_dir:
            return []

    if not os.path.isdir(parent_dir):
        return []

    dirs = [
        os.path.join(parent_dir, entry)
        for entry in os.listdir(parent_dir)
        if entry.lower().startswith(prefix)
        and os.path.isdir(os.path.join(parent_dir, entry))
    ]
    dirs.sort(key=lambda x: x.lower())
    return dirs[:limit]


def load_image_from_path(path: str) -> Tuple[torch.Tensor, Dict[str, Any]]:
    """
    Load an image from the given path and convert it to a tensor.

    Args:
        path: Path to the image file

    Returns:
        Tuple of (image tensor, metadata dict)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with Image.open(path) as img:
        # Convert to appropriate format
        if "A" in img.getbands():
            img_out = img.convert("RGBA")
        else:
            img_out = img.convert("RGB")

        # Convert to tensor
        img_array = np.array(img_out).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(img_array)[None,]

        # Collect metadata
        metadata = {
            "filename": os.path.basename(path),
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
            "format": img.format,
        }

        # Check for embedded metadata
        if "parameters" in img.info:
            metadata["parameters"] = img.info["parameters"]
        if "prompt" in img.info:
            try:
                metadata["prompt"] = json.loads(img.info["prompt"])
            except (json.JSONDecodeError, TypeError):
                metadata["prompt"] = img.info["prompt"]
        if "workflow" in img.info:
            try:
                metadata["workflow"] = json.loads(img.info["workflow"])
            except (json.JSONDecodeError, TypeError):
                metadata["workflow"] = img.info["workflow"]

    return image_tensor, metadata


def scan_directory(
    directory: str,
    show_videos: bool = False,
    show_audio: bool = False,
    sort_by: str = "name",
    sort_order: str = "asc",
    hide_dot_folders: bool = True,
) -> List[Dict[str, Any]]:
    """
    Scan a directory for supported media files.

    Args:
        directory: Directory path to scan
        show_videos: Include video files
        show_audio: Include audio files
        sort_by: Sort criteria ('name', 'date', 'size')
        sort_order: Sort order ('asc', 'desc')
        hide_dot_folders: Hide folders starting with a dot

    Returns:
        List of file information dictionaries
    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Not a directory: {directory}")

    extensions = get_supported_extensions()
    items = []

    for item in os.listdir(directory):
        # Skip dot folders/files if hide_dot_folders is enabled
        if hide_dot_folders and item.startswith("."):
            continue

        full_path = os.path.join(directory, item)

        try:
            stats = os.stat(full_path)
            item_data = {
                "path": full_path,
                "name": item,
                "mtime": stats.st_mtime,
                "size": stats.st_size,
            }

            if os.path.isdir(full_path):
                items.append({**item_data, "type": "dir"})
            else:
                ext = os.path.splitext(item)[1].lower()
                item_type = None

                if ext in extensions["image"]:
                    item_type = "image"
                elif show_videos and ext in extensions["video"]:
                    item_type = "video"
                elif show_audio and ext in extensions["audio"]:
                    item_type = "audio"

                if item_type:
                    items.append({**item_data, "type": item_type})

        except (PermissionError, FileNotFoundError):
            continue

    # Sort items
    reverse = sort_order == "desc"
    if sort_by == "date":
        items.sort(key=lambda x: x["mtime"], reverse=reverse)
    elif sort_by == "size":
        items.sort(key=lambda x: x.get("size", 0), reverse=reverse)
    else:  # name
        items.sort(key=lambda x: x["name"].lower(), reverse=reverse)

    # Directories first
    items.sort(key=lambda x: x["type"] != "dir")

    return items


def search_files(
    root_directory: str,
    query: str,
    show_videos: bool = False,
    show_audio: bool = False,
    max_results: int = 100,
) -> List[Dict[str, Any]]:
    """
    Recursively search for files matching the query.

    Args:
        root_directory: Root directory to start search
        query: Search query (case-insensitive filename match)
        show_videos: Include video files
        show_audio: Include audio files
        max_results: Maximum number of results to return

    Returns:
        List of file information dictionaries
    """
    if not os.path.isdir(root_directory):
        raise NotADirectoryError(f"Not a directory: {root_directory}")

    if not query or len(query.strip()) == 0:
        return []

    extensions = get_supported_extensions()
    results = []
    query_lower = query.lower().strip()

    def search_recursive(directory: str) -> None:
        """Recursively search directory."""
        if len(results) >= max_results:
            return

        try:
            items = os.listdir(directory)
        except (PermissionError, FileNotFoundError):
            return

        for item in items:
            if len(results) >= max_results:
                break

            full_path = os.path.join(directory, item)

            try:
                # Check if item name matches query
                if query_lower not in item.lower():
                    # If directory, search inside
                    if os.path.isdir(full_path):
                        search_recursive(full_path)
                    continue

                stats = os.stat(full_path)
                item_data = {
                    "path": full_path,
                    "name": item,
                    "directory": directory,
                    "mtime": stats.st_mtime,
                    "size": stats.st_size,
                }

                if os.path.isdir(full_path):
                    results.append({**item_data, "type": "dir"})
                    # Continue searching inside matching directories
                    search_recursive(full_path)
                else:
                    ext = os.path.splitext(item)[1].lower()
                    item_type = None

                    if ext in extensions["image"]:
                        item_type = "image"
                    elif show_videos and ext in extensions["video"]:
                        item_type = "video"
                    elif show_audio and ext in extensions["audio"]:
                        item_type = "audio"

                    if item_type:
                        results.append({**item_data, "type": item_type})

            except (PermissionError, FileNotFoundError):
                continue

    search_recursive(root_directory)

    # Sort by name
    results.sort(key=lambda x: x["name"].lower())

    return results


def create_empty_tensor() -> torch.Tensor:
    """Create an empty tensor for when no image is selected."""
    return torch.zeros(1, 1, 1, 4)
