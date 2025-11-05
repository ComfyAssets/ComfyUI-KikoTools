"""Core logic for Local Image Loader."""

import os
import json
import torch
import numpy as np
from PIL import Image
from typing import Tuple, Dict, Any, List


def get_supported_extensions() -> Dict[str, List[str]]:
    """Get supported file extensions by type."""
    return {
        "image": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"],
        "video": [".mp4", ".webm", ".mov", ".mkv", ".avi"],
        "audio": [".mp3", ".wav", ".ogg", ".flac"],
    }


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
) -> List[Dict[str, Any]]:
    """
    Scan a directory for supported media files.

    Args:
        directory: Directory path to scan
        show_videos: Include video files
        show_audio: Include audio files
        sort_by: Sort criteria ('name', 'date', 'size')
        sort_order: Sort order ('asc', 'desc')

    Returns:
        List of file information dictionaries
    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Not a directory: {directory}")

    extensions = get_supported_extensions()
    items = []

    for item in os.listdir(directory):
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
