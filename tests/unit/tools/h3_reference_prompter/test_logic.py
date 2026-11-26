import pytest
import torch

from kikotools.tools.h3_reference_prompter.logic import (
    DEFAULT_ROLES,
    ROLES,
    SLOTS,
    clean_result,
    drop_echoes,
    drop_repeats,
    find_tags,
    image_key,
    item_seed,
    pair_items,
    split_reference_sentences,
    tag_problems,
)


def test_roles_and_slots_constants():
    assert ROLES == ("character", "outfit", "pose", "other")
    assert DEFAULT_ROLES == ("character", "outfit", "pose")
    assert SLOTS == 3


def test_find_tags_reads_numbers_with_spaces_inside_brackets():
    assert find_tags("<Picture 1> and < Picture 3 >") == {1, 3}


def test_find_tags_without_tags_is_empty():
    assert find_tags("a woman in a red coat") == set()


def test_tag_problems_reports_missing_and_extra_sorted():
    draft = "<Picture 1> <Picture 2> <Picture 3>"
    result = "<Picture 1> <Picture 3> <Picture 4>"
    assert tag_problems(draft, result) == ([2], [4])


def test_tag_problems_plain_draft_and_plain_result_are_clean():
    assert tag_problems("plain draft", "plain result") == ([], [])


def test_pair_items_broadcasts_single_length_columns():
    items = pair_items(prompt=["a", "b", "c"], image_1=["img"])
    assert items == [
        {"prompt": "a", "image_1": "img"},
        {"prompt": "b", "image_1": "img"},
        {"prompt": "c", "image_1": "img"},
    ]


def test_pair_items_rejects_mismatched_lengths_naming_both():
    with pytest.raises(ValueError) as error:
        pair_items(prompt=["a", "b"], image_1=["x", "y", "z"])
    message = str(error.value)
    assert "2" in message and "3" in message


def test_pair_items_empty_column_becomes_none():
    assert pair_items(prompt=["a"], image_2=[]) == [{"prompt": "a", "image_2": None}]
    assert pair_items(prompt=["a"], image_2=[None]) == [
        {"prompt": "a", "image_2": None}
    ]


def test_item_seed_wraps_at_64_bits():
    assert item_seed(2**64 - 1, 1) == 0


def test_image_key_changes_with_content_role_model_and_tokens():
    base = torch.zeros(1, 4, 4, 3)
    other = torch.ones(1, 4, 4, 3)
    key = image_key(base, "character", "model-a", 512)
    assert key == image_key(base.clone(), "character", "model-a", 512)
    assert key != image_key(other, "character", "model-a", 512)
    assert key != image_key(base, "outfit", "model-a", 512)
    assert key != image_key(base, "character", "model-b", 512)
    assert key != image_key(base, "character", "model-a", 1024)


def test_clean_result_strips_think_block():
    assert clean_result("<think>x</think>\nA woman stands.") == "A woman stands."


def test_clean_result_strips_preamble_line_and_quotes():
    assert clean_result('Here is the prompt:\n"A woman stands."') == "A woman stands."


def test_clean_result_strips_prompt_label_on_same_line():
    assert clean_result("Prompt: A woman stands.") == "A woman stands."


def test_clean_result_strips_code_fence_with_language():
    assert clean_result("```text\nA woman stands.\n```") == "A woman stands."


def test_drop_repeats_collapses_the_runaway_closing_list():
    text = "No extra fingers.\n" + "No other people.\n" * 100
    assert drop_repeats(text) == "No extra fingers.\nNo other people."


def test_drop_repeats_drops_repeated_line_ignoring_case_and_spacing():
    text = "No other  people.\nA hand.\nno OTHER people.\n"
    assert drop_repeats(text) == "No other  people.\nA hand."


def test_drop_repeats_drops_repeated_sentence_in_one_line():
    text = "She smiles. No other people. She waves. no other people.  She smiles."
    assert drop_repeats(text) == "She smiles. No other people. She waves."


def test_drop_repeats_keeps_blank_line_paragraph_breaks():
    text = "One line.\n\nTwo line.\n\nOne line.\n\nThree line."
    assert drop_repeats(text) == "One line.\n\nTwo line.\n\nThree line."


