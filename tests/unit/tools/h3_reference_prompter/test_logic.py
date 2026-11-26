import pytest
import torch

from kikotools.tools.h3_reference_prompter.logic import (
    AUTO,
    DEFAULT_ROLES,
    NUDE_MIN_AGE,
    ROLE_CHOICES,
    ROLES,
    SLOTS,
    YOUTH_WORDS,
    check_adult,
    clean_result,
    draft_lead,
    cap_negatives,
    drop_echoes,
    says_nude,
    drop_repeats,
    find_tags,
    find_youth_word,
    image_key,
    is_nude,
    is_placeholder,
    item_seed,
    pair_items,
    parse_age_estimate,
    resolve_roles,
    tag_problems,
)


def test_roles_and_slots_constants():
    assert ROLES == ("character", "outfit", "pose", "other")
    assert DEFAULT_ROLES == ("character", "outfit", "pose")
    assert SLOTS == 3
    assert AUTO == "auto"
    assert ROLE_CHOICES == ("auto", "character", "outfit", "pose", "other")


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


def test_draft_lead_keeps_the_whole_live_draft_verbatim_without_the_stray_period():
    assert draft_lead(LIVE_DRAFT) == LIVE_DRAFT


def test_draft_lead_drops_a_stray_lone_period():
    draft = "<Picture 1> is her. . Soft light. Full body."
    assert draft_lead(draft) == "<Picture 1> is her. Soft light. Full body."


def test_draft_lead_semicolon_does_not_end_a_sentence():
    assert draft_lead("Use <Picture 1>; wear a hat. Smile") == (
        "Use <Picture 1>; wear a hat. Smile"
    )


def test_draft_lead_blank_draft_is_empty():
    assert draft_lead("   \n ") == ""
    assert draft_lead("") == ""


def test_draft_lead_keeps_lines_and_skips_empty_ones():
    draft = (
        "<Picture 1> is her.   <Picture 2> is the coat.\n"
        "\n"
        "  Photorealistic. \n"
        " . \n"
        "Full body."
    )
    assert draft_lead(draft) == (
        "<Picture 1> is her. <Picture 2> is the coat.\nPhotorealistic.\nFull body."
    )


def test_draft_lead_keeps_sentences_without_tags_in_order():
    assert draft_lead("  a woman standing. Soft light.  ") == (
        "a woman standing. Soft light."
    )


@pytest.mark.parametrize("title", ["Dr.", "Mr.", "Mrs.", "St."])
def test_draft_lead_keeps_titles_inside_a_sentence(title):
    draft = f"{title} Kim wears <Picture 1>. Soft light."
    assert draft_lead(draft) == draft


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


def test_drop_echoes_reads_multi_line_references():
    reference = "<Picture 1> is her.\nDr. Kim wears <Picture 2>."
    written = "Dr. Kim wears <Picture 2>. She stands."
    assert drop_echoes(written, reference) == "She stands."


def test_drop_echoes_does_not_split_a_title_off_the_written_part():
    assert drop_echoes("Dr. Lee waves.", "Dr. Kim wears <Picture 2>.") == (
        "Dr. Lee waves."
    )


def test_draft_lead_still_splits_after_longer_or_lowercase_words():
    assert draft_lead("It is red. <Picture 1> is Bold. Next one.") == (
        "It is red. <Picture 1> is Bold. Next one."
    )


def test_drop_echoes_drops_any_repeated_draft_sentence():
    lead = "Side view, sitting. Photorealistic photograph."
    written = "Side view, sitting. She waves. Photorealistic  photograph."
    assert drop_echoes(written, lead) == "She waves."


def test_drop_echoes_ignores_end_punctuation():
    lead = "Side view\nAnime style, full body"
    written = "Side view. The girl stands. Anime style, full body"
    assert drop_echoes(written, lead) == "The girl stands."


NUDE_DRAFT = (
    "<Picture 1> is the character. <Picture 2> is the pose. Draw the character "
    "from <Picture 1> in the pose and camera angle of <Picture 2>; the mannequin "
    "is only a pose guide, not an appearance reference. The character's outfit: "
    "completely nude, wearing no clothing and no footwear. The pose: Front view, "
    "pose: Standing contrapposto, hand on hip (Standing). Photorealistic studio "
    "photograph, real person, natural skin texture, soft even lighting. Full "
    "body from head to toe, plain light grey studio background."
)
THREE_DRAFT = (
    "<Picture 1> is the character. <Picture 2> is the outfit. <Picture 3> is "
    "the pose. Draw the character from <Picture 1> in the pose and camera angle "
    "of <Picture 3>."
)
ALL_AUTO = ("auto", "auto", "auto")


