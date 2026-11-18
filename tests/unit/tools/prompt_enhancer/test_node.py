import sys
import types
from pathlib import Path

import pytest
import torch

import kikotools
from kikotools.tools.prompt_enhancer.library import load_prompt
from kikotools.tools.prompt_enhancer.models import NONE_FOUND, ModelEntry
from kikotools.tools.prompt_enhancer import node as node_module
from kikotools.tools.prompt_enhancer.node import PromptEnhancerNode


@pytest.fixture(autouse=True)
def fake_user_dir(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "folder_paths",
        types.SimpleNamespace(get_user_directory=lambda: str(tmp_path)),
    )
    monkeypatch.setattr(node_module, "model_names", lambda: [NONE_FOUND])
    return tmp_path


def write_override(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / "kikotools" / "system_prompts" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class FakeEncoder:
    pass


class FakeClip:
    """Records calls; decode echoes the system prompt unless told to drop it."""

    def __init__(self, output="A cat on a mat.", vision=True, honours_system=True):
        self.cond_stage_model = FakeEncoder()
        self.output = output
        self.vision = vision
        self.honours_system = honours_system
        self.generated = [99, 100]
        self.tokenize_calls = []
        self.generate_calls = []

    def tokenize(self, text, **kwargs):
        self.tokenize_calls.append((text, kwargs))
        self.prompt_text = (
            kwargs["system_prompt"] if self.honours_system else ""
        ) + text
        tokens = [(1, 1.0), (2, 1.0)]
        if kwargs.get("image") is not None and self.vision:
            tokens.append(({"type": "image", "data": kwargs["image"]}, 1.0))
        return {"qwen35": [tokens, [(3, 1.0)]]}

    def generate(self, tokens, **kwargs):
        self.generate_calls.append(kwargs)
        return self.generated

    def decode(self, token_ids, skip_special_tokens=True):
        if token_ids is self.generated:
            return self.output
        assert token_ids == [1, 2, 3]
        return self.prompt_text


IMAGE = torch.zeros(1, 8, 8, 3)
NO_TEXT = load_prompt("krea2").no_text_sentence


def run(clip, prompt="a cat", base_model="krea2", model=NONE_FOUND, **kwargs):
    mode = kwargs.pop("mode", "text" if kwargs.get("image") is None else "vision")
    return PromptEnhancerNode().enhance(
        prompt, base_model, model, mode, 7, clip=clip, **kwargs
    )


def entry(name, kind="gguf", vision=False):
    return ModelEntry(name, kind, Path("/models") / name, vision, None, "flux2")


@pytest.fixture
def backends(monkeypatch):
    """Replace both backends and the model lookup; records every call."""
    calls = {"native": [], "gguf": [], "load": []}
    entries = {}

    def fake_native(*args):
        calls["native"].append(args)
        return "A cat."

    def fake_gguf(*args):
        calls["gguf"].append(args)
        return calls.get("gguf_output", "A cat.")

    def fake_load(found):
        calls["load"].append(found)
        return "loaded-clip"

    monkeypatch.setattr(node_module, "generate_native", fake_native)
    monkeypatch.setattr(node_module, "generate_gguf", fake_gguf)
    monkeypatch.setattr(node_module, "load_native", fake_load)
    monkeypatch.setattr(node_module, "find_model", entries.get)
    calls["entries"] = entries
    return calls


def test_registered_in_package():
    assert kikotools.NODE_CLASS_MAPPINGS["KikoPromptEnhancer"] is PromptEnhancerNode
    assert (
        kikotools.NODE_DISPLAY_NAME_MAPPINGS["KikoPromptEnhancer"]
        == "Kiko Prompt Enhancer"
    )


def test_input_types_lists_base_models_and_default(tmp_path):
    write_override(tmp_path, "aaa.md", "x")
    names, options = PromptEnhancerNode.INPUT_TYPES()["required"]["base_model"]
    assert names == sorted(names)
    assert names[0] == "aaa"
    assert "krea2" in names
    assert options["default"] == "krea2"


def test_enhance_passes_system_prompt_and_seed():
    clip = FakeClip()
    final, system = run(clip)
    expected = load_prompt("krea2").text
    assert system == expected
    assert clip.tokenize_calls[0][1]["system_prompt"] == expected
    assert clip.generate_calls[0]["seed"] == 7
    assert clip.generate_calls[0]["do_sample"] is True
    assert final == f"A cat on a mat. {NO_TEXT}"


def test_trigger_words_not_sent_to_encoder_and_prepended():
    clip = FakeClip()
    final, _ = run(clip, trigger_words="mabes9sans")
    assert "mabes9sans" not in clip.tokenize_calls[0][0]
    assert final.startswith("mabes9sans, ")


def test_trigger_words_stripped_from_prompt_before_encoder():
    clip = FakeClip()
    final, _ = run(clip, prompt="Mabes9sans woman in the rain", trigger_words="mabes9sans")
    assert clip.tokenize_calls[0][0] == "woman in the rain"
    assert final == f"mabes9sans, A cat on a mat. {NO_TEXT}"


def test_trigger_only_prompt_raises():
    with pytest.raises(ValueError, match="only contains trigger words"):
        run(FakeClip(), prompt="mabes9sans, vito", trigger_words="mabes9sans, vito")


def test_trigger_only_prompt_with_image_runs():
    clip = FakeClip()
    run(clip, prompt="mabes9sans", trigger_words="mabes9sans", image=IMAGE)
    assert clip.tokenize_calls[0][0] == ""


def test_image_section_appended_only_with_image(tmp_path):
    write_override(tmp_path, "vid.md", "Body text\n## With an image\nMotion only.")
    clip = FakeClip()
    _, with_image = run(clip, base_model="vid", image=IMAGE)
    _, without = run(clip, base_model="vid")
    assert clip.tokenize_calls[0][1]["system_prompt"] == "Body text\n\nMotion only."
    assert with_image == "Body text\n\nMotion only."
    assert without == "Body text"
    assert clip.tokenize_calls[1][1]["image"] is None


def test_empty_prompt_without_image_raises():
    with pytest.raises(ValueError, match="prompt is empty"):
        run(FakeClip(), prompt="   ")


def test_empty_prompt_with_image_runs():
    final, _ = run(FakeClip(), prompt="", image=IMAGE)
    assert final == f"A cat on a mat. {NO_TEXT}"


def test_output_is_cleaned_and_capped(tmp_path):
    write_override(tmp_path, "short.md", "---\nmax_words: 2\n---\nKeep it short.")
    clip = FakeClip(
        output='<think>x</think>Here is the prompt:\n"One two. Three four."'
    )
    final, _ = run(clip, base_model="short")
    assert final == "One two."


def test_node_appends_no_text_within_cap(tmp_path):
    write_override(
        tmp_path,
        "plain.md",
        "---\nmax_words: 10\nno_text_sentence: No text here.\n---\nBody",
    )
    clip = FakeClip(output="w1 w2 w3 w4 w5 w6 w7 w8 w9 w10 w11 w12")
    final, _ = run(clip, base_model="plain")
    assert final == "w1 w2 w3 w4 w5 w6 w7 No text here."


def test_node_skips_no_text_when_quoted(tmp_path):
    write_override(
        tmp_path,
        "plain.md",
        "---\nmax_words: 10\nno_text_sentence: No text here.\n---\nBody",
    )
    clip = FakeClip(output='A sign reading "OPEN" hangs.')
    final, _ = run(clip, base_model="plain")
    assert final == 'A sign reading "OPEN" hangs.'


@pytest.mark.parametrize(
    "output",
    [
        " ".join(f"w{i}" for i in range(20)) + ' "OPEN" tail',
        " ".join(f"w{i}" for i in range(20)) + ' "unpaired tail',
    ],
)
def test_node_stays_within_cap_with_late_or_unpaired_quote(tmp_path, output):
    write_override(
        tmp_path,
        "plain.md",
        "---\nmax_words: 10\nno_text_sentence: No text here.\n---\nBody",
    )
    final, _ = run(FakeClip(output=output), base_model="plain")
    assert len(final.split()) <= 10


def test_is_changed_follows_file_content(tmp_path):
    path = write_override(tmp_path, "mine.md", "first")
    before = PromptEnhancerNode.IS_CHANGED(base_model="mine", model="m", mode="text", seed=1)
    path.write_text("second", encoding="utf-8")
    assert PromptEnhancerNode.IS_CHANGED(base_model="mine", model="m", mode="text", seed=1) != before


def test_is_changed_follows_header_edits(tmp_path):
    path = write_override(tmp_path, "mine.md", "---\nmax_words: 50\n---\nBody")
    before = PromptEnhancerNode.IS_CHANGED(base_model="mine", model="m", mode="text", seed=1)
    path.write_text("---\nmax_words: 80\n---\nBody", encoding="utf-8")
    assert PromptEnhancerNode.IS_CHANGED(base_model="mine", model="m", mode="text", seed=1) != before


def test_enhance_calls_backend_and_runs_pipeline(monkeypatch):
    calls = []

    def fake_generate(*args):
        calls.append(args)
        return "<think>x</think>A cat."

    monkeypatch.setattr(node_module, "generate_native", fake_generate)
    clip = object()
    final, system = run(
        clip,
        prompt="Mabes9sans a cat",
        trigger_words="mabes9sans",
        image=IMAGE,
        temperature=0.5,
        max_length=256,
        thinking=True,
    )
    assert calls == [(clip, system, "a cat", IMAGE, 7, 0.5, 256, True)]
    krea = load_prompt("krea2")
    assert system == krea.text + "\n\n" + krea.image_text if krea.image_text else krea.text
    assert final == f"mabes9sans, A cat. {NO_TEXT}"


def test_closed_thinking_returns_answer():
    final, _ = run(FakeClip(output="<think>x</think>A cat."), thinking=True)
    assert final == f"A cat. {NO_TEXT}"


def test_empty_system_prompt_raises(tmp_path):
    write_override(tmp_path, "blank.md", "---\nmax_words: 50\n---\n  \n")
    with pytest.raises(ValueError, match="system prompt file 'blank' is empty"):
        run(FakeClip(), base_model="blank")


def test_input_order_and_mode_combo(monkeypatch):
    monkeypatch.setattr(node_module, "model_names", lambda: ["gguf: a.gguf"])
    types_ = PromptEnhancerNode.INPUT_TYPES()
    assert list(types_["required"]) == ["prompt", "base_model", "model", "mode", "seed"]
    assert list(types_["optional"]) == [
        "clip", "trigger_words", "image", "temperature", "max_length", "thinking", "keep_loaded",
    ]
    modes, options = types_["required"]["mode"]
    assert modes == ["text", "vision"]
    assert options["default"] == "text"
    assert types_["optional"]["keep_loaded"][1] == {"default": False, "advanced": True}


@pytest.mark.parametrize(
    "names, expected",
    [
        (["gguf: a.gguf", "gguf: Qwen3-Heretic.gguf", "native: x-uncensored.safetensors"], "gguf: Qwen3-Heretic.gguf"),
        (["gguf: a.gguf", "native: Qwen3-8B-ABLITERATED.safetensors"], "native: Qwen3-8B-ABLITERATED.safetensors"),
        (["gguf: a.gguf", "native: b.safetensors"], "gguf: a.gguf"),
        ([NONE_FOUND], NONE_FOUND),
    ],
)
def test_default_model_prefers_uncensored(monkeypatch, names, expected):
    monkeypatch.setattr(node_module, "model_names", lambda: names)
    listed, options = PromptEnhancerNode.INPUT_TYPES()["required"]["model"]
    assert listed == names
    assert options["default"] == expected


def test_text_mode_drops_image(tmp_path, backends):
    write_override(tmp_path, "vid.md", "Body text\n## With an image\nMotion only.")
    clip = object()
    _, system = run(clip, base_model="vid", image=IMAGE, mode="text")
    assert system == "Body text"
    assert backends["native"][0][3] is None


def test_text_mode_empty_prompt_with_image_raises(backends):
    with pytest.raises(ValueError, match="prompt is empty"):
        run(object(), prompt="", image=IMAGE, mode="text")


def test_vision_mode_requires_image(backends):
    with pytest.raises(ValueError) as error:
        run(object(), mode="vision")
    assert str(error.value) == "vision mode needs an image; connect one to the image input"
    assert backends["native"] == []


def test_vision_mode_rejects_text_only_model(backends):
    backends["entries"]["gguf: q.gguf"] = entry("gguf: q.gguf", vision=False)
    with pytest.raises(ValueError) as error:
        run(None, model="gguf: q.gguf", image=IMAGE, mode="vision")
    assert str(error.value) == (
        "gguf: q.gguf cannot read images; pick a vision model "
        "(one with an mmproj file, or a Qwen-VL / Qwen3.5 encoder)"
    )
    assert backends["gguf"] == []


def test_connected_clip_overrides_none_found(backends):
    clip = object()
    final, system = run(clip, model=NONE_FOUND)
    assert backends["native"] == [(clip, system, "a cat", None, 7, 0.7, 1024, False)]
    assert backends["load"] == []
    assert final == f"A cat. {NO_TEXT}"


def test_connected_clip_overrides_selected_model(backends):
    backends["entries"]["gguf: q.gguf"] = entry("gguf: q.gguf")
    clip = object()
    run(clip, model="gguf: q.gguf")
    assert backends["gguf"] == []
    assert backends["native"][0][0] is clip


def test_gguf_entry_dispatches_to_gguf(backends):
    found = entry("gguf: q.gguf", vision=True)
    backends["entries"]["gguf: q.gguf"] = found
    final, system = run(
        None, model="gguf: q.gguf", image=IMAGE, mode="vision",
        temperature=0.5, max_length=256, thinking=True, keep_loaded=True,
    )
    assert backends["gguf"] == [(found, system, "a cat", IMAGE, 7, 0.5, 256, True, True)]
    assert backends["native"] == []
    assert final == f"A cat. {NO_TEXT}"


def test_gguf_empty_think_block_is_removed(tmp_path, backends):
    write_override(tmp_path, "plain.md", "Body")
    backends["entries"]["gguf: q.gguf"] = entry("gguf: q.gguf")
    backends["gguf_output"] = "<think>\n\n</think>\n\nA fox."
    final, _ = run(None, base_model="plain", model="gguf: q.gguf")
    assert final == "A fox."


def test_native_entry_loads_and_dispatches(backends):
    found = entry("native: q.safetensors", kind="native")
    backends["entries"]["native: q.safetensors"] = found
    final, system = run(None, model="native: q.safetensors")
    assert backends["load"] == [found]
    assert backends["native"] == [("loaded-clip", system, "a cat", None, 7, 0.7, 1024, False)]
    assert backends["gguf"] == []
    assert final == f"A cat. {NO_TEXT}"


@pytest.mark.parametrize("model", [NONE_FOUND, "gguf: gone.gguf"])
def test_no_model_no_clip_raises(backends, model):
    with pytest.raises(ValueError) as error:
        run(None, model=model)
    assert str(error.value) == (
        "No model selected and no clip connected; pick a model or connect an encoder"
    )


def test_is_changed_follows_model_and_mode(tmp_path):
    write_override(tmp_path, "mine.md", "first")
    base = PromptEnhancerNode.IS_CHANGED(base_model="mine", model="a", mode="text", seed=1)
    assert PromptEnhancerNode.IS_CHANGED(base_model="mine", model="a", mode="text", seed=2) == base
    assert PromptEnhancerNode.IS_CHANGED(base_model="mine", model="b", mode="text", seed=1) != base
    assert PromptEnhancerNode.IS_CHANGED(base_model="mine", model="a", mode="vision", seed=1) != base
