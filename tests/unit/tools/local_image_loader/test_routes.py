"""Route handler tests for the Local Image Loader."""

import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from aiohttp.test_utils import make_mocked_request
from PIL import Image

from kikotools.tools.local_image_loader import node as node_mod


def run(coro):
    return asyncio.run(coro)


def req(query=None, body=None):
    async def _json():
        if isinstance(body, Exception):
            raise body
        return body

    return SimpleNamespace(query=query or {}, json=_json)


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    Image.new("RGB", (400, 300), "red").save(root / "a.png")
    Image.new("RGBA", (40, 30), (1, 2, 3, 4)).save(root / "alpha.png")
    (root / "notes.txt").write_text("secret")
    (root / "sub").mkdir()
    for i in range(3):
        Image.new("RGB", (4, 4)).save(root / "sub" / f"i{i}.png")
    outside = tmp_path / "outside"
    outside.mkdir()
    Image.new("RGB", (4, 4)).save(outside / "o.png")
    cfg = tmp_path / "config.json"
    sel = tmp_path / "selections.json"
    monkeypatch.setattr(node_mod, "CONFIG_FILE", str(cfg))
    monkeypatch.setattr(node_mod, "SELECTIONS_FILE", str(sel))
    monkeypatch.setattr(node_mod, "get_allowed_roots", lambda: [str(root)])
    return SimpleNamespace(root=root, outside=outside, cfg=cfg, sel=sel, tmp=tmp_path)


def body(resp):
    return json.loads(resp.text)


class TestAllowedRoots:
    def test_combines_saved_and_comfy_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(node_mod, "CONFIG_FILE", str(tmp_path / "c.json"))
        node_mod.save_config({"saved_paths": ["/saved", 7, ""]})
        fp = MagicMock()
        fp.get_input_directory.return_value = "/in"
        fp.get_output_directory.return_value = "/out"
        with patch.dict("sys.modules", {"folder_paths": fp}):
            roots = node_mod.get_allowed_roots()
        assert roots == ["/saved", "/in", "/out"]

    def test_folder_paths_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(node_mod, "CONFIG_FILE", str(tmp_path / "c.json"))
        with patch.dict("sys.modules", {"folder_paths": None}):
            assert node_mod.get_allowed_roots() == []

    def test_folder_paths_non_string_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setattr(node_mod, "CONFIG_FILE", str(tmp_path / "c.json"))
        fp = MagicMock()
        fp.get_input_directory.side_effect = RuntimeError("x")
        fp.get_output_directory.return_value = MagicMock()
        with patch.dict("sys.modules", {"folder_paths": fp}):
            assert node_mod.get_allowed_roots() == []

    def test_non_list_saved_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(node_mod, "CONFIG_FILE", str(tmp_path / "c.json"))
        node_mod.save_config({"saved_paths": "oops"})
        with patch.dict("sys.modules", {"folder_paths": None}):
            assert node_mod.get_allowed_roots() == []


class TestView:
    def test_serves_allowed_image(self, env):
        r = run(node_mod.view_image(req({"filepath": str(env.root / "a.png")})))
        assert r.status == 200

    def test_works_with_make_mocked_request(self, env):
        q = str(env.root / "a.png").replace("/", "%2F")
        r = run(node_mod.view_image(make_mocked_request("GET", f"/view?filepath={q}")))
        assert r.status == 200

    def test_missing_param_400(self, env):
        assert run(node_mod.view_image(req())).status == 400

    def test_null_byte_400(self, env):
        assert run(node_mod.view_image(req({"filepath": "a\0.png"}))).status == 400

    def test_non_image_in_root_403(self, env):
        r = run(node_mod.view_image(req({"filepath": str(env.root / "notes.txt")})))
        assert r.status == 403

    def test_outside_root_403(self, env):
        r = run(node_mod.view_image(req({"filepath": str(env.outside / "o.png")})))
        assert r.status == 403

    def test_ssh_key_style_403(self, env):
        assert run(node_mod.view_image(req({"filepath": "/etc/passwd"}))).status == 403

    def test_dotdot_traversal_403(self, env):
        p = str(env.root / ".." / "outside" / "o.png")
        assert run(node_mod.view_image(req({"filepath": p}))).status == 403

    def test_missing_file_404(self, env):
        r = run(node_mod.view_image(req({"filepath": str(env.root / "no.png")})))
        assert r.status == 404

    def test_dotdot_inside_root_is_fine(self, env):
        p = str(env.root / "sub" / ".." / "a.png")
        assert run(node_mod.view_image(req({"filepath": p}))).status == 200


