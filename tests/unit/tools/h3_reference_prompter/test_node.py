import pytest
import torch

import kikotools
from kikotools.tools.h3_reference_prompter import node as node_module
from kikotools.tools.h3_reference_prompter.instructions import (
    describe_system,
    describe_user,
    retry_user,
    writer_user,
)
from kikotools.tools.h3_reference_prompter.node import H3ReferencePrompterNode
from kikotools.tools.prompt_enhancer.models import ModelEntry

DRAFT = "<Picture 1> wears <Picture 2> in <Picture 3>."
BODY = "A long prompt body."
FULL = DRAFT + "\n\n" + BODY


def entry(kind="hf", name="hf: demo"):
    return ModelEntry(
        name=name, kind=kind, path=None, vision=True, mmproj=None, clip_type=None
    )


class Harness:
    def __init__(self, monkeypatch, writes=None, kind="hf"):
        self.calls = []
        self.batches = []
        self.events = []
        self.writes = list(writes or [BODY])
        self.entry = entry(kind)
        self.clip_loads = 0
        node_module._NOTES_CACHE.clear()
        monkeypatch.setattr(node_module, "_generate", self.generate)
        monkeypatch.setattr(node_module, "_generate_batch", self.generate_batch)
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

    def generate_batch(self, entry, requests, seed, temp, max_length):
        kind = "describe" if requests[0][2] is not None else "write"
        self.batches.append((kind, len(requests)))
        return [
            node_module._generate(
                entry, None, system, prompt, image, seed, temp, max_length
            )
            for system, prompt, image in requests
        ]

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
    # One batched call samples with one seed: every hf item uses the base seed.
    assert [c["seed"] for c in h.writers] == [10, 10, 10]
    assert h.events.count("unload") == 1
    assert len(out["result"][0]) == 3


def three_poses(h, seed=10, writes=None):
    if writes is not None:
        h.writes = list(writes)
    return run(
        prompt=[DRAFT] * 3,
        images={
            "image_1": [img(1)],
            "image_2": [img(2)],
            "image_3": [img(3), img(4), img(5)],
        },
        seed=seed,
    )


def test_hf_three_poses_describe_in_one_batch_and_write_in_another(monkeypatch):
    h = Harness(monkeypatch)
    out = three_poses(h)
    assert h.batches == [("describe", 5), ("write", 3)]
    assert out["result"][0] == [FULL] * 3
    notes = out["result"][1]
    assert len(set(notes)) == 1 and notes[0].count("<Picture") == 3


def test_hf_cached_pictures_skip_the_describe_batch(monkeypatch):
    h = Harness(monkeypatch)
    three_poses(h)
    h.batches.clear()
    three_poses(h)
    assert h.batches == [("write", 3)]


def test_hf_retries_only_failing_items_in_one_batch(monkeypatch):
    h = Harness(monkeypatch)
    bad = "Body with <Picture 4>."
    out = three_poses(h, writes=[BODY, bad, BODY, BODY])
    assert h.batches == [("describe", 5), ("write", 3), ("write", 1)]
    retry = h.writers[-1]
    assert "Your previous prompt:\n" + bad in retry["prompt"]
    assert retry["seed"] == 10
    assert out["result"][0] == [FULL] * 3


def test_hf_still_failing_items_raise_naming_the_first_failing_item(monkeypatch):
    h = Harness(monkeypatch)
    four, five = "Body <Picture 4>.", "Body <Picture 5>."
    with pytest.raises(ValueError, match="did not keep") as caught:
        three_poses(h, writes=[BODY, four, five, four, five])
    assert h.batches[-2:] == [("write", 3), ("write", 2)]
    assert "unexpected <Picture 4>" in str(caught.value)
    assert "<Picture 5>" not in str(caught.value)
    assert "repair" in h.events


def test_shared_picture_is_described_with_the_first_items_draft(monkeypatch):
    h = Harness(monkeypatch)
    drafts = ["<Picture 1> first.", "<Picture 1> second."]
    run(prompt=drafts, images={"image_1": [img(1)]})
    assert h.batches == [("describe", 1), ("write", 2)]
    assert h.describes[0]["prompt"] == describe_user("character", drafts[0])