def test_drop_repeats_keeps_first_draft_sentence_and_its_tags():
    text = "<Picture 1> is the character. She stands. <Picture 1> is the " "character."
    result = drop_repeats(text)
    assert result == "<Picture 1> is the character. She stands."
    assert find_tags(result) == {1}


def test_drop_repeats_leaves_clean_text_untouched():
    text = "  Indented line. Second sentence.\n\nNext paragraph."
    assert drop_repeats(text) == text


def test_clean_result_drops_repeats_at_the_end():
    raw = "<think>x</think>\nShe stands.\n" + "No other people.\n" * 5
    assert clean_result(raw) == "She stands.\nNo other people."


LIVE_DRAFT = (
    "<Picture 1> is the character. <Picture 2> is the outfit. "
    "<Picture 3> is the pose. Draw the character from <Picture 1> in the pose "
    "and camera angle of <Picture 3>; the mannequin is only a pose guide, not "
    "an appearance reference. Dress the character in the complete outfit from "
    "<Picture 2>, copying every garment, colour and material exactly from "
    "that picture. Include the footwear shown in the outfit picture, worn on "
    "both feet. The pose: Front view, pose: Leaning-back sit, one knee raised "
    "(Sitting). Photorealistic studio photograph, real person, natural skin "
    "texture, soft even lighting. Full body from head to toe, plain light "
    "grey studio background."
)


def test_split_reference_sentences_separates_tag_sentences_verbatim():
    reference, rest = split_reference_sentences(LIVE_DRAFT)
    assert reference == (
        "<Picture 1> is the character. <Picture 2> is the outfit. "
        "<Picture 3> is the pose. Draw the character from <Picture 1> in the "
        "pose and camera angle of <Picture 3>; the mannequin is only a pose "
        "guide, not an appearance reference. Dress the character in the "
        "complete outfit from <Picture 2>, copying every garment, colour and "
        "material exactly from that picture."
    )
    assert rest == (
        "Include the footwear shown in the outfit picture, worn on both feet. "
        "The pose: Front view, pose: Leaning-back sit, one knee raised "
        "(Sitting). Photorealistic studio photograph, real person, natural "
        "skin texture, soft even lighting. Full body from head to toe, plain "
        "light grey studio background."
    )


def test_split_reference_sentences_semicolon_does_not_end_a_sentence():
    reference, rest = split_reference_sentences("Use <Picture 1>; wear a hat. Smile")
    assert reference == "Use <Picture 1>; wear a hat."
    assert rest == "Smile"


def test_split_reference_sentences_without_tags_returns_stripped_draft():
    assert split_reference_sentences("  a woman standing. Soft light.  ") == (
        "",
        "a woman standing. Soft light.",
    )


def test_split_reference_sentences_drops_stray_lone_period():
    reference, rest = split_reference_sentences("<Picture 1> is her. . Soft light.")
    assert reference == "<Picture 1> is her."
    assert rest == "Soft light."


def test_split_reference_sentences_empty_draft():
    assert split_reference_sentences("   ") == ("", "")


def test_split_reference_sentences_question_and_bang_end_sentences():
    reference, rest = split_reference_sentences("Who? <Picture 2> wins! Done")
    assert reference == "<Picture 2> wins!"
    assert rest == "Who? Done"


def test_drop_echoes_removes_sentences_equal_to_a_reference_sentence():
    reference = "<Picture 1> is her. <Picture 2> is the coat."
    written = "<picture 1>  IS her. She stands.\n\n<Picture 2> is the coat.\nEnd."
    assert drop_echoes(written, reference) == "She stands.\n\nEnd."


def test_drop_echoes_without_reference_keeps_text():
    assert drop_echoes("She stands. She sits.", "") == "She stands. She sits."


def test_drop_echoes_only_echo_gives_blank():
    assert drop_echoes("<Picture 1> is her.", "<Picture 1> is her.") == ""


def test_drop_echoes_keeps_partial_matches():
    text = "<Picture 1> is her, smiling."
    assert drop_echoes(text, "<Picture 1> is her.") == text
