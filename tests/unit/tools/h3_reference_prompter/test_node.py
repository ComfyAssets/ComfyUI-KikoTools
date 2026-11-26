import pytest
import torch

import kikotools
from kikotools.tools.h3_reference_prompter import node as node_module
from kikotools.tools.h3_reference_prompter.instructions import (
    describe_system,
    retry_user,
    writer_user,
)
from kikotools.tools.h3_reference_prompter.node import H3ReferencePrompterNode
from kikotools.tools.prompt_enhancer.models import ModelEntry

DRAFT = "<Picture 1> wears <Picture 2> in <Picture 3>."
FULL = "<Picture 1> wears <Picture 2> in <Picture 3>. Long text."


def entry(kind="hf", name="hf: demo"):
    return ModelEntry(
        name=name, kind=kind, path=None, vision=True, mmproj=None, clip_type=None
    )


class Harness:
    def __init__(self, monkeypatch, writes=None, kind="hf"):
        self.calls = []
        self.events = []
        self.writes = list(writes or [FULL])
        self.entry = entry(kind)
        self.clip_loads = 0
        node_module._NOTES_CACHE.clear()
        monkeypatch.setattr(node_module, "_generate", self.generate)
        monkeypatch.setattr(node_module, "find_prompter_model", self.find)
        monkeypatch.setattr(
            node_module, "unload_models_safely", lambda: self.events.append("unload")
        )
        monkeypatch.setattr(
            node_module, "repair_loaded_models", lambda: self.events.append("repair")
        )
        monkeypatch.setattr(
            node_module, "free_hf", lambda: self.events.append("free_hf")
        )
        monkeypatch.setattr(
            node_module, "free_gguf", lambda: self.events.append("free_gguf")
        )
        monkeypatch.setattr(node_module, "load_native", self.load_native)

    def find(self, name):
        return self.entry if name == self.entry.name else None

    def load_native(self, entry):
        self.clip_loads += 1
        return "clip"

    def generate(self, entry, clip, system, prompt, image, seed, temp, max_length):
        self.calls.append(
            dict(system=system, prompt=prompt, image=image, seed=seed, clip=clip)
        )
        if image is not None:
            return "notes " + system[:10]
        return self.writes.pop(0) if len(self.writes) > 1 else self.writes[0]

    @property
    def describes(self):
        return [c for c in self.calls if c["image"] is not None]

    @property
    def writers(self):
        return [c for c in self.calls if c["image"] is None]


def img(value=0.0, batch=1):
    return torch.full((batch, 4, 4, 3), value)


def run(prompt=None, images=None, seed=5, **extra):
    kwargs = dict(
        prompt=prompt or [DRAFT],
        model=["hf: demo"],
        role_1=["character"],
        role_2=["outfit"],
        role_3=["pose"],
        seed=[seed],
    )
    kwargs.update(images if images is not None else {})
    kwargs.update(extra)
    return H3ReferencePrompterNode().write(**kwargs)


def test_input_types_and_metadata(monkeypatch):
    monkeypatch.setattr(node_module, "prompter_model_names", lambda: ["hf: a"])
    types = H3ReferencePrompterNode.INPUT_TYPES()
    required, optional = types["required"], types["optional"]
    assert required["prompt"][1]["multiline"] is True
    assert required["model"][0] == ["hf: a"]
    assert [required[f"role_{n}"][1]["default"] for n in (1, 2, 3)] == [
        "character",
        "outfit",
        "pose",
    ]
    assert required["role_1"][0] == ["character", "outfit", "pose", "other"]
    assert required["seed"][1]["control_after_generate"] is True
    assert all(optional[f"image_{n}"][0] == "IMAGE" for n in (1, 2, 3))
    assert optional["temperature"][1] == {
        "default": 0.7,
        "min": 0.01,
        "max": 2.0,
        "step": 0.01,
        "advanced": True,
    }
    assert optional["describe_tokens"][1]["default"] == 512
    assert optional["write_tokens"][1]["default"] == 1536
    assert optional["keep_loaded"][1]["default"] is False
    node = H3ReferencePrompterNode
    assert node.INPUT_IS_LIST is True
    assert node.RETURN_TYPES == ("STRING", "STRING")
    assert node.RETURN_NAMES == ("prompt", "notes")
    assert node.OUTPUT_IS_LIST == (True, True)
    assert node.FUNCTION == "write"
    assert node.CATEGORY == "🫶 ComfyAssets/🧠 Prompts"
    assert node.VALIDATE_INPUTS("anything") is True
    assert kikotools.NODE_CLASS_MAPPINGS["KikoH3ReferencePrompter"] is node
    assert (
        kikotools.NODE_DISPLAY_NAME_MAPPINGS["KikoH3ReferencePrompter"]
        == "H3 Reference Prompter"
    )


