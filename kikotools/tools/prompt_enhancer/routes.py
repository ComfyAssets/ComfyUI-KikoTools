"""Server route that copies a shipped system prompt into the user folder."""

import shutil
from pathlib import Path
from typing import Any

from aiohttp import web

from .library import SHIPPED_DIR, override_dir


def copy_to_user(stem: str) -> Path:
    """Copy the shipped prompt named ``stem`` into the override folder."""
    source = next((p for p in SHIPPED_DIR.glob("*.md") if p.stem == stem), None)
    if source is None:
        raise ValueError(f"Unknown base model '{stem}'")
    target_dir = override_dir()
    if target_dir is None:
        raise RuntimeError("No ComfyUI user directory available")
    target = target_dir / source.name
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with open(target, "xb") as out, open(source, "rb") as src:
            shutil.copyfileobj(src, out)
    except FileExistsError:
        raise FileExistsError(str(target)) from None
    return target


async def copy_route(request: Any) -> web.Response:
    try:
        body = await request.json()
    except ValueError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    stem = body.get("base_model") if isinstance(body, dict) else None
    if not isinstance(stem, str):
        return web.json_response({"error": "base_model is required"}, status=400)
    try:
        target = copy_to_user(stem)
    except ValueError as error:
        return web.json_response({"error": str(error)}, status=400)
    except FileExistsError as error:
        return web.json_response(
            {"error": "already exists", "path": str(error)}, status=409
        )
    except RuntimeError as error:
        return web.json_response({"error": str(error)}, status=500)
    return web.json_response({"path": str(target)})
