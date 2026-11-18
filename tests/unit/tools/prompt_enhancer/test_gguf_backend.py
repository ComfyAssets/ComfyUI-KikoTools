import base64
import sys
import types
from pathlib import Path

import pytest
import torch

from kikotools.tools.prompt_enhancer import gguf_backend
from kikotools.tools.prompt_enhancer.gguf_backend import free_gguf, generate_gguf
from kikotools.tools.prompt_enhancer.models import ModelEntry

SYSTEM = "You rewrite prompts for an image model."
TEMPLATE = "{{ messages }}"
TEXT = ModelEntry("gguf: q.gguf", "gguf", Path("/m/q.gguf"), False, None, None)
VISION = ModelEntry(
    "gguf: vl.gguf", "gguf", Path("/m/vl.gguf"), True, Path("/m/mmproj.gguf"), None
)


def completion(content="A cat on a mat.", finish_reason="stop"):
    return {
        "choices": [{"message": {"content": content}, "finish_reason": finish_reason}]
    }


class FakeChat:
    """Records handler calls; stands in for both text and vision chat handlers."""

    result = completion()
    fail = False

    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if FakeChat.fail:
            raise RuntimeError("boom")
        return FakeChat.result


class FakeFormatter:
    instances = []

    def __init__(self, template, eos_token, bos_token, stop_token_ids=None):
        self.template = template
        self.eos_token = eos_token
        self.bos_token = bos_token
        self.stop_token_ids = stop_token_ids
        self.chat = FakeChat()
        FakeFormatter.instances.append(self)

    def to_chat_handler(self):
        return self.chat


class FakeLlama:
    instances = []
    template = TEMPLATE

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.chat_handler = kwargs["chat_handler"]
        self.metadata = (
            {}
            if FakeLlama.template is None
            else {"tokenizer.chat_template": FakeLlama.template}
        )
        self.closed = False
        FakeLlama.instances.append(self)

    def token_eos(self):
        return 2

    def token_bos(self):
        return 1

    def detokenize(self, tokens, prev_tokens=None, special=False):
        assert special
        return {2: b"<|im_end|>", 1: b"\xff<bos>"}[tokens[0]]

    def close(self):
        self.closed = True


class FakeHandler(FakeChat):
    def __init__(self, clip_model_path, verbose=True):
        super().__init__()
        self.clip_model_path = clip_model_path
        self.verbose = verbose


class FakeMTMD(FakeHandler):
    pass


@pytest.fixture
def fakes(monkeypatch):
    FakeLlama.instances = []
    FakeLlama.template = TEMPLATE
    FakeFormatter.instances = []
    FakeChat.result = completion()
    FakeChat.fail = False
    events = []
    llama_cpp = types.ModuleType("llama_cpp")
    llama_cpp.Llama = FakeLlama
    chat_format = types.ModuleType("llama_cpp.llama_chat_format")
    chat_format.Qwen25VLChatHandler = FakeHandler
    chat_format.Jinja2ChatFormatter = FakeFormatter
    llama_cpp.llama_chat_format = chat_format
    mm = types.ModuleType("comfy.model_management")
    mm.unload_all_models = lambda: events.append("unload")
    mm.soft_empty_cache = lambda: events.append("empty")
    comfy = types.ModuleType("comfy")
    comfy.model_management = mm
    monkeypatch.setitem(sys.modules, "llama_cpp", llama_cpp)
    monkeypatch.setitem(sys.modules, "llama_cpp.llama_chat_format", chat_format)
    monkeypatch.setitem(sys.modules, "comfy", comfy)
    monkeypatch.setitem(sys.modules, "comfy.model_management", mm)
    monkeypatch.setattr(gguf_backend, "_loaded", None)
    yield events
    gguf_backend._loaded = None


def run(entry=TEXT, image=None, thinking=False, keep_loaded=False):
    return generate_gguf(
        entry, SYSTEM, "a cat", image, 7, 0.7, 1024, thinking, keep_loaded
    )


def text_calls():
    return FakeFormatter.instances[0].chat.calls


def test_missing_llama_cpp_raises(monkeypatch):
    monkeypatch.setitem(sys.modules, "llama_cpp", None)
    with pytest.raises(
        ValueError,
        match="^llama-cpp-python is not installed; install it to use GGUF models$",
    ):
        run()


