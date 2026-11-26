import sys
import types
from pathlib import Path

import pytest
import torch
from PIL import Image

from kikotools.tools.h3_reference_prompter import hf_backend
from kikotools.tools.h3_reference_prompter.hf_backend import free_hf, generate_hf
from kikotools.tools.prompt_enhancer.models import ModelEntry

ENTRY = ModelEntry("hf: a", "hf", Path("/m/a"), True, None, None)
OTHER = ModelEntry("hf: b", "hf", Path("/m/b"), True, None, None)
PROMPT_IDS = [[1, 2, 3]]
NEW_IDS = [7, 8]


class FakeBatch(dict):
    """Stands in for transformers' BatchFeature."""

    def to(self, device):
        self.device = device
        return self


class FakeProcessor:
    instances = []
    reject_thinking = False

    def __init__(self, path, kwargs):
        self.path = path
        self.kwargs = kwargs
        self.template_calls = []
        self.decoded = []
        FakeProcessor.instances.append(self)

    @classmethod
    def from_pretrained(cls, path, **kwargs):
        return cls(path, kwargs)

    def apply_chat_template(self, messages, **kwargs):
        self.template_calls.append((messages, kwargs))
        if FakeProcessor.reject_thinking and "enable_thinking" in kwargs:
            raise TypeError("unexpected keyword enable_thinking")
        return FakeBatch(
            input_ids=torch.tensor(PROMPT_IDS), pixel_values=torch.zeros(1)
        )

    def batch_decode(self, ids, **kwargs):
        self.decoded.append((ids, kwargs))
        return ["  A tidy prompt.  "]


class FakeModel:
    instances = []

    def __init__(self, path, kwargs):
        self.path = path
        self.kwargs = kwargs
        self.device = torch.device("cpu")
        self.moved_to = None
        self.generate_calls = []
        self.seeds = []
        FakeModel.instances.append(self)

    @classmethod
    def from_pretrained(cls, path, **kwargs):
        return cls(path, kwargs)

    def to(self, device):
        self.moved_to = device
        return self

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        self.seeds.append(torch.initial_seed())
        return torch.tensor([PROMPT_IDS[0] + NEW_IDS])


@pytest.fixture(autouse=True)
def fake_transformers(monkeypatch):
    FakeProcessor.instances = []
    FakeProcessor.reject_thinking = False
    FakeModel.instances = []
    module = types.ModuleType("transformers")
    module.AutoProcessor = FakeProcessor
    module.AutoModelForImageTextToText = FakeModel
    monkeypatch.setitem(sys.modules, "transformers", module)
    free_hf()
    yield
    free_hf()


def run(entry=ENTRY, image=None, **overrides):
    args = dict(
        system="sys",
        prompt="describe",
        image=image,
        seed=5,
        temperature=0.7,
        max_length=64,
    )
    args.update(overrides)
    return generate_hf(entry, **args)


def test_returns_only_new_tokens_decoded_and_stripped():
    assert run() == "A tidy prompt."
    ids, kwargs = FakeProcessor.instances[0].decoded[0]
    assert ids.tolist() == [NEW_IDS]
    assert kwargs == {"skip_special_tokens": True}


def test_loads_once_for_same_entry_and_reloads_for_another():
    run()
    run()
    assert len(FakeModel.instances) == 1
    run(OTHER)
    assert len(FakeModel.instances) == 2
    assert FakeModel.instances[1].path == str(OTHER.path)


def test_never_trusts_remote_code_and_uses_cpu_float32():
    run()
    assert FakeProcessor.instances[0].kwargs["trust_remote_code"] is False
    model = FakeModel.instances[0]
    assert model.kwargs["trust_remote_code"] is False
    assert model.kwargs["dtype"] == torch.float32
    assert model.moved_to == torch.device("cpu")


def test_uses_bfloat16_on_cuda(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    run()
    model = FakeModel.instances[0]
    assert model.kwargs["dtype"] == torch.bfloat16
    assert model.moved_to == torch.device("cuda")


def test_chat_template_gets_thinking_off_and_generation_prompt():
    run()
    messages, kwargs = FakeProcessor.instances[0].template_calls[0]
    assert kwargs == {
        "tokenize": True,
        "return_dict": True,
        "return_tensors": "pt",
        "add_generation_prompt": True,
        "enable_thinking": False,
    }
    assert messages[0] == {
        "role": "system",
        "content": [{"type": "text", "text": "sys"}],
    }
    assert messages[1] == {
        "role": "user",
        "content": [{"type": "text", "text": "describe"}],
    }


def test_template_rejecting_thinking_keyword_is_retried_without_it():
    FakeProcessor.reject_thinking = True
    assert run() == "A tidy prompt."
    calls = FakeProcessor.instances[0].template_calls
    assert len(calls) == 2
    assert "enable_thinking" not in calls[1][1]


def test_image_becomes_pil_part_before_text():
    frame = torch.zeros(1, 4, 6, 3)
    frame[0, :, :, 0] = 1.5
    frame[0, 0, 0, 1] = 0.5
    run(image=frame)
    content = FakeProcessor.instances[0].template_calls[0][0][1]["content"]
    assert content[0]["type"] == "image"
    pil = content[0]["image"]
    assert isinstance(pil, Image.Image) and pil.mode == "RGB"
    assert pil.size == (6, 4)
    assert pil.getpixel((0, 0)) == (255, 128, 0)
    assert content[1] == {"type": "text", "text": "describe"}


def test_sampling_arguments_and_seed():
    run(seed=2**32 + 9, temperature=0.8, max_length=33)
    model = FakeModel.instances[0]
    call = model.generate_calls[0]
    assert call["max_new_tokens"] == 33
    assert call["do_sample"] is True
    assert call["temperature"] == 0.8
    assert call["input_ids"].tolist() == PROMPT_IDS
    assert "pixel_values" in call
    assert model.seeds == [9]


def test_zero_temperature_is_greedy_without_temperature_argument():
    run(temperature=0)
    call = FakeModel.instances[0].generate_calls[0]
    assert call["do_sample"] is False
    assert "temperature" not in call


def test_generation_runs_in_inference_mode():
    seen = []
    original = FakeModel.generate

    def spy(self, **kwargs):
        seen.append(torch.is_inference_mode_enabled())
        return original(self, **kwargs)

    FakeModel.generate = spy
    try:
        run()
    finally:
        FakeModel.generate = original
    assert seen == [True]


def test_free_hf_clears_slot_and_empties_cuda_cache(monkeypatch):
    run()
    emptied = []
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: emptied.append(1))
    free_hf()
    assert hf_backend._loaded is None
    assert emptied == [1]
    free_hf()
    run()
    assert len(FakeModel.instances) == 2


def test_missing_transformers_raises_value_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "transformers", None)
    with pytest.raises(ValueError, match="install transformers"):
        run()
