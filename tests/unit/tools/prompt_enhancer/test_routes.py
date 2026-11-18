import asyncio
import json
import sys
import types

import pytest

from kikotools.tools.prompt_enhancer import library, routes


@pytest.fixture(autouse=True)
def fake_user_dir(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "folder_paths",
        types.SimpleNamespace(get_user_directory=lambda: str(tmp_path)),
    )
    return tmp_path


class StubRequest:
    def __init__(self, body=None, bad_json=False):
        self.body = body
        self.bad_json = bad_json

    async def json(self):
        if self.bad_json:
            raise json.JSONDecodeError("bad", "", 0)
        return self.body


def post(body=None, bad_json=False):
    response = asyncio.run(routes.copy_route(StubRequest(body, bad_json)))
    return response.status, json.loads(response.body)


def test_copy_creates_override(fake_user_dir):
    target = routes.copy_to_user("krea2")
    assert target == fake_user_dir / "kikotools" / "system_prompts" / "krea2.md"
    assert target.read_text(encoding="utf-8") == (
        library.SHIPPED_DIR / "krea2.md"
    ).read_text(encoding="utf-8")


def test_copy_refuses_existing(fake_user_dir):
    target = fake_user_dir / "kikotools" / "system_prompts" / "krea2.md"
    target.parent.mkdir(parents=True)
    target.write_text("mine", encoding="utf-8")
    with pytest.raises(FileExistsError):
        routes.copy_to_user("krea2")
    assert target.read_text(encoding="utf-8") == "mine"


@pytest.mark.parametrize("stem", ["../evil", "nope", "krea2/../krea2", ""])
def test_copy_rejects_unknown_and_traversal_stems(stem):
    with pytest.raises(ValueError):
        routes.copy_to_user(stem)


def test_route_status_codes():
    status, body = post({"base_model": "krea2"})
    assert status == 200 and body["path"].endswith("krea2.md")
    status, body = post({"base_model": "krea2"})
    assert status == 409 and body["error"] == "already exists" and body["path"]
    status, body = post({"base_model": "../evil"})
    assert status == 400 and "error" in body


def test_route_rejects_bad_json_and_missing_base_model():
    assert post(bad_json=True)[0] == 400
    assert post({})[0] == 400
    assert post(["krea2"])[0] == 400


def test_route_500_without_user_dir(monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", None)
    status, body = post({"base_model": "krea2"})
    assert status == 500 and "error" in body
