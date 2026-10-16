"""Run actual node routes against disposable files and a minimal ComfyUI host."""

import argparse
import asyncio
import importlib.util
import json
import shutil
from pathlib import Path
import sys
import tempfile
import types

from aiohttp import web
from PIL import Image

REPOSITORY = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent


def create_app(root: Path) -> web.Application:
    """Import the real plugin and replace only ComfyUI host services."""
    app = web.Application()
    routes = web.RouteTableDef()
    server = types.ModuleType("server")
    server.PromptServer = types.SimpleNamespace(
        instance=types.SimpleNamespace(routes=routes, send_sync=lambda *args: None)
    )
    sys.modules["server"] = server
    folder_paths = types.ModuleType("folder_paths")
    folder_paths.base_path = str(root)
    folder_paths.models_dir = str(root / "models")
    folder_paths.folder_names_and_paths = {}
    for kind in ("input", "output", "temp"):
        directory = root / kind
        directory.mkdir()
        setattr(folder_paths, f"get_{kind}_directory", lambda path=directory: str(path))
    folder_paths.get_filename_list = lambda kind: {
        "embeddings": ["portraits/cat.pt", "landscapes/forest.safetensors"],
        "loras": ["styles/ink.safetensors"],
    }.get(kind, [])
    folder_paths.get_folder_paths = lambda kind: [str(root / "models" / kind)]
    sys.modules["folder_paths"] = folder_paths
    spec = importlib.util.spec_from_file_location(
        "kiko_browser_plugin", REPOSITORY / "__init__.py"
    )
    plugin = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = plugin
    spec.loader.exec_module(plugin)
    loader = sys.modules["kiko_browser_plugin.kikotools.tools.local_image_loader.node"]
    loader.CONFIG_FILE = str(root / "config.json")
    loader.SELECTIONS_FILE = str(root / "selections.json")

    def reset() -> None:
        (root / "selections.json").unlink(missing_ok=True)
        shutil.rmtree(root / "output")
        (root / "output").mkdir()
        loader.save_config({"saved_paths": [], "last_path": str(root / "input")})
        for path, color in [
            ("input/cat & dog.png", "red"),
            ("input/sub/forest.png", "green"),
            ("outside/secret.png", "blue"),
        ]:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.new("RGB", (16, 12), color) as image:
                image.save(target)

    @routes.post("/__test__/reset")
    async def reset_route(request: web.Request) -> web.Response:
        await asyncio.to_thread(reset)
        return web.json_response({"success": True})

    @routes.get("/__test__/state")
    async def state(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "input": str(root / "input"),
                "outside": str(root / "outside"),
                "selections": loader.load_selections(),
                "config": loader.load_config(),
                "nodes": sorted(plugin.NODE_CLASS_MAPPINGS),
                "extensions": sorted(
                    path.name for path in (REPOSITORY / "web").glob("*.js")
                ),
            }
        )

    @routes.post("/__test__/execute/{name}")
    async def execute(request: web.Request) -> web.Response:
        name = request.match_info["name"]
        data = await request.json()
        if name not in {
            "DisplayAny",
            "DisplayText",
            "KikoLocalImageLoader",
            "KikoSaveImage",
        }:
            raise web.HTTPNotFound()
        if name == "KikoSaveImage":
            data["images"] = loader.load_image_from_path(
                str(root / "input" / "cat & dog.png")
            )[0]
        cls = plugin.NODE_CLASS_MAPPINGS[name]
        result = await asyncio.to_thread(getattr(cls(), cls.FUNCTION), **data)
        if name == "KikoLocalImageLoader":
            tensor, info = result
            return web.json_response(
                {"shape": list(tensor.shape), "info": json.loads(info) if info else {}}
            )
        return web.json_response(result)

    @routes.get("/__test__/")
    async def index(request: web.Request) -> web.Response:
        return web.Response(
            text='<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>KikoTools extension test host</title></head><body><main id="nodes"></main><script type="module" src="/__test__/host.mjs"></script></body></html>',
            content_type="text/html",
        )

    @routes.get("/__test__/host.mjs")
    async def host(request: web.Request) -> web.Response:
        return web.FileResponse(FIXTURES / "host.mjs")

    @routes.get("/scripts/{name}.js")
    async def host_import(request: web.Request) -> web.Response:
        exports = {
            "app": "export const app = window.kikoHost.app;",
            "api": "export const api = window.kikoHost.api;",
            "widgets": "export const ComfyWidgets = window.kikoHost.widgets;",
            "ui": "export const $el = window.kikoHost.el;",
        }
        if request.match_info["name"] not in exports:
            raise web.HTTPNotFound()
        return web.Response(
            text=exports[request.match_info["name"]], content_type="text/javascript"
        )

    @routes.get("/view")
    @routes.get("/api/view")
    async def comfy_view(request: web.Request) -> web.Response:
        directory = root / "output"
        path = (
            directory
            / request.query.get("subfolder", "")
            / request.query.get("filename", "")
        ).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise web.HTTPNotFound()
        return web.FileResponse(path)

    reset()
    app.add_routes(routes)
    app.router.add_static("/extensions/kikotools", REPOSITORY / "web")
    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="kiko-browser-") as directory:
        web.run_app(
            create_app(Path(directory).resolve()), host="127.0.0.1", port=args.port
        )


if __name__ == "__main__":
    main()
