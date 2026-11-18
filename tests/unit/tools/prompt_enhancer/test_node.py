import sys
import types
from pathlib import Path

import pytest
import torch

import kikotools
from kikotools.tools.prompt_enhancer.library import load_prompt
from kikotools.tools.prompt_enhancer.node import PromptEnhancerNode


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


def run(clip, prompt="a cat", base_model="krea2", **kwargs):
    return PromptEnhancerNode().enhance(clip, prompt, base_model, 7, **kwargs)


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


def test_image_with_non_vision_encoder_raises():
    with pytest.raises(ValueError, match="FakeEncoder did not take the image"):
        run(FakeClip(vision=False), image=IMAGE)


def test_ignored_system_prompt_raises():
    with pytest.raises(ValueError, match="ignored the system prompt"):
        run(FakeClip(honours_system=False))


def test_missing_generate_raises():
    class OldClip:
        def tokenize(self, text, **kwargs):
            return {}

    with pytest.raises(ValueError, match="too old for text generation"):
        run(OldClip())


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


def test_is_changed_follows_file_content(tmp_path):
    path = write_override(tmp_path, "mine.md", "first")
    before = PromptEnhancerNode.IS_CHANGED(base_model="mine", seed=1)
    path.write_text("second", encoding="utf-8")
    assert PromptEnhancerNode.IS_CHANGED(base_model="mine", seed=1) != before


def test_is_changed_follows_header_edits(tmp_path):
    path = write_override(tmp_path, "mine.md", "---\nmax_words: 50\n---\nBody")
    before = PromptEnhancerNode.IS_CHANGED(base_model="mine", seed=1)
    path.write_text("---\nmax_words: 80\n---\nBody", encoding="utf-8")
    assert PromptEnhancerNode.IS_CHANGED(base_model="mine", seed=1) != before


def test_cut_off_thinking_raises():
    clip = FakeClip(output="<think>still reasoning when max_length ran out")
    with pytest.raises(ValueError, match="thinking used up max_length"):
        run(clip, thinking=True)


def test_closed_thinking_returns_answer():
    final, _ = run(FakeClip(output="<think>x</think>A cat."), thinking=True)
    assert final == f"A cat. {NO_TEXT}"


def test_empty_system_prompt_raises(tmp_path):
    write_override(tmp_path, "blank.md", "---\nmax_words: 50\n---\n  \n")
    with pytest.raises(ValueError, match="system prompt file 'blank' is empty"):
        run(FakeClip(), base_model="blank")


def test_vision_check_runs_before_system_prompt_check():
    with pytest.raises(ValueError, match="did not take the image"):
        run(FakeClip(vision=False, honours_system=False), image=IMAGE)
