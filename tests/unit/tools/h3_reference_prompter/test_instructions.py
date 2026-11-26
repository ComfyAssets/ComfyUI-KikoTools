"""Tests for the H3 Reference Prompter instruction text."""

import re

import pytest

from kikotools.tools.h3_reference_prompter.instructions import (
    describe_system,
    describe_user,
    adult_block,
    nude_block,
    retry_user,
    writer_system,
    writer_user,
)
from kikotools.tools.h3_reference_prompter.logic import (
    ROLES,
    YOUTH_WORDS,
    parse_age_estimate,
)

DRAFT = (
    "<Picture 1> is the character. <Picture 2> is the outfit. "
    "<Picture 3> is the pose. Draw the character from <Picture 1> in the pose "
    "of <Picture 3>; the mannequin is only a pose guide. Photorealistic studio "
    "photograph. The pose: Low angle view, pose: Leaning-back sit (Sitting)"
)

LEAD = (
    "<Picture 1> is the character. <Picture 2> is the outfit. <Picture 3> is the pose.\n"
    "Photorealistic studio photograph. The pose: Side view, Leaning-back sit."
)

SECTIONS = (
    "subject",
    "outfit",
    "pose",
    "camera",
    "lighting",
    "background",
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
    assert [number for number, _ in items] == list("1234567")
    for (_, line), name in zip(items, SECTIONS):
        assert name in line
    assert "250" in text and "450" in text
    assert "full sentences" in text
    assert "<picture n>" in text
    assert "exactly" in text
    assert "never write a tag that is not in the draft" in text


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
    text = writer_user(LEAD, notes)
    assert LEAD in text
    assert "Notes for <Picture 2> (outfit): A red wool coat." in text
    assert "<Picture 3> (pose)" in text
    assert "no picture" in text.lower()


def test_writer_user_marks_slot_missing_from_draft_as_context_only():
    notes = [(2, "outfit", "A red wool coat.")]
    text = writer_user("Plain draft with <Picture 1> only.", notes)
    assert "do not write its tag" in text.lower()
    assert "context only" in text.lower()


def test_writer_user_tagged_slot_is_not_context_only():
    text = writer_user(LEAD, [(2, "outfit", "A red wool coat.")])
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


def test_retry_user_blank_asks_for_the_whole_prompt():
    text = retry_user(([], []), blank=True)
    assert "empty" in text.lower()
    assert "<Picture" not in text
    assert text.endswith("give only the prompt.")


def test_retry_user_blank_and_tags_together():
    text = retry_user(([], [4]), blank=True)
    assert "empty" in text.lower() and "<Picture 4>" in text


def test_retry_user_without_blank_does_not_say_empty():
    assert "empty" not in retry_user(([2], [])).lower()


def test_writer_system_has_fallbacks():
    text = writer_system().lower()
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
    text = writer_user(LEAD, [(3, "pose", None)])
    assert "Notes for <Picture 3> (pose): no picture" in text


def test_writer_system_forbids_labels_with_examples():
    text = writer_system()
    lowered = text.lower()
    assert "plain paragraphs" in lowered
    assert "never write part numbers, part names or labels" in lowered
    assert '"The subject:"' in text
    assert '"The camera:"' in text


def test_writer_system_says_the_whole_draft_is_already_written():
    lowered = " ".join(writer_system().lower().split())
    assert "whole draft is already written word for word" in lowered
    assert "never repeat or rewrite its sentences" in lowered
    assert "start directly with the subject" in lowered
    assert "unless you repeat one of the draft's tags" in lowered
    assert "reference sentences" not in lowered


def test_writer_system_has_no_style_sentence_part():
    lowered = writer_system().lower()
    assert "no style sentence" not in lowered
    assert "the style sentence from the draft:" not in lowered
    assert "taken from the draft's remaining sentences" not in lowered


def test_writer_system_word_target_covers_only_the_models_part():
    lowered = " ".join(writer_system().lower().split())
    assert "250 to 450 words" in lowered
    assert "your part" in lowered


def test_writer_user_shows_the_lead_under_a_heading():
    text = writer_user(LEAD, [])
    heading = text[: text.index(LEAD)].lower()
    assert "whole draft" in heading
    assert "word for word" in heading
    assert "do not repeat or rewrite" in heading
    assert "detail that follows" in heading


def test_writer_user_without_a_lead_has_no_lead_block():
    text = writer_user("", [(1, "character", "A woman.")])
    assert "already written" not in text
    assert "Notes for <Picture 1> (character), context only: A woman." in text
    assert "Write the final prompt now." in text


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


def test_writer_repeats_traits_inside_sentences_not_as_a_summary():
    text = writer_system()
    assert "mention the key traits once more in other words" in text
    assert 'never write a separate summary such as "Same description:"' in text


def test_character_describer_says_each_trait_once():
    text = describe_system("character")
    assert "Say each trait once." in text
    assert "twice" not in text


def test_character_describer_pins_bangs_and_mouth():
    text = describe_system("character")
    assert "the fringe or bangs exactly as they fall" in text
    assert "a wide smile with the teeth showing" in text


def test_outfit_describer_says_length_and_where_items_are_worn():
    text = describe_system("outfit")
    assert "how far it reaches on the body" in text
    assert "socks at the ankle, mid-calf or knee" in text
    assert "a hat worn on the head" in text
    assert "is still worn in its usual place" in text


def test_writer_uses_other_notes_as_setting_or_prop_detail():
    text = " ".join(writer_system().split())
    assert "role other" in text
    assert "setting or prop detail" in text
    assert "Never describe a person from them unless the draft says so." in text


def test_writer_covers_same_role_pictures_in_slot_order():
    text = " ".join(writer_system().split())
    assert "same role" in text
    assert "slot order" in text


def test_pose_describer_starts_with_overall_position_and_facing():
    text = describe_system("pose")
    assert "Start with one sentence that names the overall position" in text
    assert "which way the body faces the camera (front, side or back)" in text


def test_outfit_describer_never_lets_items_float():
    assert "never say an item floats, hovers or is suspended" in describe_system(
        "outfit"
    )


def test_writer_pose_follows_the_drafts_view_and_accessories_stay_in_place():
    text = " ".join(writer_system().split())
    assert "Begin it with the draft's view" not in text
    assert "in the view and position the draft names" in text
    assert "where the weight rests" in text
    assert "The notes only add detail to the pose the draft names" in text
    assert "Keep the pose name from the draft" not in text
    assert "The draft's view and position win over the notes." in text
    assert "a hat is on the head" in text
    assert "Never write that an item floats or hovers" in text


def test_character_describer_always_ends_with_the_age_line():
    text = describe_system("character")
    assert "Estimated age: N to M years." in text
    assert "whole numbers" in text and "last line" in text
    assert parse_age_estimate("Estimated age: N to M years.") is None


@pytest.mark.parametrize("role", ["outfit", "pose", "other"])
def test_other_describers_do_not_ask_for_an_age(role):
    assert "Estimated age" not in describe_system(role)


def test_nude_block_describes_the_unclothed_adult_body():
    text = nude_block((22, 28))
    lowered = text.lower()
    assert "the draft says the person is nude" in lowered
    assert "no outfit picture" in lowered
    assert "in place of the outfit part" in lowered
    for word in ("build", "proportions", "skin tone", "texture", "adult anatomy"):
        assert word in lowered
    assert "figure" in lowered and "photography reference" in lowered


def test_nude_block_forbids_sexual_content_and_clothing():
    lowered = nude_block((22, 28)).lower()
    assert "no sexual acts" in lowered
    assert "no sexual poses" in lowered
    assert "arousal" in lowered and "explicit" in lowered
    assert "no clothing, no footwear and no accessories" in lowered
    assert "unless the draft names them" in lowered


def test_nude_block_uses_adult_wording_and_bans_youth_words():
    text = nude_block((22, 28))
    assert "an adult woman aged 22 to 28" in text
    assert "in her twenties" in text
    assert "adult man" in text
    for word in YOUTH_WORDS:
        assert f'"{word}"' in text


def test_nude_block_offers_in_her_twenties_only_for_a_twenties_range():
    assert "in her twenties" not in nude_block((31, 38))
    assert "an adult woman aged 31 to 38" in nude_block((31, 38))


NUDE_LEAD = LEAD + " The character's outfit: completely nude."


def test_writer_user_adds_the_nude_block_before_the_closing_line():
    notes = [(1, "character", "Dark hair.")]
    plain = writer_user(NUDE_LEAD, notes)
    nude = writer_user(NUDE_LEAD, notes, adult=(22, 28))
    assert nude_block((22, 28)) not in plain
    assert nude.endswith(nude_block((22, 28)) + "\n\nWrite the final prompt now.")
    assert nude.replace(nude_block((22, 28)) + "\n\n", "") == plain


def test_writer_user_keeps_the_outfit_when_an_outfit_picture_is_connected():
    notes = [(1, "character", "Dark hair."), (2, "outfit", "A red coat.")]
    text = writer_user(NUDE_LEAD, notes, adult=(22, 28))
    assert nude_block((22, 28)) not in text
    assert text.endswith(adult_block((22, 28)) + "\n\nWrite the final prompt now.")
    assert '"teen"' in adult_block((22, 28))
    assert '"girl"' not in adult_block((22, 28))


def test_retry_user_names_a_banned_word():
    text = retry_user(([], []), banned="teen")
    assert '"teen"' in text and "Remove" in text
    assert "adult woman" in text
    assert "picture tags" not in text
    assert text.endswith("give only the prompt.")


def test_retry_user_without_banned_word_is_unchanged():
    assert "Remove the word" not in retry_user(([], [4]))


HINT = (
    "The character is an adult woman aged 25. Body: a curvy body. "
    "Unclothed detail: pierced nipples. Extra: has a scar."
)


def test_writer_user_puts_the_hint_after_the_notes():
    notes = [(1, "character", "Dark hair.")]
    text = writer_user("Draft.", notes, hint=HINT)
    assert text.index("Dark hair.") < text.index(HINT.split(" Unclothed")[0])
    assert "the hint wins" in text or "hint wins" in text
    assert text.endswith("Write the final prompt now.")


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_writer_user_treats_a_blank_hint_as_no_hint(blank):
    notes = [(1, "character", "Dark hair.")]
    assert writer_user("Draft.", notes, hint=blank) == writer_user("Draft.", notes)


def test_writer_user_drops_unclothed_detail_for_a_clothed_item():
    notes = [(1, "character", "Dark hair.")]
    text = writer_user("Draft.", notes, hint=HINT)
    assert "Unclothed detail" not in text
    assert "Extra: has a scar." in text


def test_writer_user_keeps_unclothed_detail_for_a_nude_item():
    notes = [(1, "character", "Dark hair.")]
    text = writer_user("The woman is nude.", notes, adult=(25, 25), hint=HINT)
    assert "Unclothed detail: pierced nipples." in text
    assert text.index("Unclothed detail") < text.index("Nude mode")


def test_writer_user_drops_unclothed_detail_when_an_outfit_is_connected():
    notes = [(1, "character", "Dark hair."), (2, "outfit", "A red coat.")]
    text = writer_user("The woman is nude.", notes, adult=(25, 25), hint=HINT)
    assert "Unclothed detail" not in text


def test_nude_block_with_one_age_says_aged_n_only():
    text = nude_block((25, 25))
    assert "aged 25" in text
    assert "25 to 25" not in text
    assert "twenties" not in text
    assert "character notes or the character hint say" in text


def test_adult_block_with_one_age_says_aged_n_only():
    assert "25 to 25" not in adult_block((25, 25))
    assert "aged 25" in adult_block((25, 25))