class TestViewMedia:
    def test_video_and_audio_served(self, env):
        for name in ("clip.mp4", "song.mp3"):
            (env.root / name).write_bytes(b"x")
            r = run(node_mod.view_image(req({"filepath": str(env.root / name)})))
            assert r.status == 200

    def test_video_outside_root_403(self, env):
        (env.outside / "clip.mp4").write_bytes(b"x")
        r = run(node_mod.view_image(req({"filepath": str(env.outside / "clip.mp4")})))
        assert r.status == 403

    def test_key_files_rejected(self, env):
        for name in ("id_rsa", "id_rsa.pem", "notes.txt"):
            (env.root / name).write_text("secret")
            r = run(node_mod.view_image(req({"filepath": str(env.root / name)})))
            assert r.status == 403

    def test_thumbnail_stays_image_only(self, env):
        (env.root / "clip.mp4").write_bytes(b"x")
        r = run(node_mod.get_thumbnail(req({"filepath": str(env.root / "clip.mp4")})))
        assert r.status == 403

    def test_video_selection_allowed_but_not_loaded(self, env):
        (env.root / "clip.mp4").write_bytes(b"x")
        p = str(env.root / "clip.mp4")
        r = run(
            node_mod.set_node_selection(
                req(body={"node_id": 1, "path": p, "type": "video"})
            )
        )
        assert r.status == 200


class TestThumbnail:
    def test_jpeg_for_opaque(self, env):
        r = run(node_mod.get_thumbnail(req({"filepath": str(env.root / "a.png")})))
        assert r.status == 200 and r.content_type == "image/jpeg"

    def test_png_for_alpha(self, env):
        r = run(node_mod.get_thumbnail(req({"filepath": str(env.root / "alpha.png")})))
        assert r.status == 200 and r.content_type == "image/png"

    def test_errors(self, env):
        t = node_mod.get_thumbnail
        assert run(t(req())).status == 400
        assert run(t(req({"filepath": "a\0"}))).status == 400
        assert run(t(req({"filepath": str(env.root / "notes.txt")}))).status == 403
        assert run(t(req({"filepath": str(env.outside / "o.png")}))).status == 403
        assert run(t(req({"filepath": str(env.root / "no.png")}))).status == 404

    def test_corrupt_image_500(self, env):
        (env.root / "bad.png").write_bytes(b"not an image")
        r = run(node_mod.get_thumbnail(req({"filepath": str(env.root / "bad.png")})))
        assert r.status == 500


class TestImages:
    def test_lists_and_paginates(self, env):
        r = run(
            node_mod.get_local_images(
                req({"directory": str(env.root / "sub"), "per_page": "2"})
            )
        )
        data = body(r)
        assert r.status == 200
        assert len(data["items"]) == 2
        assert data["total_pages"] == 2
        assert data["parent_directory"] == str(env.root)
        assert json.loads(env.cfg.read_text())["last_path"] == str(env.root / "sub")

    def test_root_has_no_parent(self, env):
        r = run(node_mod.get_local_images(req({"directory": str(env.root)})))
        assert body(r)["parent_directory"] is None

    def test_outside_root_403_and_last_path_not_saved(self, env):
        r = run(node_mod.get_local_images(req({"directory": str(env.outside)})))
        assert r.status == 403
        assert not env.cfg.exists()

    def test_root_slash_403(self, env):
        assert run(node_mod.get_local_images(req({"directory": "/"}))).status == 403

    def test_missing_directory_param_400(self, env):
        assert run(node_mod.get_local_images(req())).status == 400
        assert run(node_mod.get_local_images(req({"directory": "x\0"}))).status == 400

    def test_nonexistent_404(self, env):
        r = run(node_mod.get_local_images(req({"directory": str(env.root / "zz")})))
        assert r.status == 404

    @pytest.mark.parametrize(
        "extra",
        [{"page": "abc"}, {"per_page": "x"}, {"page": "0"}, {"page": "-3"}],
    )
    def test_bad_paging_400(self, env, extra):
        q = {"directory": str(env.root), **extra}
        assert run(node_mod.get_local_images(req(q))).status == 400

    def test_per_page_clamped(self, env):
        for raw, expected in [("0", 1), ("-5", 1), ("100000", 200)]:
            r = run(
                node_mod.get_local_images(
                    req({"directory": str(env.root / "sub"), "per_page": raw})
                )
            )
            assert r.status == 200
            if expected == 1:
                assert len(body(r)["items"]) == 1
            else:
                assert len(body(r)["items"]) == 3

    def test_scan_error_500(self, env):
        with patch.object(node_mod, "scan_directory", side_effect=OSError("boom")):
            r = run(node_mod.get_local_images(req({"directory": str(env.root)})))
        assert r.status == 500
        assert "boom" not in r.text

    def test_flags(self, env):
        q = {
            "directory": str(env.root),
            "show_videos": "true",
            "show_audio": "true",
            "hide_dot_folders": "false",
            "sort_by": "date",
            "sort_order": "desc",
        }
        assert run(node_mod.get_local_images(req(q))).status == 200