@pytest.mark.parametrize("kind", ["gguf", "native"])
def test_gguf_and_native_loop_with_per_item_seeds(monkeypatch, kind):
    h = Harness(monkeypatch, kind=kind)
    h.entry = entry(kind, f"{kind}: m")
    run(
        prompt=[DRAFT] * 3,
        model=[f"{kind}: m"],
        images={
            "image_1": [img(1)],
            "image_2": [img(2)],
            "image_3": [img(3), img(4), img(5)],
        },
        seed=10,
    )
    assert h.batches == []
    assert len(h.describes) == 5
    assert [c["seed"] for c in h.writers] == [10, 11, 12]


def test_gguf_retries_each_item_before_writing_the_next(monkeypatch):
    h = Harness(monkeypatch, kind="gguf")
    h.entry = entry("gguf", "gguf: m")
    h.writes = ["Body <Picture 4>.", BODY, BODY]
    run(prompt=[DRAFT] * 2, model=["gguf: m"], seed=3)
    assert [c["seed"] for c in h.writers] == [3, 3, 4]
    assert "Your previous prompt:" in h.writers[1]["prompt"]


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
    bad = "A body with a stray <Picture 4> tag."
    h = Harness(monkeypatch, writes=[bad, bad])
    with pytest.raises(ValueError, match=r"unexpected <Picture 4>"):
        run(images={"image_1": [img(1)]}, seed=7)
    first, second = h.writers
    assert second["seed"] == first["seed"] == 7
    assert second["prompt"].startswith(first["prompt"])
    assert "Your previous prompt:\n" + bad in second["prompt"]
    assert second["prompt"].endswith(retry_user(([], [4])))
    assert "repair" in h.events


def test_tag_retry_succeeds(monkeypatch):
    h = Harness(monkeypatch, writes=["Body with <Picture 4>.", BODY])
    out = run()
    assert out["result"][0] == [FULL]
    assert len(h.writers) == 2
    assert "repair" not in h.events


def test_extra_tag_error_names_extra(monkeypatch):
    h = Harness(monkeypatch, writes=["Body <Picture 2>"] * 2)
    with pytest.raises(ValueError, match=r"unexpected <Picture 2>"):
        run(prompt=["<Picture 1> alone"])
    assert len(h.writers) == 2


def test_missing_tag_error_names_missing(monkeypatch):
    # Only reachable if the program-written reference ever lost a tag.
    monkeypatch.setattr(
        node_module, "split_reference_sentences", lambda draft: ("", draft)
    )
    h = Harness(monkeypatch, writes=["Body only."] * 2)
    with pytest.raises(ValueError, match=r"missing <Picture 1>"):
        run(prompt=["<Picture 1> alone"])
    assert len(h.writers) == 2


def test_output_starts_with_the_drafts_reference_sentences_verbatim(monkeypatch):
    draft = (
        "<Picture 1> is the character. Draw her in <Picture 3>; keep it calm. "
        "Photorealistic photograph. Full body."
    )
    h = Harness(monkeypatch, writes=["She stands."])
    out = run(prompt=[draft])
    reference = "<Picture 1> is the character. Draw her in <Picture 3>; keep it calm."
    assert out["result"][0] == [reference + "\n\nShe stands."]
    sent = h.writers[0]["prompt"]
    assert "Photorealistic photograph. Full body." in sent
    assert "already written; do not repeat" in sent


def test_model_output_repeating_a_tag_sentence_is_accepted(monkeypatch):
    repeat = "<Picture 1> wears <Picture 2> in <Picture 3>. More text."
    h = Harness(monkeypatch, writes=[repeat])
    out = run()
    assert out["result"][0] == [DRAFT + "\n\n" + repeat]
    assert len(h.writers) == 1