def test_one_item_two_passes(monkeypatch):
    h = Harness(monkeypatch)
    out = run(images={"image_1": [img(1)], "image_2": [img(2)], "image_3": [img(3)]})
    assert [c["system"] for c in h.describes] == [
        describe_system("character"),
        describe_system("outfit"),
        describe_system("pose"),
    ]
    assert len(h.writers) == 1
    assert out["result"][0] == [FULL]
    notes = out["result"][1][0].split("\n\n")
    assert [n.split(":")[0] for n in notes] == [
        "<Picture 1> (character)",
        "<Picture 2> (outfit)",
        "<Picture 3> (pose)",
    ]
    assert out["ui"] == {"h3_prompts": [FULL], "h3_notes": out["result"][1]}


def test_one_per_pose_caches_character_and_outfit(monkeypatch):
    h = Harness(monkeypatch)
    poses = [img(3), img(4), img(5)]
    out = run(
        prompt=[DRAFT] * 3,
        images={"image_1": [img(1)], "image_2": [img(2)], "image_3": poses},
        seed=10,
    )
    assert len(h.describes) == 5
    assert len(h.writers) == 3
    assert [c["seed"] for c in h.writers] == [10, 11, 12]
    assert h.events.count("unload") == 1
    assert len(out["result"][0]) == 3


def test_plain_draft_without_tags(monkeypatch):
    h = Harness(monkeypatch, writes=["A woman stands."])
    out = run(prompt=["a woman standing"], images={"image_1": [img(1)]})
    assert out["result"][0] == ["A woman stands."]
    assert len(h.writers) == 1


def test_unconnected_images_give_empty_notes(monkeypatch):
    Harness(monkeypatch, writes=["A woman stands."])
    out = run(prompt=["a woman standing"])
    assert out["result"][1] == [""]


def test_tag_retry_then_error(monkeypatch):
    bad = "<Picture 1> wears <Picture 3>."
    h = Harness(monkeypatch, writes=[bad, bad])
    with pytest.raises(ValueError, match=r"<Picture 2>"):
        run(images={"image_1": [img(1)]}, seed=7)
    first, second = h.writers
    assert second["seed"] == first["seed"] == 7
    assert second["prompt"].startswith(first["prompt"])
    assert "Your previous prompt:\n" + bad in second["prompt"]
    assert second["prompt"].endswith(retry_user(([2], [])))
    assert "repair" in h.events


def test_tag_retry_succeeds(monkeypatch):
    h = Harness(monkeypatch, writes=["<Picture 1> only.", FULL])
    out = run()
    assert out["result"][0] == [FULL]
    assert "repair" not in h.events


def test_extra_tag_error_names_extra(monkeypatch):
    h = Harness(monkeypatch, writes=["<Picture 1> <Picture 2>"] * 2)
    with pytest.raises(ValueError, match=r"unexpected <Picture 2>"):
        run(prompt=["<Picture 1> alone"])
    assert len(h.writers) == 2


def test_batch_tensor_in_a_slot_is_rejected(monkeypatch):
    h = Harness(monkeypatch)
    with pytest.raises(ValueError, match="image_3"):
        run(images={"image_3": [img(3, batch=2)]})
    assert "unload" not in h.events
    assert h.calls == []


