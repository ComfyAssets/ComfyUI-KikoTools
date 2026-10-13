"""Path building logic for the Project File Path node."""

import os
import re
from datetime import date
from typing import Optional

# Characters that are invalid in Windows paths (and awkward elsewhere)
_UNSAFE_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
_SEPARATORS = re.compile(r"[\\/]+")

# Only these are treated as a file extension and stripped from the filename,
# so names like "render_v1.5" keep their dot.
FILE_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".mp4",
        ".webm",
        ".mov",
        ".mkv",
        ".avi",
        ".wav",
        ".mp3",
        ".flac",
        ".ogg",
        ".txt",
        ".json",
        ".latent",
    }
)

SEPARATOR_OPTIONS = ("auto", "forward_slash", "backslash")


def _clean_part(part: str) -> str:
    """Clean one path segment: drop unsafe chars, spaces to underscores."""
    part = _UNSAFE_CHARS.sub("", part).strip(" .")
    return part.replace(" ", "_")


def sanitize_component(text: str) -> str:
    """Clean a folder component, keeping nested folders as 'a/b'.

    Splits on both / and \\, drops empty, '.' and '..' segments, so the
    result is always relative and can never climb out of its parent.
    """
    parts = (_clean_part(p) for p in _SEPARATORS.split(text or ""))
    return "/".join(p for p in parts if p and p not in (".", ".."))


def sanitize_filename(text: str) -> str:
    """Clean a filename: no folders, and a known file extension removed."""
    name = _UNSAFE_CHARS.sub("", _SEPARATORS.sub("", text or ""))
    stem, extension = os.path.splitext(name)
    if extension.lower() in FILE_EXTENSIONS:
        name = stem
    elif name.strip().lower() in FILE_EXTENSIONS:  # just ".png": splitext sees no ext
        name = ""
    return _clean_part(name)


def _resolve_separator(separator: str) -> str:
    if separator == "auto":
        return os.sep
    if separator == "forward_slash":
        return "/"
    if separator == "backslash":
        return "\\"
    raise ValueError(
        f"Unknown separator '{separator}'; use one of {', '.join(SEPARATOR_OPTIONS)}"
    )


def build_project_path(
    root: str,
    project_name: str,
    subfolder: str,
    filename: str,
    date_folder: bool = False,
    separator: str = "auto",
    today: Optional[date] = None,
) -> str:
    """Build 'root/project/[YYYY-MM-DD/]subfolder/filename'.

    Raises:
        ValueError: If the filename is empty after cleaning, or the
            separator is unknown.
    """
    sep = _resolve_separator(separator)
    clean_filename = sanitize_filename(filename)
    if not clean_filename:
        raise ValueError(f"filename {filename!r} is empty after removing unsafe parts")

    folders = [sanitize_component(root), sanitize_component(project_name)]
    if date_folder:
        folders.append((today or date.today()).isoformat())
    folders.append(sanitize_component(subfolder))

    path = "/".join([f for f in folders if f] + [clean_filename])
    return path.replace("/", sep)
