"""Tests for the H3 Reference Prompter instruction text."""

import re

import pytest

from kikotools.tools.h3_reference_prompter.instructions import (
    describe_system,
    describe_user,
    retry_user,
    writer_system,
    writer_user,
)
from kikotools.tools.h3_reference_prompter.logic import ROLES

DRAFT = (
    "<Picture 1> is the character. <Picture 2> is the outfit. "
    "<Picture 3> is the pose. Draw the character from <Picture 1> in the pose "
    "of <Picture 3>; the mannequin is only a pose guide. Photorealistic studio "
    "photograph. The pose: Low angle view, pose: Leaning-back sit (Sitting)"
)

SECTIONS = (
    "reference sentences",
    "subject",
    "outfit",
    "pose",
    "camera",
    "lighting",
    "background",
    "style",
    "closing list",
)


def _has_all(text, words):
    lowered = text.lower()
    return [w for w in words if w not in lowered]


def test_describe_system_covers_character_fields():
    text = describe_system("character")
    assert not _has_all(
        text, ["face", "eyes", "hair", "skin", "build", "clothing", "background"]
    )
    assert "do not describe" in text.lower()


def test_describe_system_covers_outfit_fields():
    text = describe_system("outfit")
    assert not _has_all(
        text, ["garment", "colour", "material", "footwear", "accessories", "fit"]
    )


def test_describe_system_covers_pose_fields():
    text = describe_system("pose")
    assert not _has_all(
        text,
        [
            "left hand",
            "right hand",
            "left foot",
            "right foot",
            "weight",
            "height",
            "the side it sits on",
            "distance",
            "direction",
            "do not mention its surface, colour, build or face",
            "subject's left",
        ],
    )
    assert "never describe the mannequin" in text.lower()


@pytest.mark.parametrize("role", ROLES)
def test_describe_system_asks_for_full_sentences(role):
    assert "full sentences" in describe_system(role).lower()


def test_describe_system_rejects_unknown_role():
    with pytest.raises(ValueError):
        describe_system("furniture")


def test_describe_user_gives_draft_and_role():
    text = describe_user("outfit", DRAFT)
    assert "outfit" in text
    assert DRAFT in text
    assert "this picture only" in text.lower()


def test_describe_user_rejects_unknown_role():
    with pytest.raises(ValueError):
        describe_user("furniture", DRAFT)


def test_writer_system_lists_sections_in_order():
    text = writer_system().lower()
    items = re.findall(r"^([1-9])\. (.*)$", text, re.MULTILINE)
    assert [number for number, _ in items] == list("123456789")
    for (_, line), name in zip(items, SECTIONS):
        assert name in line
    assert "250" in text and "450" in text
    assert "full sentences" in text
    assert "<picture n>" in text
    assert "exactly" in text
    assert "add none" in text or "do not add" in text


def test_writer_system_carries_the_rules():
    text = writer_system().lower()
    assert "mannequin" in text
    assert "draft wins" in text or "the draft wins" in text
    assert "one problem per line" in text
    assert "no extra fingers" in text


def test_writer_user_labels_notes_by_tag():
    notes = [
        (1, "character", "A woman in her thirties."),
        (2, "outfit", "A red wool coat."),
        (3, "pose", None),
    ]
    text = writer_user(DRAFT, notes)
    assert DRAFT in text
    assert "Notes for <Picture 2> (outfit): A red wool coat." in text
    assert "<Picture 3> (pose)" in text
    assert "no picture" in text.lower()


def test_writer_user_marks_slot_missing_from_draft_as_context_only():
    notes = [(2, "outfit", "A red wool coat.")]
    text = writer_user("Plain draft with <Picture 1> only.", notes)
    assert "do not write its tag" in text.lower()
    assert "context only" in text.lower()


def test_writer_user_tagged_slot_is_not_context_only():
    text = writer_user(DRAFT, [(2, "outfit", "A red wool coat.")])
    assert "context only" not in text.lower()


def test_retry_user_names_tags():
    text = retry_user(([2], [4]))
    assert "<Picture 2>" in text
    assert "<Picture 4>" in text
    assert "missing" in text.lower()
    assert "extra" in text.lower() or "remove" in text.lower()


def test_retry_user_omits_empty_side():
    text = retry_user(([2], []))
    assert "<Picture 2>" in text
    assert "extra" not in text.lower()


def test_writer_system_has_fallbacks():
    text = writer_system().lower()
    assert "names no pictures, skip" in text
    assert "no style sentence, skip" in text
    assert "lighting and the background from the draft first" in text
    assert "plain, neutral choice" in text
    assert "invent nothing" in text


def test_describe_user_forbids_tags():
    assert "do not write any <picture n> tags" in describe_user("pose", DRAFT).lower()


def test_writer_user_skips_empty_slot_not_in_draft():
    text = writer_user("Only <Picture 1> here.", [(3, "pose", None)])
    assert "<Picture 3>" not in text
    assert "No notes." in text


def test_writer_user_keeps_empty_slot_in_draft():
    text = writer_user(DRAFT, [(3, "pose", None)])
    assert "Notes for <Picture 3> (pose): no picture" in text


def test_writer_system_forbids_labels_with_examples():
    text = writer_system()
    lowered = text.lower()
    assert "plain paragraphs" in lowered
    assert "never write part numbers, part names or labels" in lowered
    assert '"The subject:"' in text
    assert '"The style sentence from the draft:"' in text


def test_writer_system_part_one_copies_only_tagged_sentences():
    lowered = " ".join(writer_system().lower().split())
    assert "only the draft's sentences that contain a <picture n> tag" in lowered
    assert "every other draft sentence" in lowered
    assert "style, framing, pose name" in lowered
    assert "its own part below, once" in lowered


def test_writer_system_closing_list_is_short_distinct_and_last():
    lowered = " ".join(writer_system().lower().split())
    assert "three to six lines" in lowered
    assert "each line about a different problem" in lowered
    assert "never repeat a line" in lowered
    assert "nothing comes after the closing list" in lowered


def test_pose_describer_puts_each_limb_in_one_place_and_checks():
    text = " ".join(describe_system("pose").lower().split())
    assert "each hand and each foot is in one place only" in text
    assert "never put one hand in two places" in text
    assert "agree with each other" in text


def test_pose_describer_says_hidden_limbs_are_hidden():
    text = " ".join(describe_system("pose").lower().split())
    assert "hidden" in text
    assert "instead of guessing" in text
