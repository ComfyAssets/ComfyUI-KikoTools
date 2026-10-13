"""Download flow, security and failure-path tests for all downloaders.

All network access is mocked; nothing here touches the real network.
"""

import io
import json
import os
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from kikotools.tools.model_downloader import base
from kikotools.tools.model_downloader.base import (
    BaseDownloader,
    safe_server_filename,
    validate_filename,
    validate_url_scheme,
)
from kikotools.tools.model_downloader.civitai import CivitAIDownloader
from kikotools.tools.model_downloader.custom import CustomDownloader
from kikotools.tools.model_downloader.huggingface import HuggingFaceDownloader

HF_URL = "https://huggingface.co/user/repo/resolve/main/model.safetensors"
CIVITAI_URL = "https://civitai.com/api/download/models/123"
SIGNED_URL = "https://cdn.example.com/blob/model.safetensors"


class FakeResponse:
    def __init__(self, data=b"", status=200, headers=None, fail_after=None):
        self._io = io.BytesIO(data)
        self.status = status
        self.headers = headers or {}
        self.closed = False
        self._fail_after = fail_after

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read(self, n=-1):
        if self._fail_after is not None and self._io.tell() >= self._fail_after:
            raise ConnectionResetError("boom")
        if self._fail_after is not None:
            n = self._fail_after
        return self._io.read(n)

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def http_error(code, reason="err"):
    return urllib.error.HTTPError("http://x", code, reason, {}, None)


@pytest.fixture
def root(tmp_path):
    models = tmp_path / "models"
    (models / "checkpoints").mkdir(parents=True)
    return models


@pytest.fixture
def out(root):
    return str(root / "checkpoints")


@pytest.fixture
def opener():
    """Patch build_opener; yields (build_opener_mock, opener_mock)."""
    with patch.object(urllib.request, "build_opener") as build:
        op = MagicMock()
        build.return_value = op
        yield build, op


def make(cls, root, token=None):
    return cls(token=token, models_root=str(root))


# ---------------------------------------------------------------- helpers


class TestValidators:
    @pytest.mark.parametrize(
        "name", ["", ".", "..", "../x", "a/b", "/etc/passwd", "a\\b", None, "x\x00y"]
    )
    def test_validate_filename_rejects(self, name):
        with pytest.raises(ValueError):
            validate_filename(name)

    def test_validate_filename_accepts_plain(self):
        assert validate_filename("model.safetensors") == "model.safetensors"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("../../evil.bin", "evil.bin"),
            ("/etc/passwd", "passwd"),
            ("..\\win\\x.bin", "x.bin"),
            ("ok.bin", "ok.bin"),
            ("..", "dflt"),
            ("dir/", "dflt"),
            ("", "dflt"),
            (None, "dflt"),
        ],
    )
    def test_safe_server_filename(self, raw, expected):
        assert safe_server_filename(raw, "dflt") == expected

    @pytest.mark.parametrize(
        "url", ["file:///etc/passwd", "ftp://h/x", "gopher://h", "", "//h/x"]
    )
    def test_scheme_rejected(self, url):
        with pytest.raises(ValueError):
            validate_url_scheme(url)

    @pytest.mark.parametrize("url", ["http://h/x", "HTTPS://h/x"])
    def test_scheme_allowed(self, url):
        validate_url_scheme(url)


class TestHeaderParsing:
    @pytest.mark.parametrize(
        "header,expected",
        [
            ('attachment; filename="a b.bin"', "a b.bin"),
            ("attachment; filename=a.bin; size=3", "a.bin"),
            ("attachment; filename='q.bin'", "q.bin"),
            ("attachment; filename*=UTF-8''na%C3%AFve.bin", "naïve.bin"),
            ("attachment", None),
            ("", None),
            ('attachment; filename=""', None),
        ],
    )
    def test_extract(self, header, expected):
        d = CustomDownloader()
        assert d.extract_filename_from_header(header) == expected