def test_text_run_messages_and_params(fakes):
    assert run() == "A cat on a mat."
    llm = FakeLlama.instances[0]
    assert llm.kwargs["model_path"] == "/m/q.gguf"
    assert llm.kwargs["n_ctx"] == 8192
    assert llm.kwargs["n_gpu_layers"] == -1
    assert llm.kwargs["flash_attn"] == torch.cuda.is_available()
    assert llm.kwargs["seed"] == 7
    assert llm.kwargs["chat_handler"] is None
    formatter = FakeFormatter.instances[0]
    assert formatter.template == TEMPLATE
    assert formatter.eos_token == "<|im_end|>"
    assert formatter.bos_token == "<bos>"
    assert formatter.stop_token_ids == [2]
    (call,) = text_calls()
    assert call["llama"] is llm
    assert call["messages"] == [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "a cat"},
    ]
    assert call["enable_thinking"] is False
    assert call["max_tokens"] == 1024
    assert call["seed"] == 7
    assert call["temperature"] == 0.7
    assert (call["top_k"], call["top_p"], call["min_p"], call["repeat_penalty"]) == (
        64,
        0.95,
        0.05,
        1.05,
    )


def test_thinking_reaches_template(fakes):
    FakeChat.result = completion("<think>x</think>A cat.")
    run(thinking=True)
    (call,) = text_calls()
    assert call["enable_thinking"] is True
    assert call["messages"][1]["content"] == "a cat"


def test_thinking_used_up_max_length_raises(fakes):
    FakeChat.result = completion("<think>still going", finish_reason="length")
    with pytest.raises(
        ValueError,
        match="^thinking used up max_length; raise max_length or turn thinking off$",
    ):
        run(thinking=True)


def test_length_cut_without_thinking_returns_text(fakes):
    FakeChat.result = completion("A cat on", finish_reason="length")
    assert run() == "A cat on"


def test_missing_chat_template_raises(fakes):
    FakeLlama.template = None
    with pytest.raises(ValueError, match="^gguf: q.gguf has no chat template$"):
        run()


def test_image_run_uses_handler_and_data_uri(fakes):
    image = torch.zeros(2, 4, 4, 3)
    image[0, :, :, 0] = 1.0
    run(entry=VISION, image=image)
    llm = FakeLlama.instances[0]
    handler = llm.kwargs["chat_handler"]
    assert type(handler) is FakeHandler
    assert handler.clip_model_path == "/m/mmproj.gguf"
    assert handler.verbose is False
    assert FakeFormatter.instances == []
    (call,) = handler.calls
    assert call["llama"] is llm
    assert call["enable_thinking"] is False
    image_part, text_part = call["messages"][1]["content"]
    assert text_part == {"type": "text", "text": "a cat"}
    url = image_part["image_url"]["url"]
    assert image_part["type"] == "image_url"
    assert url.startswith("data:image/png;base64,")
    png = base64.b64decode(url.split(",", 1)[1])
    assert png.startswith(b"\x89PNG")


def test_image_run_prefers_mtmd_handler(fakes):
    sys.modules["llama_cpp.llama_chat_format"].MTMDChatHandler = FakeMTMD
    run(entry=VISION, image=torch.zeros(1, 4, 4, 3))
    assert type(FakeLlama.instances[0].kwargs["chat_handler"]) is FakeMTMD


def test_no_vision_handler_raises(fakes):
    del sys.modules["llama_cpp.llama_chat_format"].Qwen25VLChatHandler
    with pytest.raises(
        ValueError,
        match="^llama-cpp-python has no vision chat handler; update llama-cpp-python$",
    ):
        run(entry=VISION, image=torch.zeros(1, 4, 4, 3))


def test_unloads_comfy_models_first(fakes):
    run()
    assert fakes == ["unload", "empty"]


def test_keep_loaded_reuses_model(fakes):
    run(keep_loaded=True)
    run(keep_loaded=True)
    assert len(FakeLlama.instances) == 1
    assert sum(len(f.chat.calls) for f in FakeFormatter.instances) == 2
    assert not FakeLlama.instances[0].closed
    free_gguf()
    assert FakeLlama.instances[0].closed
    assert gguf_backend._loaded is None


def test_keep_loaded_false_frees_after_run(fakes):
    run()
    assert FakeLlama.instances[0].closed
    assert gguf_backend._loaded is None


def test_gguf_freed_after_error(fakes):
    FakeChat.fail = True
    with pytest.raises(RuntimeError, match="boom"):
        run()
    assert FakeLlama.instances[0].closed
    assert gguf_backend._loaded is None