def test_resolve_roles_nude_draft_makes_slot_2_the_pose():
    assert resolve_roles(NUDE_DRAFT, ALL_AUTO) == ("character", "pose", "pose")


def test_resolve_roles_usual_three_picture_draft():
    assert resolve_roles(THREE_DRAFT, ALL_AUTO) == ("character", "outfit", "pose")


def test_resolve_roles_explicit_role_overrides_auto():
    roles = ("auto", "outfit", "other")
    assert resolve_roles(NUDE_DRAFT, roles) == ("character", "outfit", "other")


def test_resolve_roles_without_picture_sentences_falls_back_to_defaults():
    assert resolve_roles("a woman in <Picture 2> standing", ALL_AUTO) == DEFAULT_ROLES
    assert resolve_roles("", ALL_AUTO) == DEFAULT_ROLES


def test_resolve_roles_is_case_insensitive_and_allows_spacing():
    draft = "< picture 3 >  IS THE Outfit . <PICTURE 1> is the pose."
    assert resolve_roles(draft, ALL_AUTO) == ("pose", "outfit", "outfit")


def test_resolve_roles_reads_the_chinese_picture_sentences():
    draft = "<Picture 1>是人物。<Picture 2>是姿势。"
    assert resolve_roles(draft, ALL_AUTO) == ("character", "pose", "pose")


def test_resolve_roles_ignores_slots_beyond_three():
    draft = "<Picture 4> is the outfit. <Picture 2> is the pose."
    assert resolve_roles(draft, ALL_AUTO) == ("character", "pose", "pose")


def test_nude_constants():
    assert NUDE_MIN_AGE == 20
    assert YOUTH_WORDS == (
        "teen",
        "teenage",
        "teenager",
        "adolescent",
        "schoolgirl",
        "child",
        "childlike",
        "kid",
        "minor",
        "underage",
        "loli",
    )


def test_is_nude_for_the_charsheet_nude_draft_without_an_outfit_picture():
    assert is_nude(NUDE_DRAFT, ["character", "pose"]) is True


@pytest.mark.parametrize("word", ["Nude", "NAKED", "naked"])
def test_is_nude_matches_either_word_in_any_case(word):
    assert is_nude(f"A woman, {word}, standing.", []) is True


def test_is_nude_is_off_when_an_outfit_picture_is_connected():
    assert is_nude(NUDE_DRAFT, ["character", "outfit", "pose"]) is False


@pytest.mark.parametrize("draft", ["nudes and nudity", "a denuded hill", "", None])
def test_is_nude_needs_the_whole_word(draft):
    assert is_nude(draft, []) is False


@pytest.mark.parametrize(
    "notes, expected",
    [
        ("Dark hair.\nEstimated age: 22 to 28 years.", (22, 28)),
        ("estimated AGE:  25 to 30 years", (25, 30)),
        ("Estimated age: 30 to 25 years.", (25, 30)),
        ("Estimated age: 18 to 24 years. Estimated age: 26 to 30 years.", (26, 30)),
        ("Estimated age: 22-28 years.", (22, 28)),
    ],
)
def test_parse_age_estimate_reads_the_last_estimate_line(notes, expected):
    assert parse_age_estimate(notes) == expected


@pytest.mark.parametrize(
    "notes",
    ["", None, "She looks about 25.", "Estimated age: twenty to thirty years."],
)
def test_parse_age_estimate_missing_or_unparsable_is_none(notes):
    assert parse_age_estimate(notes) is None


@pytest.mark.parametrize(
    "text, word",
    [
        ("She is in her late teens.", "teens"),
        ("A Teenager with dark hair.", "teenager"),
        ("childlike features", "childlike"),
        ("UNDERAGE", "underage"),
        ("a pre-teen look", "teen"),
        ("two kids", "kids"),
        ("Three Children.", "children"),
        ("a teenaged look", "teenaged"),
    ],
)
def test_find_youth_word_matches_whole_words_in_any_case(text, word):
    assert find_youth_word(text) == word


def test_find_youth_word_ignores_partial_words_and_young_woman():
    assert find_youth_word("A young woman, canteen, kidney, minority.") is None
    assert find_youth_word("") is None


def test_find_youth_word_does_not_check_girl():
    assert find_youth_word("A girl stands. Two GIRLS.") is None


ADULT_NOTES = "A young woman with dark hair.\nEstimated age: 22 to 28 years."


