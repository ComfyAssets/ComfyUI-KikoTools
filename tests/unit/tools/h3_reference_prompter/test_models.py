import json
import sys
import types
from pathlib import Path

import pytest

from kikotools.tools.h3_reference_prompter import models as h3_models
from kikotools.tools.h3_reference_prompter.models import (
    HF_ARCHITECTURES,
    default_prompter_model,
    find_prompter_model,
    hf_entries,
    list_prompter_models,
    prompter_model_names,
)
from kikotools.tools.prompt_enhancer import models as enhancer_models
from kikotools.tools.prompt_enhancer.models import NONE_FOUND, ModelEntry


def write_config(folder: Path, text) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    body = text if isinstance(text, str) else json.dumps(text)
    (folder / "config.json").write_text(body)


def make_tree(root: Path) -> None:
    qwen = root / "Qwen-VL" / "Qwen3.5-4B-Unredacted-MAX"
    write_config(qwen, {"architectures": ["Qwen3_5ForConditionalGeneration"]})
    write_config(
        qwen / "nested", {"architectures": ["Qwen3VLForConditionalGeneration"]}
    )
    write_config(
        root / "gemma-4-e4b", {"architectures": ["Gemma4ForConditionalGeneration"]}
    )
    write_config(root / "text-only", {"architectures": ["Qwen3ForCausalLM"]})
    write_config(root / "broken", "{not json")
    write_config(root / "no-list", {"architectures": "Gemma4ForConditionalGeneration"})
    write_config(root / "not-object", "[1, 2]")
    (root / "no-config").mkdir()


def entry(name, kind="gguf", vision=True, mmproj=Path("m.gguf")):
    return ModelEntry(
        name=name,
        kind=kind,
        path=Path(name),
        vision=vision,
        mmproj=mmproj,
        clip_type=None,
    )


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    folder_paths = types.SimpleNamespace(models_dir=str(tmp_path))
    monkeypatch.setitem(sys.modules, "folder_paths", folder_paths)
    state = types.SimpleNamespace(root=tmp_path / "LLM", enhancer=[])
    monkeypatch.setattr(h3_models, "list_models", lambda: state.enhancer)
    return state


def test_architectures_cover_the_four_supported_families():
    assert set(HF_ARCHITECTURES) == {
        "Qwen3_5ForConditionalGeneration",
        "Qwen3VLForConditionalGeneration",
        "Gemma4ForConditionalGeneration",
        "Gemma4UnifiedForConditionalGeneration",
    }


def test_hf_entries_lists_only_recognised_folders(tmp_path):
    make_tree(tmp_path)

    entries = hf_entries(tmp_path)

    assert [e.name for e in entries] == [
        "hf: Qwen-VL/Qwen3.5-4B-Unredacted-MAX",
        "hf: gemma-4-e4b",
    ]


def test_hf_entries_fields(tmp_path):
    make_tree(tmp_path)

    first = hf_entries(tmp_path)[0]

    assert first.kind == "hf"
    assert first.path == tmp_path / "Qwen-VL" / "Qwen3.5-4B-Unredacted-MAX"
    assert first.vision is True
    assert first.mmproj is None
    assert first.clip_type is None


def test_hf_entries_accepts_any_listed_architecture(tmp_path):
    write_config(
        tmp_path / "multi",
        {"architectures": ["Other", "Gemma4UnifiedForConditionalGeneration"]},
    )

    assert [e.name for e in hf_entries(tmp_path)] == ["hf: multi"]


def test_hf_entries_missing_root_is_empty(tmp_path):
    assert hf_entries(tmp_path / "absent") == []


def test_hf_entries_unreadable_config_is_skipped(tmp_path):
    (tmp_path / "dir-config" / "config.json").mkdir(parents=True)

    assert hf_entries(tmp_path) == []


def test_hf_entries_does_not_log_for_bad_folders(tmp_path, caplog):
    write_config(tmp_path / "broken", "{not json")

    hf_entries(tmp_path)

    assert caplog.records == []


def test_list_prompter_models_merges_and_sorts(fake_env):
    write_config(
        fake_env.root / "gemma", {"architectures": ["Gemma4ForConditionalGeneration"]}
    )
    fake_env.enhancer = [
        entry("native: z", kind="native", mmproj=None),
        entry("gguf: a.gguf"),
    ]

    names = [e.name for e in list_prompter_models()]

    assert names == ["gguf: a.gguf", "hf: gemma", "native: z"]


def test_list_prompter_models_vision_filter(fake_env):
    fake_env.enhancer = [
        entry("native: text", kind="native", vision=False, mmproj=None),
        entry("native: vl", kind="native", vision=True, mmproj=None),
        entry("gguf: no-proj.gguf", mmproj=None),
        entry("gguf: text.gguf", vision=False),
        entry("gguf: ok.gguf"),
    ]

    names = [e.name for e in list_prompter_models()]

    assert names == ["gguf: ok.gguf", "native: vl"]


def test_list_prompter_models_first_duplicate_wins(fake_env):
    write_config(
        fake_env.root / "dup", {"architectures": ["Gemma4ForConditionalGeneration"]}
    )
    clash = entry("hf: dup", kind="native", mmproj=None)
    fake_env.enhancer = [clash]

    result = list_prompter_models()

    assert [e.name for e in result] == ["hf: dup"]
    assert result[0].kind == "hf"


def test_list_prompter_models_without_llm_folder(fake_env):
    fake_env.enhancer = [entry("gguf: a.gguf")]

    assert [e.name for e in list_prompter_models()] == ["gguf: a.gguf"]


def test_prompter_model_names_none_found(fake_env):
    assert prompter_model_names() == [NONE_FOUND]


def test_find_prompter_model(fake_env):
    fake_env.enhancer = [entry("gguf: a.gguf")]

    assert find_prompter_model("gguf: a.gguf").name == "gguf: a.gguf"
    assert find_prompter_model("missing") is None


@pytest.mark.parametrize(
    "names, expected",
    [
        (["gguf: a", "hf: b", "hf: Qwen3.5-4B-x"], "hf: Qwen3.5-4B-x"),
        (["gguf: a", "hf: b", "hf: c"], "hf: b"),
        (["gguf: a", "native: b"], "gguf: a"),
        ([NONE_FOUND], NONE_FOUND),
    ],
)
def test_default_prompter_model(names, expected):
    assert default_prompter_model(names) == expected


def test_enhancer_picker_is_unchanged(fake_env, monkeypatch):
    sentinel = [entry("gguf: only.gguf")]
    monkeypatch.setattr(enhancer_models, "list_models", lambda: sentinel)
    write_config(
        fake_env.root / "gemma", {"architectures": ["Gemma4ForConditionalGeneration"]}
    )

    list_prompter_models()

    assert enhancer_models.model_names() == ["gguf: only.gguf"]
