import logging
import sys
import types
from pathlib import Path

import pytest

from kikotools.tools.prompt_enhancer import library


@pytest.fixture(autouse=True)
def fake_user_dir(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "folder_paths",
        types.SimpleNamespace(get_user_directory=lambda: str(tmp_path)),
    )
    return tmp_path


def write_override(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / "kikotools" / "system_prompts" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_shipped_prompts_listed():
    assert "krea2" in library.prompt_names()


def test_override_replaces_shipped_by_stem(tmp_path):
    write_override(tmp_path, "krea2.md", "mine")
    prompt = library.load_prompt("krea2")
    assert prompt.text == "mine"
    assert prompt.is_override


def test_override_adds_new_entry(tmp_path):
    write_override(tmp_path, "lustify-v9.md", "x")
    assert "lustify-v9" in library.prompt_names()


def test_missing_override_dir_is_fine():
    assert "krea2" in library.prompt_names()
    assert not any(prompt.is_override for prompt in library.available_prompts().values())


def test_front_matter_parsed():
    prompt = library.parse_prompt_file(
        "x", "---\nmax_words: 80\n---\nBody", Path("x.md"), False
    )
    assert prompt.max_words == 80
    assert prompt.text == "Body"


def test_image_section_split():
    prompt = library.parse_prompt_file(
        "x", "Body\n## With an image\nMotion only.", Path("x.md"), False
    )
    assert prompt.text == "Body"
    assert prompt.image_text == "Motion only."


def test_bad_header_value_is_ignored_with_warning(caplog):
    with caplog.at_level(logging.WARNING):
        prompt = library.parse_prompt_file(
            "x", "---\nmax_words: lots\n---\nBody", Path("bad.md"), True
        )
    assert prompt.max_words is None
    assert prompt.text == "Body"
    assert "bad.md" in caplog.text


def test_unknown_stem_raises():
    with pytest.raises(ValueError, match="Unknown base model"):
        library.load_prompt("nope")


def test_default_prefers_krea2():
    assert library.default_prompt_name(["a", "krea2"]) == "krea2"
    assert library.default_prompt_name(["b", "a"]) == "a"


def test_non_md_files_ignored(tmp_path):
    write_override(tmp_path, "notes.txt", "x")
    assert "notes" not in library.prompt_names()
