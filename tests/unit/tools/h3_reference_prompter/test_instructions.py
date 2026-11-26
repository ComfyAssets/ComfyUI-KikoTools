"""Tests for the H3 Reference Prompter instruction text."""

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
            "side",
            "distance",
            "direction",
            "mannequin",
            "surface",
            "colour",
            "build",
            "face",
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
    positions = [text.index(name) for name in SECTIONS]
    assert positions == sorted(positions)
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