def test_check_adult_returns_the_estimate():
    assert check_adult([(1, ADULT_NOTES)], NUDE_DRAFT) == (22, 28)


def test_check_adult_spans_every_character_picture():
    second = "A woman.\nEstimated age: 25 to 34 years."
    assert check_adult([(1, ADULT_NOTES), (3, second)], NUDE_DRAFT) == (22, 34)


def _refusal(notes, draft=NUDE_DRAFT):
    with pytest.raises(ValueError) as caught:
        check_adult(notes, draft)
    message = str(caught.value)
    assert message.startswith(
        "Nude prompts need an adult character picture whose estimated age is "
        "20 or older."
    )
    return message


def test_check_adult_refuses_without_a_character_picture():
    assert "No character picture is connected" in _refusal([])


def test_check_adult_refuses_a_missing_estimate():
    message = _refusal([(1, "A woman with dark hair.")])
    assert "no age estimate for image_1" in message


def test_check_adult_refuses_a_lower_bound_under_20():
    message = _refusal([(2, "A woman.\nEstimated age: 19 to 25 years.")])
    assert "19 to 25 years for image_2" in message


def test_check_adult_accepts_a_lower_bound_of_exactly_20():
    notes = [(1, "A woman.\nEstimated age: 20 to 26 years.")]
    assert check_adult(notes, NUDE_DRAFT) == (20, 26)


def test_check_adult_refuses_a_youth_word_in_the_notes_and_gives_the_estimate():
    notes = [(1, "She is in her late teens.\nEstimated age: 20 to 24 years.")]
    message = _refusal(notes)
    assert "'teens'" in message and "20 to 24 years" in message


def test_check_adult_accepts_girl_in_the_draft():
    assert check_adult([(1, ADULT_NOTES)], "A nude girl standing.") == (22, 28)


def test_check_adult_refuses_a_youth_word_in_the_draft():
    assert "'teen'" in _refusal([(1, ADULT_NOTES)], "A nude teen.")


def test_check_adult_does_not_check_girl_in_the_notes():
    notes = [(1, "A girl-next-door look.\nEstimated age: 24 to 30 years.")]
    assert check_adult(notes, NUDE_DRAFT) == (24, 30)


@pytest.mark.parametrize(
    "draft, expected",
    [
        ("完全裸体，不穿衣服。", True),
        ("Completely NAKED.", True),
        ("A red coat.", False),
        (None, False),
    ],
)
def test_says_nude_matches_english_and_chinese(draft, expected):
    assert says_nude(draft) is expected


@pytest.mark.parametrize(
    "image, expected",
    [
        (torch.ones((1, 64, 64, 3)), True),
        (torch.full((1, 128, 96, 3), 0.98), True),
        (torch.ones((1, 512, 512, 3)), False),
        (torch.ones((1, 64, 129, 3)), False),
        (torch.full((1, 64, 64, 3), 0.5), False),
        (torch.full((1, 64, 64, 3), 0.97), False),
    ],
)
def test_is_placeholder_needs_a_small_uniformly_white_image(image, expected):
    assert is_placeholder(image) is expected


def test_is_placeholder_rejects_an_image_with_one_dark_pixel():
    image = torch.ones((1, 64, 64, 3))
    image[0, 10, 10, 0] = 0.2
    assert is_placeholder(image) is False


def test_cap_negatives_cuts_a_long_comma_run_to_six():
    items = ", ".join(f"no thing {n}" for n in range(1, 41))
    text = f"She sits on the floor, against a grey wall, {items}, no end."
    got = cap_negatives(text)
    assert got == (
        "She sits on the floor, against a grey wall, no thing 1, no thing 2, "
        "no thing 3, no thing 4, no thing 5, no thing 6."
    )


def test_cap_negatives_keeps_a_short_list_and_line_lists():
    short = "Soft light.\n\nNo extra fingers or limbs.\nNo other people.\nNo text."
    assert cap_negatives(short) == short
    lines = "\n".join(f"No problem {n}." for n in range(1, 10))
    assert cap_negatives(lines) == "\n".join(f"No problem {n}." for n in range(1, 7))


def test_clean_result_caps_negatives():
    long = "A woman. " + " ".join(f"No item {n}." for n in range(1, 12))
    assert clean_result(long).count("No item") == 6


def test_cap_negatives_drops_blank_lines_after_the_cut():
    text = "\n\n".join(f"No problem {n}." for n in range(1, 10))
    assert cap_negatives(text) == "\n\n".join(f"No problem {n}." for n in range(1, 7))