class TestListDirectories:
    def test_empty_path_returns_root(self, env):
        r = run(node_mod.list_directories(req()))
        assert body(r)["directories"] == [os.path.abspath(os.sep)] or os.name == "nt"

    def test_directories_only_no_files(self, env):
        r = run(node_mod.list_directories(req({"path": str(env.root) + os.sep})))
        dirs = body(r)["directories"]
        assert dirs == [os.path.join(str(env.root) + os.sep, "sub")]

    def test_can_browse_outside_roots_names_only(self, env):
        r = run(node_mod.list_directories(req({"path": str(env.tmp) + os.sep})))
        assert r.status == 200
        assert all(os.path.isdir(d) for d in body(r)["directories"])

    def test_nul_byte_returns_empty(self, env):
        r = run(node_mod.list_directories(req({"path": "a\0b"})))
        assert body(r)["directories"] == []

    def test_permission_error(self, env):
        with patch.object(node_mod, "list_subdirectories", side_effect=PermissionError):
            r = run(node_mod.list_directories(req({"path": "/x/"})))
        assert body(r) == {"directories": [], "error": "Permission denied"}

    def test_unexpected_error(self, env):
        with patch.object(node_mod, "list_subdirectories", side_effect=OSError):
            r = run(node_mod.list_directories(req({"path": "/x/"})))
        assert body(r)["directories"] == []


class TestSelectionAndConfig:
    def test_set_selection_ok(self, env):
        p = str(env.root / "a.png")
        r = run(
            node_mod.set_node_selection(
                req(body={"node_id": 5, "path": p, "type": "image"})
            )
        )
        assert r.status == 200
        assert json.loads(env.sel.read_text())["5"]["image"] == {"path": p}

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"node_id": 1, "path": "", "type": "image"},
            {"node_id": 1, "path": ["x"], "type": "image"},
            {"node_id": 1, "path": "a\0.png", "type": "image"},
            [1, 2],
        ],
    )
    def test_set_selection_bad_input_400(self, env, payload):
        assert run(node_mod.set_node_selection(req(body=payload))).status == 400

    def test_set_selection_bad_json_400(self, env):
        r = run(node_mod.set_node_selection(req(body=ValueError("bad"))))
        assert r.status == 400

    def test_set_selection_disallowed_403(self, env):
        for p in (
            "/etc/passwd",
            str(env.root / "notes.txt"),
            str(env.outside / "o.png"),
        ):
            r = run(
                node_mod.set_node_selection(
                    req(body={"node_id": 1, "path": p, "type": "image"})
                )
            )
            assert r.status == 403
        assert not env.sel.exists()

    def test_saved_paths_roundtrip(self, env):
        r = run(node_mod.save_paths(req(body={"paths": ["/a", "/b"]})))
        assert r.status == 200
        assert body(run(node_mod.get_saved_paths(req()))) == {
            "saved_paths": ["/a", "/b"]
        }

    @pytest.mark.parametrize("payload", [{"paths": "x"}, {"paths": [1]}, [1]])
    def test_save_paths_bad_input_400(self, env, payload):
        assert run(node_mod.save_paths(req(body=payload))).status == 400

    def test_save_paths_bad_json_400(self, env):
        assert run(node_mod.save_paths(req(body=ValueError()))).status == 400

    def test_last_path(self, env):
        assert body(run(node_mod.get_last_path(req())))["last_path"] == ""
        node_mod.save_config({"last_path": "/q"})
        assert body(run(node_mod.get_last_path(req())))["last_path"] == "/q"


class TestLoadMediaGuard:
    def test_tampered_selection_refused(self, env):
        env.sel.write_text(
            json.dumps({"7": {"image": {"path": str(env.outside / "o.png")}}})
        )
        image, info = node_mod.LocalImageLoaderNode().load_media("7")
        assert image.shape == (1, 1, 1, 4) and info == ""

    def test_non_image_selection_refused(self, env):
        env.sel.write_text(
            json.dumps({"7": {"image": {"path": str(env.root / "notes.txt")}}})
        )
        _, info = node_mod.LocalImageLoaderNode().load_media("7")
        assert info == ""

    def test_allowed_selection_loads(self, env):
        env.sel.write_text(
            json.dumps({"7": {"image": {"path": str(env.root / "a.png")}}})
        )
        image, info = node_mod.LocalImageLoaderNode().load_media("7")
        assert image.shape == (1, 300, 400, 3)
        assert json.loads(info)["width"] == 400

    def test_load_error_is_swallowed(self, env):
        (env.root / "bad.png").write_bytes(b"junk")
        env.sel.write_text(
            json.dumps({"7": {"image": {"path": str(env.root / "bad.png")}}})
        )
        image, info = node_mod.LocalImageLoaderNode().load_media("7")
        assert info == ""


class TestPersistence:
    def test_selections_corrupt_file(self, env):
        env.sel.write_text("{nope")
        assert node_mod.load_selections() == {}

    def test_config_corrupt_file(self, env):
        env.cfg.write_text("{nope")
        assert node_mod.load_config() == {}

    def test_save_errors_logged_not_raised(self, env, monkeypatch):
        monkeypatch.setattr(node_mod, "SELECTIONS_FILE", "/nonexistent_dir/x.json")
        monkeypatch.setattr(node_mod, "CONFIG_FILE", "/nonexistent_dir/y.json")
        node_mod.save_selections({"a": 1})
        node_mod.save_config({"a": 1})
