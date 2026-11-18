import json
import logging
import struct
import sys
import types
from pathlib import Path

import pytest

from kikotools.tools.prompt_enhancer import models

real_llama_available = models.llama_available

DETECTED = {
    "qwen35_marker": "QWEN35_9B",
    "qwen3_marker": "QWEN3_4B",
    "t5_marker": "T5_XXL",
}


def fake_detect_te_model(sd):
    for key, name in DETECTED.items():
        if key in sd:
            assert sd[key].shape == (8,)
            return types.SimpleNamespace(name=name)
    return None


@pytest.fixture(autouse=True)
def fake_comfy(tmp_path, monkeypatch):
    text_encoders = tmp_path / "text_encoders"
    llm = tmp_path / "LLM"
    text_encoders.mkdir()
    llm.mkdir()
    folder_paths = types.SimpleNamespace(
        models_dir=str(tmp_path),
        get_folder_paths=lambda name: [str(text_encoders)] if name == "text_encoders" else [],
    )
    comfy = types.ModuleType("comfy")
    comfy_sd = types.ModuleType("comfy.sd")
    comfy_sd.detect_te_model = fake_detect_te_model
    comfy.sd = comfy_sd
    monkeypatch.setitem(sys.modules, "folder_paths", folder_paths)
    monkeypatch.setitem(sys.modules, "comfy", comfy)
    monkeypatch.setitem(sys.modules, "comfy.sd", comfy_sd)
    monkeypatch.setattr(models, "llama_available", lambda: True)
    models._native_cache.clear()
    return types.SimpleNamespace(text_encoders=text_encoders, llm=llm)


def write_safetensors(path: Path, key: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = json.dumps(
        {
            "__metadata__": {"format": "pt"},
            key: {"dtype": "F16", "shape": [8], "data_offsets": [0, 0]},
        }
    ).encode("utf-8")
    path.write_bytes(struct.pack("<Q", len(header)) + header)
    return path


def touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"GGUF")
    return path


def test_native_listed_with_clip_type(fake_comfy):
    path = write_safetensors(fake_comfy.text_encoders / "Moss" / "x.safetensors", "qwen35_marker")
    [entry] = models.list_models()
    assert entry.name == "native: Moss/x.safetensors"
    assert entry.kind == "native"
    assert entry.path == path
    assert entry.clip_type == "moss_image"
    assert entry.vision is True
    assert entry.mmproj is None


def test_native_text_only_qwen3_4b(fake_comfy):
    write_safetensors(fake_comfy.text_encoders / "qwen3_4b.safetensors", "qwen3_marker")
    [entry] = models.list_models()
    assert entry.clip_type == "lumina2"
    assert entry.vision is False


def test_unmapped_native_excluded(fake_comfy):
    write_safetensors(fake_comfy.text_encoders / "t5xxl.safetensors", "t5_marker")
    assert models.list_models() == []


def test_corrupt_safetensors_skipped(fake_comfy, caplog):
    bad = fake_comfy.text_encoders / "broken.safetensors"
    bad.write_bytes(b"\x05\x00")
    write_safetensors(fake_comfy.text_encoders / "good.safetensors", "qwen3_marker")
    with caplog.at_level(logging.WARNING):
        names = models.model_names()
    assert names == ["native: good.safetensors"]
    assert "broken.safetensors" in caplog.text


def test_gguf_vision_with_mmproj(fake_comfy):
    folder = fake_comfy.llm / "GGUF" / "huihui"
    model = touch(folder / "Huihui-Qwen3.8-27B-Q4_K_M.gguf")
    mmproj = touch(folder / "mmproj-Qwen3.8-27B-f16.gguf")
    [entry] = models.list_models()
    assert entry.name == "gguf: GGUF/huihui/Huihui-Qwen3.8-27B-Q4_K_M.gguf"
    assert entry.kind == "gguf"
    assert entry.path == model
    assert entry.vision is True
    assert entry.mmproj == mmproj
    assert entry.clip_type is None


def test_mmproj_shared_by_all_quants(fake_comfy):
    folder = fake_comfy.llm / "qwen"
    touch(folder / "qwen-Q4_K_M.gguf")
    touch(folder / "qwen-Q8_0.gguf")
    mmproj = touch(folder / "qwen-mmproj.gguf")
    entries = models.list_models()
    assert [entry.name for entry in entries] == ["gguf: qwen/qwen-Q4_K_M.gguf", "gguf: qwen/qwen-Q8_0.gguf"]
    assert all(entry.vision and entry.mmproj == mmproj for entry in entries)


def test_gguf_without_mmproj_is_text_only(fake_comfy):
    touch(fake_comfy.llm / "Qwen3-4B-abliterated-q8_0.gguf")
    [entry] = models.list_models()
    assert entry.vision is False
    assert entry.mmproj is None


def test_umt5_gguf_excluded(fake_comfy):
    touch(fake_comfy.text_encoders / "Wan2.2" / "umt5-xxl-encoder-Q8_0.gguf")
    assert models.list_models() == []


def test_gguf_in_text_encoders_listed(fake_comfy):
    touch(fake_comfy.text_encoders / "Llama-3.1-8B-Q4_K_M.gguf")
    assert models.model_names() == ["gguf: Llama-3.1-8B-Q4_K_M.gguf"]


def test_gguf_hidden_without_llama_cpp(fake_comfy, monkeypatch):
    monkeypatch.setattr(models, "llama_available", lambda: False)
    touch(fake_comfy.llm / "qwen-Q4_K_M.gguf")
    write_safetensors(fake_comfy.text_encoders / "qwen3_4b.safetensors", "qwen3_marker")
    assert models.model_names() == ["native: qwen3_4b.safetensors"]


def test_llama_missing_logged_once(monkeypatch, caplog):
    real = real_llama_available
    real.cache_clear()
    monkeypatch.setattr(models.importlib.util, "find_spec", lambda name: None)
    with caplog.at_level(logging.INFO):
        assert real() is False
        assert real() is False
    real.cache_clear()
    assert caplog.text.count("llama-cpp-python is not installed") == 1


def test_none_found_placeholder():
    assert models.model_names() == [models.NONE_FOUND]


def test_find_model_round_trip(fake_comfy):
    write_safetensors(fake_comfy.text_encoders / "Moss" / "x.safetensors", "qwen35_marker")
    touch(fake_comfy.llm / "qwen-Q4_K_M.gguf")
    for name in models.model_names():
        assert models.find_model(name).name == name
    assert models.find_model("gguf: missing.gguf") is None
    assert models.find_model(models.NONE_FOUND) is None


def test_native_detection_cached(fake_comfy, monkeypatch):
    write_safetensors(fake_comfy.text_encoders / "qwen3_4b.safetensors", "qwen3_marker")
    models.list_models()
    monkeypatch.setattr(sys.modules["comfy.sd"], "detect_te_model", lambda sd: pytest.fail("not cached"))
    assert models.model_names() == ["native: qwen3_4b.safetensors"]