def test_notes_are_deduplicated(monkeypatch):
    h = Harness(monkeypatch)
    twice = "Young and bright. Young and bright. Dark hair."
    monkeypatch.setattr(h, "generate", lambda *a: twice if a[4] is not None else BODY)
    monkeypatch.setattr(node_module, "_generate", h.generate)
    out = run(images={"image_1": [img(1)]})
    assert out["result"][1] == ["<Picture 1> (character): Young and bright. Dark hair."]
    (cached,) = node_module._NOTES_CACHE.values()
    assert cached == "Young and bright. Dark hair."


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
    h = Harness(monkeypatch, writes=["Body <Picture 3>.", "Body."])
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
    h = Harness(monkeypatch, writes=["nope <Picture 4>"] * 2)
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
        "",
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


def test_real_batch_dispatch_uses_generate_hf_batch(monkeypatch):
    seen = []
    monkeypatch.setattr(
        node_module, "generate_hf_batch", lambda *a: seen.append(a) or ["h"]
    )
    requests = [("s", "p", None)]
    assert node_module._generate_batch(entry("hf"), requests, 1, 0.7, 99) == ["h"]
    assert seen == [(entry("hf"), requests, 1, 0.7, 99)]


def test_empty_describe_result_raises_naming_slot_and_model_and_is_not_cached(
    monkeypatch,
):
    h = Harness(monkeypatch)
    monkeypatch.setattr(h, "generate", lambda *a: "   ")
    monkeypatch.setattr(node_module, "_generate", h.generate)
    with pytest.raises(ValueError) as caught:
        run(images={"image_2": [img(2)]})
    assert "image_2" in str(caught.value) and "hf: demo" in str(caught.value)
    assert node_module._NOTES_CACHE == {}
    assert "repair" in h.events


def test_empty_prompt_list_raises_no_prompt(monkeypatch):
    h = Harness(monkeypatch)
    with pytest.raises(ValueError, match="no prompt"):
        H3ReferencePrompterNode().write(
            prompt=[],
            model=["hf: demo"],
            role_1=["character"],
            role_2=["outfit"],
            role_3=["pose"],
            seed=[1],
        )
    assert h.events == [] and h.calls == []


def test_repair_failure_is_logged_and_original_error_is_raised(monkeypatch, caplog):
    h = Harness(monkeypatch, writes=["nope <Picture 4>"] * 2)

    def broken_repair():
        raise OSError("repair broke")

    monkeypatch.setattr(node_module, "repair_loaded_models", broken_repair)
    with caplog.at_level("ERROR"):
        with pytest.raises(ValueError, match="did not keep the picture tags"):
            run()
    assert "repair broke" in caplog.text
    assert "free_hf" in h.events


def test_native_run_unloads_again_at_the_end_unless_kept(monkeypatch):
    h = Harness(monkeypatch, kind="native")
    h.entry = entry("native", "native: clip")
    run(model=["native: clip"], images={"image_1": [img(1)]})
    assert h.events.count("unload") == 2
    assert h.events[-1] == "unload"
    h.events.clear()
    run(model=["native: clip"], images={"image_1": [img(1)]}, keep_loaded=[True])
    assert h.events.count("unload") == 1


def test_non_native_run_unloads_once(monkeypatch):
    h = Harness(monkeypatch)
    run()
    assert h.events.count("unload") == 1


def test_native_failure_does_not_unload_again_after_repair(monkeypatch):
    h = Harness(monkeypatch, kind="native", writes=["nope <Picture 4>"] * 2)
    h.entry = entry("native", "native: clip")
    with pytest.raises(ValueError):
        run(model=["native: clip"])
    assert h.events.count("unload") == 1
    assert h.events[-1] != "unload"


def test_failed_unload_does_not_trigger_repair(monkeypatch):
    h = Harness(monkeypatch)

    def broken_unload():
        raise RuntimeError("unload broke")

    monkeypatch.setattr(node_module, "unload_models_safely", broken_unload)
    with pytest.raises(RuntimeError, match="unload broke"):
        run()
    assert "repair" not in h.events


def test_native_errors_pass_through_unwrapped_and_repair(monkeypatch):
    h = Harness(monkeypatch, kind="native")
    h.entry = entry("native", "native: clip")

    def boom(*args):
        raise RuntimeError("clip broke")

    monkeypatch.setattr(node_module, "_generate", boom)
    with pytest.raises(RuntimeError, match="clip broke"):
        run(model=["native: clip"], images={"image_1": [img(1)]})
    assert "repair" in h.events
