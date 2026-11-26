import json
import sys
import types
from pathlib import Path

import pytest
import torch
from PIL import Image

from kikotools.tools.h3_reference_prompter import hf_backend
from kikotools.tools.h3_reference_prompter.hf_backend import (
    HF_BATCH_SIZE,
    free_hf,
    generate_hf,
    generate_hf_batch,
)
from kikotools.tools.prompt_enhancer.models import ModelEntry

BATCH_ARCHITECTURES = getattr(hf_backend, "BATCH_ARCHITECTURES", ())
MAX_IMAGE_PIXELS = getattr(hf_backend, "MAX_IMAGE_PIXELS", None)
READ_ARCHITECTURES = getattr(hf_backend, "_read_architectures", None)
ENTRY = ModelEntry("hf: a", "hf", Path("/m/a"), True, None, None)
OTHER = ModelEntry("hf: b", "hf", Path("/m/b"), True, None, None)
PROMPT_IDS = [[1, 2, 3]]
NEW_IDS = [7, 8]


class FakeBatch(dict):
    """Stands in for transformers' BatchFeature."""

    def to(self, *, device, dtype):
        self.device = device
        self.dtype = dtype
        return self


def _prompt_ids(conversation):
    """Digit prompts tokenize to a request-specific, variable-length row."""
    text = conversation[-1]["content"][-1]["text"]
    if not text.isdigit():
        return PROMPT_IDS[0]
    number = int(text)
    return [9] * (number % 3) + [10 + number]


class FakeProcessor:
    instances = []
    raises = None
    chat_template = "{% if enable_thinking %}x{% endif %}"

    def __init__(self, path, kwargs):
        self.path = path
        self.kwargs = kwargs
        self.template_calls = []
        self.padding_sides = []
        self.decoded = []
        self.tokenizer = types.SimpleNamespace(padding_side="right")
        FakeProcessor.instances.append(self)

    @classmethod
    def from_pretrained(cls, path, **kwargs):
        return cls(path, kwargs)

    def apply_chat_template(self, conversations, **kwargs):
        self.template_calls.append((conversations, kwargs))
        self.padding_sides.append(self.tokenizer.padding_side)
        if FakeProcessor.raises is not None:
            raise FakeProcessor.raises
        rows = [_prompt_ids(conversation) for conversation in conversations]
        width = max(len(row) for row in rows)
        padded = [[0] * (width - len(row)) + row for row in rows]
        mask = [[0] * (width - len(row)) + [1] * len(row) for row in rows]
        return FakeBatch(
            input_ids=torch.tensor(padded),
            attention_mask=torch.tensor(mask),
            pixel_values=torch.zeros(1),
        )

    def batch_decode(self, ids, **kwargs):
        self.decoded.append((ids, kwargs))
        return [
            "  A tidy prompt.  " if row == NEW_IDS else f" r{row[0] - 14} "
            for row in ids.tolist()
        ]


class FakeModel:
    instances = []

    def __init__(self, path, kwargs):
        self.path = path
        self.kwargs = kwargs
        self.device = torch.device("cpu")
        self.dtype = kwargs["dtype"]
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
        ids = kwargs["input_ids"]
        last = ids[:, -1:]
        return torch.cat([ids, last + 4, last + 5], dim=1)


QWEN3_VL = ("Qwen3VLForConditionalGeneration",)
ARCHITECTURES = {"value": QWEN3_VL, "reads": []}


def fake_read_architectures(path):
    ARCHITECTURES["reads"].append(path)
    return ARCHITECTURES["value"]


