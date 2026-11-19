import sys
import types

import pytest
import torch

from kikotools.tools.prompt_enhancer.models import ModelEntry
from kikotools.tools.prompt_enhancer import native_backend
from kikotools.tools.prompt_enhancer.native_backend import generate_native, load_native

IMAGE = torch.zeros(1, 8, 8, 3)
SYSTEM = "You rewrite prompts for an image model. Be concise and visual."


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


def run(clip, image=None, thinking=False):
    return generate_native(clip, SYSTEM, "a cat", image, 7, 0.7, 1024, thinking)


def test_generate_passes_system_prompt_and_sampling():
    clip = FakeClip()
    assert run(clip) == "A cat on a mat."
    assert clip.tokenize_calls[0][1]["system_prompt"] == SYSTEM
    assert clip.generate_calls[0]["seed"] == 7
    assert clip.generate_calls[0]["do_sample"] is True
    assert clip.generate_calls[0]["max_length"] == 1024
    assert clip.generate_calls[0]["temperature"] == 0.7


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


def test_cut_off_thinking_raises():
    clip = FakeClip(output="<think>still reasoning when max_length ran out")
    with pytest.raises(ValueError, match="thinking used up max_length"):
        run(clip, thinking=True)


def test_closed_thinking_returns_raw_text():
    clip = FakeClip(output="<think>x</think>A cat.")
    assert run(clip, thinking=True) == "<think>x</think>A cat."


def test_vision_check_runs_before_system_prompt_check():
    with pytest.raises(ValueError, match="did not take the image"):
        run(FakeClip(vision=False, honours_system=False), image=IMAGE)


@pytest.fixture
def fake_comfy(monkeypatch):
    calls = []
    clip_type = types.SimpleNamespace(MOSS_IMAGE="moss-image-type")
    sd = types.SimpleNamespace(
        CLIPType=clip_type,
        load_clip=lambda **kwargs: calls.append(kwargs) or object(),
    )
    comfy = types.ModuleType("comfy")
    comfy.sd = sd
    monkeypatch.setitem(sys.modules, "comfy", comfy)
    monkeypatch.setitem(sys.modules, "comfy.sd", sd)
    monkeypatch.setitem(
        sys.modules,
        "folder_paths",
        types.SimpleNamespace(get_folder_paths=lambda name: [f"/emb/{name}"]),
    )
    monkeypatch.setattr(native_backend, "_loaded", None)
    return calls


def entry(path="/te/moss.safetensors"):
    return ModelEntry("moss", "native", path, False, None, "moss_image")


def test_load_native_uses_clip_type_and_caches(fake_comfy):
    first = load_native(entry())
    second = load_native(entry())
    assert first is second
    assert len(fake_comfy) == 1
    assert fake_comfy[0] == {
        "ckpt_paths": ["/te/moss.safetensors"],
        "embedding_directory": ["/emb/embeddings"],
        "clip_type": "moss-image-type",
    }


def test_load_native_reloads_for_a_different_path(fake_comfy):
    load_native(entry())
    load_native(entry("/te/other.safetensors"))
    assert len(fake_comfy) == 2