def test_missing_model_validates_then_fails_clearly(monkeypatch):
    h = Harness(monkeypatch)
    assert H3ReferencePrompterNode.VALIDATE_INPUTS("hf: gone") is True
    with pytest.raises(ValueError) as caught:
        run(model=["hf: gone"])
    assert "hf: gone" in str(caught.value)
    assert "models/LLM" in str(caught.value)
    assert "unload" not in h.events


def test_unmentioned_slot_is_context_only(monkeypatch):
    draft = "<Picture 1> wears <Picture 2>."
    h = Harness(monkeypatch, writes=["<Picture 1> <Picture 2> <Picture 3>.", draft])
    run(
        prompt=[draft],
        images={"image_1": [img(1)], "image_2": [img(2)], "image_3": [img(3)]},
    )
    assert "do not write its tag" in h.writers[0]["prompt"]
    assert len(h.writers) == 2


def test_backend_freed_unless_keep_loaded(monkeypatch):
    h = Harness(monkeypatch)
    run()
    assert "free_hf" in h.events and "free_gguf" in h.events
    h.events.clear()
    run(keep_loaded=[True])
    assert "free_hf" not in h.events and "free_gguf" not in h.events


def test_backend_freed_after_failure(monkeypatch):
    h = Harness(monkeypatch, writes=["nope", "nope"])
    with pytest.raises(ValueError):
        run()
    assert h.events.index("repair") < h.events.index("free_hf")


def test_gguf_failure_names_model_and_suggests_folder(monkeypatch):
    h = Harness(monkeypatch, kind="gguf")
    h.entry = entry("gguf", "gguf: gemma")

    def boom(*args):
        raise RuntimeError("mtmd exploded")

    monkeypatch.setattr(node_module, "_generate", boom)
    with pytest.raises(ValueError) as caught:
        run(model=["gguf: gemma"], images={"image_1": [img(1)]})
    message = str(caught.value)
    assert "gguf: gemma" in message and "models/LLM" in message
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert "repair" in h.events


def test_non_gguf_errors_pass_through_and_repair(monkeypatch):
    h = Harness(monkeypatch)

    def boom(*args):
        raise RuntimeError("oom")

    monkeypatch.setattr(node_module, "_generate", boom)
    with pytest.raises(RuntimeError, match="oom"):
        run(images={"image_1": [img(1)]})
    assert "repair" in h.events


def test_native_clip_loaded_once_and_dispatch(monkeypatch):
    h = Harness(monkeypatch, kind="native")
    h.entry = entry("native", "native: clip")
    run(
        model=["native: clip"],
        images={"image_1": [img(1)], "image_2": [img(2)]},
    )
    assert h.clip_loads == 1
    assert {c["clip"] for c in h.calls} == {"clip"}


def test_hf_does_not_load_clip(monkeypatch):
    h = Harness(monkeypatch)
    run(images={"image_1": [img(1)]})
    assert h.clip_loads == 0


def test_writer_message_uses_notes(monkeypatch):
    h = Harness(monkeypatch)
    run(images={"image_1": [img(1)]})
    expected = writer_user(
        DRAFT,
        [
            (
                1,
                "character",
                h.describes[0] and "notes " + h.describes[0]["system"][:10],
            ),
            (2, "outfit", None),
            (3, "pose", None),
        ],
    )
    assert h.writers[0]["prompt"] == expected


def test_real_dispatch_routes_by_kind(monkeypatch):
    seen = []
    monkeypatch.setattr(
        node_module, "generate_hf", lambda *a: seen.append(("hf", a)) or "h"
    )
    monkeypatch.setattr(
        node_module, "generate_gguf", lambda *a: seen.append(("gguf", a)) or "g"
    )
    monkeypatch.setattr(
        node_module, "generate_native", lambda *a: seen.append(("native", a)) or "n"
    )
    args = ("c", "s", "p", None, 1, 0.7, 99)
    assert node_module._generate(entry("hf"), *args) == "h"
    assert node_module._generate(entry("gguf"), *args) == "g"
    assert node_module._generate(entry("native"), *args) == "n"
    assert seen[1][1][-2:] == (False, True)
    assert seen[2][1][0] == "c" and seen[2][1][-1] is False