@pytest.fixture(autouse=True)
def fake_transformers(monkeypatch):
    ARCHITECTURES["value"] = QWEN3_VL
    ARCHITECTURES["reads"] = []
    monkeypatch.setattr(
        hf_backend, "_read_architectures", fake_read_architectures, raising=False
    )
    FakeProcessor.instances = []
    FakeProcessor.chat_template = "{% if enable_thinking %}x{% endif %}"
    FakeProcessor.raises = None
    FakeModel.instances = []
    module = types.ModuleType("transformers")
    module.__version__ = "5.19.0"
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
    (messages,), kwargs = FakeProcessor.instances[0].template_calls[0]
    assert kwargs == {
        "tokenize": True,
        "return_dict": True,
        "return_tensors": "pt",
        "add_generation_prompt": True,
        "processor_kwargs": {"padding": True},
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


@pytest.mark.parametrize(
    "template, expected",
    [
        ("{{ enable_thinking }}", True),
        ("plain template", False),
        ({"default": "plain", "alt": "{% if enable_thinking %}"}, False),
        ({"default": "{{ enable_thinking }}", "alt": "plain"}, True),
        ({"alt": "{{ enable_thinking }}"}, False),
        ({"default": None}, False),
        (None, False),
    ],
)
def test_enable_thinking_only_for_templates_that_use_it(template, expected):
    FakeProcessor.chat_template = template
    run()
    kwargs = FakeProcessor.instances[0].template_calls[0][1]
    assert ("enable_thinking" in kwargs) is expected
    if expected:
        assert kwargs["enable_thinking"] is False


def test_type_error_from_template_propagates():
    FakeProcessor.raises = TypeError("bad image")
    with pytest.raises(TypeError, match="bad image"):
        run()
    assert len(FakeProcessor.instances[0].template_calls) == 1


def test_inputs_are_cast_to_the_model_dtype(monkeypatch):
    seen = []
    original = FakeBatch.to

    def spy(self, **kwargs):
        seen.append(kwargs)
        return original(self, **kwargs)

    monkeypatch.setattr(FakeBatch, "to", spy)
    run()
    assert seen == [{"device": torch.device("cpu"), "dtype": torch.float32}]


def test_image_becomes_pil_part_before_text():
    frame = torch.zeros(1, 4, 6, 3)
    frame[0, :, :, 0] = 1.5
    frame[0, 0, 0, 1] = 0.5
    run(image=frame)
    content = FakeProcessor.instances[0].template_calls[0][0][0][1]["content"]
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


def test_repetition_penalty_is_passed_to_generate():
    run()
    call = FakeModel.instances[0].generate_calls[0]
    assert call["repetition_penalty"] == 1.05
    run(temperature=0)
    assert FakeModel.instances[0].generate_calls[1]["repetition_penalty"] == 1.05


def batch(requests, seed=5, temperature=0.7, max_length=64):
    return generate_hf_batch(ENTRY, requests, seed, temperature, max_length)


def text_request(number):
    return ("sys", str(number), None)


def image_request(number):
    return ("sys", str(number), torch.zeros(1, 2, 2, 3))


def test_batch_returns_results_in_request_order_with_padding_sliced_off():
    assert batch([text_request(n) for n in (2, 0, 1)]) == ["r2", "r0", "r1"]
    processor = FakeProcessor.instances[0]
    assert len(processor.template_calls) == 1
    ids, kwargs = processor.decoded[0]
    assert ids.tolist() == [[16, 17], [14, 15], [15, 16]]
    assert kwargs == {"skip_special_tokens": True}


def test_batch_tokenizes_all_conversations_padded_in_one_call():
    batch([text_request(1), text_request(2)])
    conversations, kwargs = FakeProcessor.instances[0].template_calls[0]
    assert [c[1]["content"] for c in conversations] == [
        [{"type": "text", "text": "1"}],
        [{"type": "text", "text": "2"}],
    ]
    assert all(
        c[0]["content"] == [{"type": "text", "text": "sys"}] for c in conversations
    )
    assert kwargs["processor_kwargs"] == {"padding": True}
    call = FakeModel.instances[0].generate_calls[0]
    assert call["attention_mask"].tolist() == [[0, 1, 1], [1, 1, 1]]


def test_batch_pads_on_the_left_then_restores_the_padding_side():
    batch([text_request(1), text_request(2)])
    processor = FakeProcessor.instances[0]
    assert processor.padding_sides == ["left"]
    assert processor.tokenizer.padding_side == "right"


def test_batch_restores_the_padding_side_after_an_error():
    batch([text_request(1)])
    processor = FakeProcessor.instances[0]
    FakeProcessor.raises = TypeError("bad image")
    with pytest.raises(TypeError, match="bad image"):
        batch([text_request(1)])
    assert processor.tokenizer.padding_side == "right"


def test_batch_splits_into_chunks_of_four_each_seeded_alike():
    assert HF_BATCH_SIZE == 4
    out = batch([text_request(n) for n in range(9)], seed=2**32 + 3)
    assert out == [f"r{n}" for n in range(9)]
    calls = FakeProcessor.instances[0].template_calls
    assert [len(conversations) for conversations, _ in calls] == [4, 4, 1]
    model = FakeModel.instances[0]
    assert len(model.generate_calls) == 3
    assert model.seeds == [3, 3, 3]


def test_batch_never_mixes_image_and_text_requests():
    requests = [
        image_request(0),
        text_request(1),
        image_request(2),
        text_request(3),
        text_request(4),
    ]
    assert batch(requests) == ["r0", "r1", "r2", "r3", "r4"]
    calls = FakeProcessor.instances[0].template_calls
    kinds = [
        [c[1]["content"][0]["type"] for c in conversations]
        for conversations, _ in calls
    ]
    assert kinds == [["image", "image"], ["text", "text", "text"]]


def test_batch_uses_generate_hf_sampling_settings():
    batch([text_request(1), text_request(2)], temperature=0, max_length=21)
    call = FakeModel.instances[0].generate_calls[0]
    assert call["do_sample"] is False and "temperature" not in call
    assert call["max_new_tokens"] == 21
    assert call["repetition_penalty"] == 1.05


def test_empty_batch_returns_nothing_without_loading():
    assert batch([]) == []
    assert FakeModel.instances == []


def test_generate_hf_is_a_one_request_batch(monkeypatch):
    seen = []
    monkeypatch.setattr(
        hf_backend,
        "generate_hf_batch",
        lambda *args: seen.append(args) or ["only"],
    )
    image = torch.zeros(1, 2, 2, 3)
    assert generate_hf(ENTRY, "s", "p", image, 3, 0.5, 9) == "only"
    assert seen == [(ENTRY, [("s", "p", image)], 3, 0.5, 9)]


def test_large_image_is_scaled_to_about_one_megapixel_keeping_aspect():
    assert MAX_IMAGE_PIXELS == 1_048_576
    run(image=torch.zeros(1, 1500, 2000, 3))
    pil = FakeProcessor.instances[0].template_calls[0][0][0][1]["content"][0]["image"]
    width, height = pil.size
    assert width * height <= MAX_IMAGE_PIXELS
    assert width * height > 0.99 * MAX_IMAGE_PIXELS
    assert abs(width / height - 2000 / 1500) < 0.01


def test_large_image_uses_lanczos(monkeypatch):
    seen = []
    original = Image.Image.resize

    def spy(self, size, resample=None, *args, **kwargs):
        seen.append(resample)
        return original(self, size, resample, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "resize", spy)
    hf_backend._to_pil(torch.zeros(1, 1100, 1100, 3))
    assert seen == [Image.Resampling.LANCZOS]


@pytest.mark.parametrize("shape", [(1, 4, 6, 3), (1, 1024, 1024, 3)])
def test_small_image_keeps_its_size(shape):
    pil = hf_backend._to_pil(torch.zeros(*shape))
    assert pil.size == (shape[2], shape[1])


def test_batch_architectures_are_the_verified_qwen_families():
    assert BATCH_ARCHITECTURES == (
        "Qwen3VLForConditionalGeneration",
        "Qwen3_5ForConditionalGeneration",
    )


@pytest.mark.parametrize("arch", BATCH_ARCHITECTURES)
def test_verified_architectures_batch(arch):
    ARCHITECTURES["value"] = ("Other", arch)
    batch([text_request(n) for n in range(5)])
    calls = FakeProcessor.instances[0].template_calls
    assert [len(conversations) for conversations, _ in calls] == [4, 1]


@pytest.mark.parametrize("architectures", [("Gemma4ForConditionalGeneration",), ()])
def test_other_architectures_run_one_request_at_a_time_in_order(architectures):
    ARCHITECTURES["value"] = architectures
    requests = [image_request(0), text_request(1), image_request(2)]
    assert batch(requests) == ["r0", "r1", "r2"]
    calls = FakeProcessor.instances[0].template_calls
    assert [len(conversations) for conversations, _ in calls] == [1, 1, 1]
    assert len(FakeModel.instances[0].generate_calls) == 3


def test_architectures_are_read_once_per_load():
    run()
    run()
    assert ARCHITECTURES["reads"] == [ENTRY.path]
    run(OTHER)
    assert ARCHITECTURES["reads"] == [ENTRY.path, OTHER.path]


@pytest.mark.parametrize("version", ["4.57.1", "4.0", "", "dev"])
def test_transformers_below_5_runs_alone_without_processor_kwargs(version):
    sys.modules["transformers"].__version__ = version
    assert batch([text_request(n) for n in range(3)]) == ["r0", "r1", "r2"]
    calls = FakeProcessor.instances[0].template_calls
    assert [len(conversations) for conversations, _ in calls] == [1, 1, 1]
    assert all("processor_kwargs" not in kwargs for _, kwargs in calls)


def test_transformers_without_version_runs_alone():
    del sys.modules["transformers"].__version__
    batch([text_request(1), text_request(2)])
    calls = FakeProcessor.instances[0].template_calls
    assert [len(conversations) for conversations, _ in calls] == [1, 1]


def test_transformers_5_batches_with_processor_kwargs():
    sys.modules["transformers"].__version__ = "5.0.0"
    batch([text_request(1), text_request(2)])
    ((conversations, kwargs),) = FakeProcessor.instances[0].template_calls
    assert len(conversations) == 2
    assert kwargs["processor_kwargs"] == {"padding": True}


def test_only_named_template_arguments_are_passed():
    FakeProcessor.chat_template = "plain"
    run()
    kwargs = FakeProcessor.instances[0].template_calls[0][1]
    assert set(kwargs) == {
        "tokenize",
        "return_dict",
        "return_tensors",
        "add_generation_prompt",
        "processor_kwargs",
    }


def write_config(folder, content):
    folder.mkdir()
    (folder / "config.json").write_text(content, encoding="utf-8")
    return folder


def test_read_architectures_from_config(tmp_path):
    folder = write_config(
        tmp_path / "m",
        json.dumps({"architectures": ["Qwen3VLForConditionalGeneration"]}),
    )
    assert READ_ARCHITECTURES(folder) == QWEN3_VL


@pytest.mark.parametrize(
    "content", ["not json", "[1]", json.dumps({"architectures": "x"}), "{}"]
)
def test_read_architectures_bad_config_is_empty(tmp_path, content):
    folder = write_config(tmp_path / "m", content)
    assert READ_ARCHITECTURES(folder) == ()


def test_read_architectures_missing_folder_is_empty(tmp_path):
    assert READ_ARCHITECTURES(tmp_path / "gone") == ()
    assert READ_ARCHITECTURES(None) == ()