class TestResolveOutputDir:
    def test_inside_ok_and_created(self, root):
        d = make(CustomDownloader, root)
        new = root / "loras" / "sub"
        assert d.resolve_output_dir(str(new)) == os.path.realpath(new)
        assert new.is_dir()

    def test_root_itself_ok(self, root):
        assert make(CustomDownloader, root).resolve_output_dir(str(root))

    @pytest.mark.parametrize("rel", ["..", "../other", "checkpoints/../../x"])
    def test_traversal_rejected(self, root, rel):
        d = make(CustomDownloader, root)
        with pytest.raises(ValueError):
            d.resolve_output_dir(str(root / rel))
        assert not (root.parent / "other").exists()

    def test_sibling_prefix_not_accepted(self, root, tmp_path):
        sibling = tmp_path / "models_evil"
        with pytest.raises(ValueError):
            make(CustomDownloader, root).resolve_output_dir(str(sibling))

    def test_symlink_escape_rejected(self, root, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        (root / "link").symlink_to(outside)
        with pytest.raises(ValueError):
            make(CustomDownloader, root).resolve_output_dir(str(root / "link"))

    def test_absolute_outside_rejected(self, root):
        with pytest.raises(ValueError):
            make(CustomDownloader, root).resolve_output_dir("/etc")

    def test_default_roots_include_models_dir_and_registered_paths(
        self, root, tmp_path
    ):
        extra = tmp_path / "mnt" / "loras"
        extra.mkdir(parents=True)
        fp = MagicMock()
        fp.models_dir = str(root)
        fp.folder_names_and_paths = {
            "loras": ([str(extra), "/other/x"], {".safetensors"}),
            "broken": 5,
        }
        with patch.dict("sys.modules", {"folder_paths": fp}):
            d = CustomDownloader()
            assert d.resolve_output_dir(str(root / "x"))
            assert d.resolve_output_dir(str(extra / "sub"))
            with pytest.raises(ValueError):
                d.resolve_output_dir("/etc")

    def test_injected_roots_accept_list(self, root, tmp_path):
        other = tmp_path / "other"
        d = CustomDownloader(models_root=[str(root), str(other)])
        assert d.resolve_output_dir(str(other / "a"))

    def test_relative_path_resolved_against_base_path(self, root, tmp_path):
        fp = MagicMock()
        fp.models_dir = str(root)
        fp.base_path = str(tmp_path)
        with patch.dict("sys.modules", {"folder_paths": fp}):
            result = CustomDownloader().resolve_output_dir("models/checkpoints")
        assert result == os.path.realpath(root / "checkpoints")

    def test_relative_path_falls_back_to_cwd(self, root, monkeypatch):
        monkeypatch.chdir(root.parent)
        fp = MagicMock()  # base_path not a str
        with patch.dict("sys.modules", {"folder_paths": fp}):
            result = CustomDownloader(models_root=str(root)).resolve_output_dir(
                "models/loras"
            )
        assert result == os.path.realpath(root / "loras")

    def test_unavailable_root_fails_closed(self, tmp_path):
        fp = MagicMock()  # models_dir is a MagicMock, not a str
        with patch.dict("sys.modules", {"folder_paths": fp}):
            with pytest.raises(ValueError):
                CustomDownloader().resolve_output_dir(str(tmp_path))

    def test_folder_paths_import_error(self, tmp_path):
        with patch.dict("sys.modules", {"folder_paths": None}):
            with pytest.raises(ValueError):
                CustomDownloader().resolve_output_dir(str(tmp_path))


class TestOpenUrl:
    def test_timeout_and_scheme(self, opener):
        build, op = opener
        d = CustomDownloader()
        d.open_url(urllib.request.Request("https://h/x"))
        assert op.open.call_args.kwargs["timeout"] == base.DOWNLOAD_TIMEOUT
        with pytest.raises(ValueError):
            d.open_url(urllib.request.Request("file:///etc/passwd"))

    def test_no_redirect_mode_uses_processor(self, opener):
        build, _ = opener
        CustomDownloader().open_url(
            urllib.request.Request("https://h/x"), follow_redirects=False
        )
        assert build.call_args.args == (base._NoRedirectProcessor,)

    def test_no_redirect_processor_passes_through(self):
        resp = object()
        assert base._NoRedirectProcessor().http_response(None, resp) is resp


class TestRedirectHandler:
    def redirect(self, src, dst, headers):
        req = urllib.request.Request(src, headers=headers)
        return base._SafeRedirectHandler().redirect_request(
            req, io.BytesIO(), 302, "Found", {}, dst
        )

    def test_cross_host_drops_authorization(self):
        new = self.redirect(
            "https://a.com/x", "https://b.com/y", {"Authorization": "Bearer s"}
        )
        assert not new.has_header("Authorization")

    def test_same_host_keeps_authorization(self):
        new = self.redirect(
            "https://a.com/x", "https://a.com/y", {"Authorization": "Bearer s"}
        )
        assert new.get_header("Authorization") == "Bearer s"

    def test_disallowed_scheme_blocked(self):
        with pytest.raises(urllib.error.HTTPError):
            self.redirect("https://a.com/x", "file:///etc/passwd", {})


class TestSaveResponse:
    def test_success_atomic(self, tmp_path):
        target = str(tmp_path / "f.bin")
        resp = FakeResponse(b"abcdef")
        cb = MagicMock()
        d = CustomDownloader()
        d.set_progress_callback(cb)
        assert d.save_response(resp, target, 6) == target
        assert open(target, "rb").read() == b"abcdef"
        assert not os.path.exists(target + ".part")
        assert resp.closed
        cb.assert_called()

    def test_unknown_size_progress(self, tmp_path):
        cb = MagicMock()
        d = CustomDownloader()
        d.set_progress_callback(cb)
        d.save_response(FakeResponse(b"abc"), str(tmp_path / "f"), None)
        assert cb.call_args.args[:2] == (3, 0)

    def test_strict_size_mismatch_leaves_nothing(self, tmp_path):
        target = str(tmp_path / "f.bin")
        with pytest.raises(Exception, match="incomplete"):
            CustomDownloader().save_response(FakeResponse(b"abc"), target, 10)
        assert os.listdir(tmp_path) == []

    def test_lenient_size_mismatch_saves(self, tmp_path):
        target = str(tmp_path / "f.bin")
        CustomDownloader().save_response(
            FakeResponse(b"abc"), target, 10, strict_size=False
        )
        assert os.path.exists(target)

    def test_network_error_midstream_cleans_part(self, tmp_path):
        target = str(tmp_path / "f.bin")
        resp = FakeResponse(b"x" * 100, fail_after=10)
        with pytest.raises(ConnectionResetError):
            CustomDownloader().save_response(resp, target, 100)
        assert os.listdir(tmp_path) == []

    def test_keyboard_interrupt_cleans_part(self, tmp_path):
        d = CustomDownloader()
        with patch.object(d, "check_interrupt", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                d.save_response(FakeResponse(b"abc"), str(tmp_path / "f"), 3)
        assert os.listdir(tmp_path) == []

    def test_existing_final_file_untouched_on_failure(self, tmp_path):
        target = tmp_path / "f.bin"
        target.write_bytes(b"old")
        with pytest.raises(Exception):
            CustomDownloader().save_response(FakeResponse(b"abc"), str(target), 10)
        assert target.read_bytes() == b"old"

    @pytest.mark.parametrize("value,expected", [("12", 12), (None, None), ("x", None)])
    def test_parse_content_length(self, value, expected):
        resp = FakeResponse(headers={} if value is None else {"Content-Length": value})
        assert BaseDownloader.parse_content_length(resp) == expected

    def test_http_error_messages(self):
        d = CustomDownloader()
        with pytest.raises(Exception, match="Rate limited"):
            d.raise_for_http_status(429, "r", {})
        with pytest.raises(Exception, match="HTTP error 500: boom"):
            d.raise_for_http_status(500, "boom", {})
        with pytest.raises(Exception, match="hint"):
            d.raise_for_http_status(404, "r", {404: "hint"})


# ---------------------------------------------------------------- custom


class TestCustom:
    def test_download_with_header_filename_and_token(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(
            b"data",
            headers={
                "Content-Disposition": 'attachment; filename="named.safetensors"',
                "Content-Length": "4",
            },
        )
        path = make(CustomDownloader, root, "tok").download("https://h/dl?id=1", out)
        assert path == os.path.join(os.path.realpath(out), "named.safetensors")
        assert open(path, "rb").read() == b"data"
        req = op.open.call_args.args[0]
        assert req.get_header("Authorization") == "Bearer tok"
        assert op.open.call_args.kwargs["timeout"] == base.DOWNLOAD_TIMEOUT

    def test_malicious_header_filename_is_basenamed(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(
            b"d", headers={"Content-Disposition": 'attachment; filename="../../evil"'}
        )
        path = make(CustomDownloader, root).download("https://h/dl", out)
        assert os.path.basename(path) == "evil"
        assert os.path.dirname(path) == os.path.realpath(out)
        assert not (root.parent / "evil").exists()

    def test_default_name_only_when_no_header_and_no_url_name(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d")
        path = make(CustomDownloader, root).download("https://h/", out)
        assert os.path.basename(path) == "downloaded_model.safetensors"

    def test_url_name_used_when_no_header(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d")
        path = make(CustomDownloader, root).download("https://h/a/m.ckpt", out)
        assert os.path.basename(path) == "m.ckpt"

    def test_existing_file_skipped_with_header_name(self, root, out, opener):
        _, op = opener
        existing = os.path.join(out, "named.bin")
        open(existing, "wb").write(b"old")
        resp = FakeResponse(
            b"new", headers={"Content-Disposition": "attachment; filename=named.bin"}
        )
        op.open.return_value = resp
        path = make(CustomDownloader, root).download("https://h/dl", out)
        assert open(path, "rb").read() == b"old"
        assert resp.closed

    def test_explicit_filename_existing_skips_request(self, root, out, opener):
        build, op = opener
        open(os.path.join(out, "a.bin"), "wb").write(b"old")
        make(CustomDownloader, root).download("https://h/x", out, filename="a.bin")
        op.open.assert_not_called()

    def test_force_overwrites(self, root, out, opener):
        _, op = opener
        open(os.path.join(out, "a.bin"), "wb").write(b"old")
        op.open.return_value = FakeResponse(b"new")
        path = make(CustomDownloader, root).download(
            "https://h/x", out, filename="a.bin", force=True
        )
        assert open(path, "rb").read() == b"new"

    @pytest.mark.parametrize("bad", ["../x", "/abs", "..", "a/b"])
    def test_bad_filename_rejected(self, root, out, bad):
        with pytest.raises(ValueError):
            make(CustomDownloader, root).download("https://h/x", out, filename=bad)

    def test_out_of_root_rejected_before_network(self, root, opener):
        _, op = opener
        with pytest.raises(ValueError):
            make(CustomDownloader, root).download("https://h/x", str(root.parent))
        op.open.assert_not_called()

    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://h/f"])
    def test_bad_scheme_rejected(self, root, out, url):
        with pytest.raises(ValueError):
            make(CustomDownloader, root).download(url, out)

    @pytest.mark.parametrize(
        "code,text",
        [
            (401, "Authentication"),
            (403, "forbidden"),
            (404, "not found"),
            (429, "Rate limited"),
            (500, "HTTP error 500"),
        ],
    )
    def test_http_errors(self, root, out, opener, code, text):
        _, op = opener
        op.open.side_effect = http_error(code)
        with pytest.raises(Exception, match=text):
            make(CustomDownloader, root).download("https://h/x", out, filename="a")

    def test_url_error(self, root, out, opener):
        _, op = opener
        op.open.side_effect = urllib.error.URLError("dns")
        with pytest.raises(Exception, match="Network error: dns"):
            make(CustomDownloader, root).download("https://h/x", out, filename="a")

    def test_size_mismatch_warns_but_saves(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"ab", headers={"Content-Length": "9"})
        path = make(CustomDownloader, root).download("https://h/x", out, filename="a")
        assert os.path.exists(path)

    def test_midstream_failure_leaves_no_file(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"x" * 50, fail_after=5)
        with pytest.raises(ConnectionResetError):
            make(CustomDownloader, root).download("https://h/x", out, filename="a")
        assert os.listdir(out) == []

    def test_token_not_logged(self, root, out, opener, caplog):
        _, op = opener
        op.open.return_value = FakeResponse(b"d")
        with caplog.at_level("DEBUG"):
            make(CustomDownloader, root, "SECRET123").download(
                "https://h/x", out, filename="a"
            )
        assert "SECRET123" not in caplog.text


# ---------------------------------------------------------------- hugging face


class TestHuggingFace:
    def test_download_blob_url_converted(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d", headers={"Content-Length": "1"})
        url = "https://huggingface.co/user/repo/blob/main/sub/m.safetensors"
        path = make(HuggingFaceDownloader, root, "t").download(url, out)
        assert os.path.basename(path) == "m.safetensors"
        req = op.open.call_args.args[0]
        assert req.full_url == (
            "https://huggingface.co/user/repo/resolve/main/sub/m.safetensors"
        )
        assert req.get_header("Authorization") == "Bearer t"

    def test_non_hf_structure_uses_original_url(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d")
        path = make(HuggingFaceDownloader, root).download(
            "https://huggingface.co/some/file.bin", out
        )
        assert op.open.call_args.args[0].full_url.endswith("/some/file.bin")
        assert os.path.basename(path) == "file.bin"

    def test_fallback_name(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d")
        path = make(HuggingFaceDownloader, root).download(
            "https://huggingface.co/", out
        )
        assert os.path.basename(path) == "model.safetensors"

    def test_existing_skipped(self, root, out, opener):
        _, op = opener
        open(os.path.join(out, "model.safetensors"), "wb").write(b"old")
        make(HuggingFaceDownloader, root).download(HF_URL, out)
        op.open.assert_not_called()

    def test_size_mismatch_removes_file(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"ab", headers={"Content-Length": "9"})
        with pytest.raises(Exception, match="incomplete"):
            make(HuggingFaceDownloader, root).download(HF_URL, out)
        assert os.listdir(out) == []

    @pytest.mark.parametrize(
        "code,text",
        [(401, "Authentication"), (403, "gated"), (404, "not found"), (500, "HTTP")],
    )
    def test_http_errors(self, root, out, opener, code, text):
        _, op = opener
        op.open.side_effect = http_error(code)
        with pytest.raises(Exception, match=text):
            make(HuggingFaceDownloader, root).download(HF_URL, out)

    def test_url_error(self, root, out, opener):
        _, op = opener
        op.open.side_effect = urllib.error.URLError("down")
        with pytest.raises(Exception, match="Network error"):
            make(HuggingFaceDownloader, root).download(HF_URL, out)

    def test_traversal_filename_rejected(self, root, out):
        with pytest.raises(ValueError):
            make(HuggingFaceDownloader, root).download(HF_URL, out, filename="../x")

    def test_scheme_rejected(self, root, out):
        with pytest.raises(ValueError):
            make(HuggingFaceDownloader, root).download("file:///etc/passwd", out)

    def test_path_traversal_in_url_path_is_basenamed(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d")
        url = "https://huggingface.co/u/r/resolve/main/..%2F..%2Fevil.bin"
        path = make(HuggingFaceDownloader, root).download(url, out)
        assert os.path.dirname(path) == os.path.realpath(out)


# ---------------------------------------------------------------- civitai


def redirect_resp(location, status=302):
    return FakeResponse(
        status=status, headers={"Location": location} if location else {}
    )


class TestCivitAI:
    def test_redirect_flow_filename_from_disposition(self, root, out, opener):
        _, op = opener
        loc = (
            SIGNED_URL
            + "?response-content-disposition=attachment%3B%20filename%3D%22real.safetensors%22"
        )
        op.open.side_effect = [
            redirect_resp(loc),
            FakeResponse(b"data", headers={"Content-Length": "4"}),
        ]
        path = make(CivitAIDownloader, root, "tok").download(CIVITAI_URL, out)
        assert os.path.basename(path) == "real.safetensors"
        first, second = [c.args[0] for c in op.open.call_args_list]
        assert first.get_header("Authorization") == "Bearer tok"
        assert not second.has_header("Authorization")
        assert all(
            c.kwargs["timeout"] == base.DOWNLOAD_TIMEOUT for c in op.open.call_args_list
        )

    def test_malicious_redirect_disposition_sanitized(self, root, out, opener):
        _, op = opener
        loc = (
            SIGNED_URL
            + "?response-content-disposition=filename%3D%22..%2F..%2Fevil.bin%22"
        )
        op.open.side_effect = [redirect_resp(loc), FakeResponse(b"d")]
        path = make(CivitAIDownloader, root).download(CIVITAI_URL, out)
        assert os.path.dirname(path) == os.path.realpath(out)
        assert os.path.basename(path) == "evil.bin"

    def test_filename_from_redirect_path(self, root, out, opener):
        _, op = opener
        op.open.side_effect = [redirect_resp(SIGNED_URL), FakeResponse(b"d")]
        path = make(CivitAIDownloader, root).download(CIVITAI_URL, out)
        assert os.path.basename(path) == "model.safetensors"

    def test_redirect_path_without_name_uses_default(self, root, out, opener):
        _, op = opener
        op.open.side_effect = [
            redirect_resp("https://cdn.example.com/"),
            FakeResponse(b"d"),
        ]
        path = make(CivitAIDownloader, root).download(CIVITAI_URL, out)
        assert os.path.basename(path) == "downloaded_file.safetensors"

    def test_relative_redirect(self, root, out, opener):
        _, op = opener
        op.open.side_effect = [redirect_resp("/files/x.bin"), FakeResponse(b"d")]
        make(CivitAIDownloader, root).download(CIVITAI_URL, out)
        assert op.open.call_args_list[1].args[0].full_url == (
            "https://civitai.com/files/x.bin"
        )

    def test_missing_location_header(self, root, out, opener):
        _, op = opener
        op.open.return_value = redirect_resp(None)
        with pytest.raises(Exception, match="Location"):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out)

    @pytest.mark.parametrize("loc", ["file:///etc/passwd", "ftp://h/x"])
    def test_redirect_bad_scheme(self, root, out, opener, loc):
        _, op = opener
        op.open.return_value = redirect_resp(loc)
        with pytest.raises(ValueError):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out)
        assert op.open.call_count == 1

    def test_direct_200_no_redirect(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d", status=200)
        path = make(CivitAIDownloader, root).download(
            CIVITAI_URL, out, filename="m.bin"
        )
        assert os.path.basename(path) == "m.bin"

    def test_200_without_filename_uses_url_default(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d", status=200)
        path = make(CivitAIDownloader, root).download(CIVITAI_URL, out)
        assert os.path.basename(path) == "model.safetensors"

    @pytest.mark.parametrize(
        "status,text",
        [
            (401, "Authentication"),
            (403, "forbidden"),
            (404, "File not found"),
            (500, "HTTP error 500"),
        ],
    )
    def test_non_200_statuses(self, root, out, opener, status, text):
        _, op = opener
        op.open.return_value = FakeResponse(status=status)
        with pytest.raises(Exception, match=text):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out)

    def test_http_error_raised(self, root, out, opener):
        _, op = opener
        op.open.side_effect = http_error(401)
        with pytest.raises(Exception, match="Authentication"):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out)

    def test_url_error_first_and_second_request(self, root, out, opener):
        _, op = opener
        op.open.side_effect = urllib.error.URLError("x")
        with pytest.raises(Exception, match="Network error"):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out)
        op.open.side_effect = [redirect_resp(SIGNED_URL), urllib.error.URLError("y")]
        with pytest.raises(Exception, match="Network error: y"):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out)

    def test_second_request_http_error(self, root, out, opener):
        _, op = opener
        op.open.side_effect = [redirect_resp(SIGNED_URL), http_error(403)]
        with pytest.raises(Exception, match="forbidden"):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out)

    def test_existing_file_skipped(self, root, out, opener):
        _, op = opener
        open(os.path.join(out, "model.safetensors"), "wb").write(b"old")
        op.open.side_effect = [redirect_resp(SIGNED_URL), FakeResponse(b"new")]
        path = make(CivitAIDownloader, root).download(CIVITAI_URL, out)
        assert open(path, "rb").read() == b"old"

    def test_size_mismatch_removes_file(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(
            b"ab", status=200, headers={"Content-Length": "9"}
        )
        with pytest.raises(Exception, match="incomplete"):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out, filename="m")
        assert os.listdir(out) == []

    def test_interrupt_propagates_and_cleans(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"abc", status=200)

        class Interrupted(Exception):
            pass

        d = make(CivitAIDownloader, root)
        with patch.object(d, "check_interrupt", side_effect=Interrupted):
            with pytest.raises(Interrupted):
                d.download(CIVITAI_URL, out, filename="m")
        assert os.listdir(out) == []

    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://civitai.com/x"])
    def test_bad_scheme(self, root, out, url):
        with pytest.raises(ValueError):
            make(CivitAIDownloader, root).download(url, out)

    def test_foreign_domain_rejected(self, root, out):
        with pytest.raises(ValueError, match="civitai.com"):
            make(CivitAIDownloader, root).download("https://evil.com/x", out)

    def test_bad_filename_rejected(self, root, out):
        with pytest.raises(ValueError):
            make(CivitAIDownloader, root).download(CIVITAI_URL, out, filename="../x")

    def test_save_path_outside_rejected(self, root):
        with pytest.raises(ValueError):
            make(CivitAIDownloader, root).download(CIVITAI_URL, "/etc")

    def test_web_url_with_version_id(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b"d", status=200)
        make(CivitAIDownloader, root).download(
            "https://civitai.com/models/5?modelVersionId=77", out, filename="m"
        )
        assert op.open.call_args.args[0].full_url.endswith("/api/download/models/77")

    def test_web_url_model_id_resolves_latest(self, root, out, opener):
        _, op = opener
        details = FakeResponse(json.dumps({"modelVersions": [{"id": 9}]}).encode())
        op.open.side_effect = [details, FakeResponse(b"d", status=200)]
        make(CivitAIDownloader, root).download(
            "https://civitai.com/models/5/name", out, filename="m"
        )
        assert op.open.call_args.args[0].full_url.endswith("/api/download/models/9")

    def test_web_url_model_without_versions(self, root, out, opener):
        _, op = opener
        op.open.return_value = FakeResponse(b'{"modelVersions": []}')
        with pytest.raises(Exception, match="No versions"):
            make(CivitAIDownloader, root).download("https://civitai.com/models/5", out)

    def test_web_url_unparseable(self, root, out):
        with pytest.raises(Exception, match="Could not parse"):
            make(CivitAIDownloader, root).download("https://civitai.com/about", out)

    def test_model_details_errors(self, opener):
        _, op = opener
        d = CivitAIDownloader(token="t")
        op.open.side_effect = http_error(404)
        with pytest.raises(Exception, match="not found"):
            d.get_model_details(1)
        op.open.side_effect = http_error(500)
        with pytest.raises(Exception, match="API request failed"):
            d.get_model_details(1)

    def test_make_request_adds_auth(self):
        req = CivitAIDownloader(token="t")._make_request("https://civitai.com/x")
        assert req.get_header("Authorization") == "Bearer t"
        assert (
            CivitAIDownloader()
            ._make_request("https://civitai.com/x")
            .has_header("Authorization")
            is False
        )

    def test_parse_urls(self):
        d = CivitAIDownloader()
        assert d._parse_civitai_url(CIVITAI_URL)["version_id"] == 123
        assert d._parse_civitai_url("https://civitai.com/models/5")["model_id"] == 5
