import json
import sys
import types
from pathlib import Path

import pytest

from kikotools.tools.character_hint import options


@pytest.fixture(autouse=True)
def fake_user_dir(tmp_path, monkeypatch):
    """Point the ComfyUI user directory at tmp_path and clear the cache."""
    monkeypatch.setitem(
        sys.modules,
        "folder_paths",
        types.SimpleNamespace(get_user_directory=lambda: str(tmp_path)),
    )
    options._reset_cache()
    yield tmp_path
    options._reset_cache()


@pytest.fixture
def write_user_file(tmp_path):
    def write(data) -> Path:
        path = tmp_path / options.USER_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data))
        return path

    return write
