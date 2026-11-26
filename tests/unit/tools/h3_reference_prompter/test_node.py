import pytest
import torch

import kikotools
from kikotools.tools.h3_reference_prompter import node as node_module
from kikotools.tools.h3_reference_prompter.instructions import (
    describe_system,
    describe_user,
    adult_block,
    nude_block,
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
        self.describe_reply = None
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
            if self.describe_reply is not None:
                return self.describe_reply(system)
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
    assert [required[f"role_{n}"][1]["default"] for n in (1, 2, 3)] == ["auto"] * 3
    assert required["role_1"][0] == ["auto", "character", "outfit", "pose", "other"]
    assert "auto" in required["role_2"][1]["tooltip"]
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
    assert out["result"][0] == ["a woman standing\n\nA woman stands."]
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
    # Only reachable if the program-written lead ever lost a tag.
    monkeypatch.setattr(node_module, "draft_lead", lambda draft: "")
    h = Harness(monkeypatch, writes=["Body only."] * 2)
    with pytest.raises(ValueError, match=r"missing <Picture 1>"):
        run(prompt=["<Picture 1> alone"])
    assert len(h.writers) == 2


def test_output_starts_with_the_whole_draft_verbatim(monkeypatch):
    draft = (
        "<Picture 1> is the character. Draw her in <Picture 3>; keep it calm. "
        "Side view, sitting. . Photorealistic photograph."
    )
    h = Harness(monkeypatch, writes=["She sits. Side view, sitting. Calm."])
    out = run(prompt=[draft])
    lead = (
        "<Picture 1> is the character. Draw her in <Picture 3>; keep it calm. "
        "Side view, sitting. Photorealistic photograph."
    )
    assert out["result"][0] == [lead + "\n\nShe sits. Calm."]
    sent = h.writers[0]["prompt"]
    assert lead in sent
    assert "word for word" in sent


def test_model_output_echoing_a_tag_sentence_drops_the_echo(monkeypatch):
    repeat = "<Picture 1> wears <Picture 2> in <Picture 3>. More text."
    h = Harness(monkeypatch, writes=[repeat])
    out = run()
    assert out["result"][0] == [DRAFT + "\n\nMore text."]
    assert len(h.writers) == 1


def test_echo_is_matched_ignoring_case_and_spacing(monkeypatch):
    echo = "<Picture 1>  WEARS <Picture 2> in  <Picture 3>.\nShe stands."
    Harness(monkeypatch, writes=[echo])
    out = run()
    assert out["result"][0] == [DRAFT + "\n\nShe stands."]


def test_blank_written_part_is_retried_once(monkeypatch):
    h = Harness(monkeypatch, writes=["<think>still thinking", BODY])
    out = run()
    assert out["result"][0] == [FULL]
    assert len(h.writers) == 2
    retry = h.writers[1]["prompt"]
    assert retry.endswith(retry_user(([], []), blank=True))
    assert "Your previous prompt:" not in retry


def test_echo_only_reply_counts_as_blank(monkeypatch):
    h = Harness(monkeypatch, writes=[DRAFT, BODY])
    out = run()
    assert out["result"][0] == [FULL]
    assert len(h.writers) == 2


def test_still_blank_after_retry_raises_naming_model_and_write_tokens(monkeypatch):
    h = Harness(monkeypatch, writes=["   "])
    with pytest.raises(ValueError) as caught:
        run(prompt=["a woman standing"])
    message = str(caught.value)
    assert "hf: demo" in message and "write_tokens" in message
    assert len(h.writers) == 2
    assert "repair" in h.events


@pytest.mark.parametrize("kind", ["gguf", "native"])
def test_blank_reply_is_retried_on_the_loop_path(monkeypatch, kind):
    h = Harness(monkeypatch, kind=kind, writes=["", BODY])
    h.entry = entry(kind, f"{kind}: m")
    out = run(model=[f"{kind}: m"])
    assert out["result"][0] == [FULL]
    assert len(h.writers) == 2


def test_hf_batch_retries_a_blank_item(monkeypatch):
    h = Harness(monkeypatch)
    out = three_poses(h, writes=[BODY, "<think>cut", BODY, BODY])
    assert h.batches == [("describe", 5), ("write", 3), ("write", 1)]
    assert out["result"][0] == [FULL] * 3


def test_hf_batch_still_blank_raises(monkeypatch):
    h = Harness(monkeypatch)
    with pytest.raises(ValueError, match="write_tokens"):
        three_poses(h, writes=[BODY, "", BODY, ""])


def test_combined_prompt_has_no_trailing_whitespace(monkeypatch):
    Harness(monkeypatch, writes=["End line.  \nEnd line."])
    out = run(prompt=["a woman standing"])
    assert out["result"][0] == ["a woman standing\n\nEnd line."]


def test_blank_drafts_without_pictures_raise_before_unload(monkeypatch):
    h = Harness(monkeypatch)
    with pytest.raises(ValueError) as caught:
        run(prompt=["  ", ""])
    assert str(caught.value) == (
        "nothing to write from: the draft is empty and no picture is connected"
    )
    assert h.events == [] and h.calls == []


def test_blank_draft_with_a_picture_still_runs(monkeypatch):
    h = Harness(monkeypatch, writes=["She stands."])
    out = run(prompt=[" "], images={"image_1": [img(1)]})
    assert out["result"][0] == ["She stands."]
    assert len(h.describes) == 1


def test_notes_are_cleaned_like_results(monkeypatch):
    h = Harness(monkeypatch)
    raw = "<think>hmm</think>\nHere is the description:\nDark hair. Dark hair."
    monkeypatch.setattr(h, "generate", lambda *a: raw if a[4] is not None else BODY)
    monkeypatch.setattr(node_module, "_generate", h.generate)
    out = run(images={"image_1": [img(1)]})
    assert out["result"][1] == ["<Picture 1> (character): Dark hair."]


def test_unfinished_thinking_note_raises(monkeypatch):
    h = Harness(monkeypatch)
    monkeypatch.setattr(
        h, "generate", lambda *a: "<think>no end" if a[4] is not None else BODY
    )
    monkeypatch.setattr(node_module, "_generate", h.generate)
    with pytest.raises(ValueError, match="no description for image_1"):
        run(images={"image_1": [img(1)]})
    assert node_module._NOTES_CACHE == {}


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
    message = str(caught.value)
    assert "hf: gone" in message
    assert "models/LLM" in message
    assert "mmproj" in message and "vision model" in message
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
    assert "free_hf" not in h.events


@pytest.mark.parametrize(
    "kind, freed",
    [
        ("hf", ["free_gguf"]),
        ("gguf", ["free_hf"]),
        ("native", ["free_hf", "free_gguf"]),
    ],
)
def test_other_backends_are_freed_first_even_when_kept(monkeypatch, kind, freed):
    h = Harness(monkeypatch, kind=kind)
    h.entry = entry(kind, f"{kind}: m")
    run(model=[f"{kind}: m"], keep_loaded=[True])
    before_unload = h.events[: h.events.index("unload")]
    assert before_unload == freed
    assert h.events.count("free_hf") + h.events.count("free_gguf") == len(freed)


def test_keep_loaded_tooltip_warns_about_memory_management(monkeypatch):
    monkeypatch.setattr(node_module, "prompter_model_names", lambda: ["hf: a"])
    tooltip = H3ReferencePrompterNode.INPUT_TYPES()["optional"]["keep_loaded"][1][
        "tooltip"
    ]
    assert "hf:" in tooltip and "outside ComfyUI's memory management" in tooltip


def test_raising_describe_tokens_describes_again(monkeypatch):
    h = Harness(monkeypatch)
    run(images={"image_1": [img(1)]}, describe_tokens=[512])
    run(images={"image_1": [img(1)]}, describe_tokens=[512])
    assert len(h.describes) == 1
    run(images={"image_1": [img(1)]}, describe_tokens=[1024])
    assert len(h.describes) == 2


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


def test_multi_line_draft_keeps_all_its_lines(monkeypatch):
    draft = "<Picture 1> is her.\nSoft light.\n<Picture 2> is the coat."
    Harness(monkeypatch, writes=["<Picture 2> is the coat. She stands."])
    out = run(prompt=[draft])
    assert out["result"][0] == [
        "<Picture 1> is her.\nSoft light.\n<Picture 2> is the coat.\n\nShe stands."
    ]


NUDE_DRAFT = (
    "<Picture 1> is the character. <Picture 2> is the pose. Draw the character "
    "from <Picture 1> in the pose and camera angle of <Picture 2>; the mannequin "
    "is only a pose guide, not an appearance reference. The character's outfit: "
    "completely nude, wearing no clothing and no footwear. The pose: Front view, "
    "pose: Standing contrapposto, hand on hip (Standing). Photorealistic studio "
    "photograph, real person, natural skin texture, soft even lighting. Full "
    "body from head to toe, plain light grey studio background."
)
AUTO_ROLES = dict(role_1=["auto"], role_2=["auto"], role_3=["auto"])


def note_labels(out, index=0):
    return [n.split(":")[0] for n in out["result"][1][index].split("\n\n")]


def test_auto_roles_follow_the_drafts_picture_sentences(monkeypatch):
    h = nude_harness(monkeypatch)
    out = run(
        prompt=[NUDE_DRAFT],
        images={"image_1": [img(1)], "image_2": [img(2)]},
        **AUTO_ROLES,
    )
    assert [c["system"] for c in h.describes] == [
        describe_system("character"),
        describe_system("pose"),
    ]
    assert note_labels(out) == ["<Picture 1> (character)", "<Picture 2> (pose)"]
    assert "<Picture 2> (pose)" in h.writers[0]["prompt"]


def test_auto_roles_fall_back_to_slot_defaults(monkeypatch):
    h = Harness(monkeypatch)
    out = run(
        images={"image_1": [img(1)], "image_2": [img(2)], "image_3": [img(3)]},
        **AUTO_ROLES,
    )
    assert [c["system"] for c in h.describes] == [
        describe_system("character"),
        describe_system("outfit"),
        describe_system("pose"),
    ]
    assert note_labels(out) == [
        "<Picture 1> (character)",
        "<Picture 2> (outfit)",
        "<Picture 3> (pose)",
    ]


def test_explicit_role_wins_over_the_drafts_sentence(monkeypatch):
    h = nude_harness(monkeypatch)
    out = run(
        prompt=[NUDE_DRAFT],
        images={"image_1": [img(1)], "image_2": [img(2)]},
        role_1=["auto"],
        role_2=["other"],
        role_3=["auto"],
    )
    assert [c["system"] for c in h.describes] == [
        describe_system("character"),
        describe_system("other"),
    ]
    assert note_labels(out) == ["<Picture 1> (character)", "<Picture 2> (other)"]


def test_auto_roles_resolve_per_item_and_cache_by_resolved_role(monkeypatch):
    h = Harness(monkeypatch)
    three = "<Picture 1> is the character. <Picture 2> is the outfit."
    dressed = NUDE_DRAFT.replace("completely nude", "a red coat")
    out = run(
        prompt=[dressed, three],
        images={"image_2": [img(2)]},
        **AUTO_ROLES,
    )
    assert sorted(c["system"] for c in h.describes) == sorted(
        [describe_system("pose"), describe_system("outfit")]
    )
    assert note_labels(out, 0) == ["<Picture 2> (pose)"]
    assert note_labels(out, 1) == ["<Picture 2> (outfit)"]
    keys = {
        node_module.image_key(img(2), role, "hf: demo", 512)
        for role in ("pose", "outfit")
    }
    assert set(node_module._NOTES_CACHE) == keys


ADULT_NOTES = "A young woman with dark hair.\nEstimated age: 22 to 28 years."
NUDE_LEAD = node_module.draft_lead(NUDE_DRAFT)


def nude_harness(monkeypatch, character=ADULT_NOTES, writes=None, kind="hf"):
    h = Harness(monkeypatch, writes=writes, kind=kind)
    if kind != "hf":
        h.entry = entry(kind, f"{kind}: m")

    def reply(system):
        if system == describe_system("character"):
            return character
        return "Standing, weight on the left leg."

    h.describe_reply = reply
    return h


def run_nude(h, prompt=None, images=None):
    pictures = images or {"image_1": [img(1)], "image_2": [img(2)]}
    return run(
        prompt=prompt or [NUDE_DRAFT],
        model=[h.entry.name],
        images=pictures,
        **AUTO_ROLES,
    )


@pytest.mark.parametrize("kind", ["hf", "gguf"])
def test_clean_nude_run_adds_the_nude_block_and_passes(monkeypatch, kind):
    h = nude_harness(monkeypatch, kind=kind)
    out = run_nude(h)
    assert out["result"][0] == [NUDE_LEAD + "\n\n" + BODY]
    (writer,) = h.writers
    assert nude_block((22, 28)) in writer["prompt"]
    assert "Estimated age: 22 to 28 years." in out["result"][1][0]


@pytest.mark.parametrize("kind", ["hf", "gguf"])
def test_youth_word_in_the_written_part_is_retried_naming_it(monkeypatch, kind):
    bad = "She is an adult woman, not a teen, standing."
    h = nude_harness(monkeypatch, writes=[bad, BODY], kind=kind)
    out = run_nude(h)
    assert out["result"][0] == [NUDE_LEAD + "\n\n" + BODY]
    first, second = h.writers
    assert "Your previous prompt:\n" + bad in second["prompt"]
    assert second["prompt"].endswith(retry_user(([], []), banned="teen"))


@pytest.mark.parametrize("kind", ["hf", "gguf"])
def test_youth_word_after_the_retry_raises(monkeypatch, kind):
    h = nude_harness(monkeypatch, writes=["A girl stands."], kind=kind)
    with pytest.raises(ValueError, match="'girl'") as caught:
        run_nude(h)
    assert "after a retry" in str(caught.value)
    assert len(h.writers) == 2
    assert "repair" in h.events


def test_girl_is_allowed_outside_nude_mode(monkeypatch):
    h = Harness(monkeypatch, writes=["A girl stands in a red coat."])
    out = run(prompt=["a girl in a red coat"], images={"image_1": [img(1)]})
    assert out["result"][0] == ["a girl in a red coat\n\nA girl stands in a red coat."]
    assert len(h.writers) == 1
    assert nude_block((22, 28)) not in h.writers[0]["prompt"]


def test_nude_needs_a_character_picture(monkeypatch):
    h = nude_harness(monkeypatch)
    with pytest.raises(ValueError, match="No character picture is connected"):
        run_nude(h, images={"image_2": [img(2)]})
    assert h.writers == []
    assert "repair" in h.events


@pytest.mark.parametrize(
    "character, found",
    [
        ("A woman with dark hair.", "no age estimate for image_1"),
        ("A woman.\nEstimated age: 17 to 23 years.", "17 to 23 years for image_1"),
        ("A teenager.\nEstimated age: 20 to 25 years.", "'teenager'"),
    ],
)
def test_nude_refuses_before_writing(monkeypatch, character, found):
    h = nude_harness(monkeypatch, character=character)
    with pytest.raises(ValueError) as caught:
        run_nude(h)
    message = str(caught.value)
    assert "estimated age is 20 or older" in message and found in message
    assert h.writers == []
    assert "repair" in h.events and "free_hf" in h.events


def test_one_refused_item_fails_the_whole_run(monkeypatch):
    h = nude_harness(monkeypatch)
    young = "<Picture 1> is the character. <Picture 2> is the pose. A nude teen."
    with pytest.raises(ValueError, match="'teen'"):
        run_nude(h, prompt=[NUDE_DRAFT, young])
    assert h.writers == []


THREE = {"image_1": [img(1)], "image_2": [img(2)], "image_3": [img(3)]}


def test_outfit_picture_keeps_the_outfit_but_still_checks_the_age(monkeypatch):
    draft = DRAFT + " Nude lipstick."
    h = nude_harness(monkeypatch, writes=["An adult woman in a coat."])
    out = run(prompt=[draft], images=THREE, **AUTO_ROLES)
    assert out["result"][0] == [draft + "\n\nAn adult woman in a coat."]
    (writer,) = h.writers
    assert nude_block((22, 28)) not in writer["prompt"]
    assert adult_block((22, 28)) in writer["prompt"]


def test_nude_draft_with_an_outfit_picture_still_refuses_a_young_estimate(
    monkeypatch,
):
    h = nude_harness(monkeypatch, character="A woman.\nEstimated age: 16 to 19 years.")
    with pytest.raises(ValueError, match="16 to 19 years"):
        run(prompt=[DRAFT + " Completely nude."], images=THREE, **AUTO_ROLES)
    assert h.writers == []


def test_explicit_outfit_role_does_not_skip_the_age_check(monkeypatch):
    h = nude_harness(monkeypatch, character="A woman.\nEstimated age: 17 to 21 years.")
    with pytest.raises(ValueError, match="17 to 21 years"):
        run(
            prompt=[NUDE_DRAFT],
            model=[h.entry.name],
            images={"image_1": [img(1)], "image_2": [img(2)]},
        )
    assert h.writers == []


def test_batch_checks_youth_words_only_for_the_nude_item(monkeypatch):
    plain = "<Picture 1> is the character. A woman in a red coat."
    h = nude_harness(monkeypatch, writes=["A girl.", "A girl.", BODY])
    out = run_nude(h, prompt=[NUDE_DRAFT, plain])
    assert h.batches[-2:] == [("write", 2), ("write", 1)]
    assert nude_block((22, 28)) in h.writers[0]["prompt"]
    assert nude_block((22, 28)) not in h.writers[1]["prompt"]
    assert out["result"][0] == [
        NUDE_LEAD + "\n\n" + BODY,
        plain + "\n\nA girl.",
    ]
