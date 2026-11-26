import copy

import pytest

from kikotools.tools.character_hint import logic, options
from kikotools.tools.character_hint.options import UNSET

FEMALE_VALUES = {
    "heritage": "Japanese",
    "body_type": "Curvy",
    "breast_size": "Large",
    "butt_size": "Large",
    "face_shape": "Round",
    "eye_color": "Green",
    "eye_shape": "Hooded",
    "lip_shape": "Full",
    "lip_color": "Berry",
    "makeup": "Soft glam",
    "hair_color": "Copper",
    "hair_length": "Chin length",
    "hair_style": "Bob",
    "bangs": "Curtain bangs",
    "skin_tone": "Olive",
    "freckles": "A few",
    "beauty_mark": "Left cheek",
    "tattoo": "Sleeve tattoo",
    "expression": "Smirking",
    "nipples": "Pierced",
    "areola": "Dark",
}

FEMALE_GOLDEN = (
    "The character is an adult Japanese woman aged 25. "
    "Body: a curvy body, large breasts, a large butt. "
    "Face: a round face, green eyes, hooded eyes, full lips. "
    "Makeup: wearing soft glam makeup, smoothly blended taupe eyeshadow, "
    "softly defined eyeliner, fluttery lashes, warm blush, and berry lips. "
    "Hair: copper hair, chin length hair, her hair in a bob cut, curtain bangs. "
    "Skin: olive skin, a few freckles, a single beauty mark on the left cheek. "
    "Tattoos: a sleeve tattoo. "
    "Expression: a smirking expression. "
    "Unclothed detail: pierced nipples, dark areolas. "
    "Extra: has a scar on the chin."
)


def test_golden_female_hint():
    text = logic.build_hint("woman", 25, FEMALE_VALUES, extra=" has a scar on the chin")
    assert text == FEMALE_GOLDEN


def test_golden_male_hint():
    values = {
        "body_type": "Dad bod",
        "facial_hair": "Goatee",
        "hair_style": "Man bun",
        "breast_size": "Large",
    }
    assert logic.build_hint("man", 40, values) == (
        "The character is an adult man aged 40. "
        "Body: a dad bod. Face: a goatee. Hair: a man bun."
    )


def test_explicit_tables_are_used():
    tables = copy.deepcopy(options.load_shipped())
    tables["nose"]["Hawk"] = "a hawk nose"
    tables["makeup"]["Mine"] = {"look": "my look", "lips": "my lips"}
    tables["heritage"]["Maori"] = "Maori"
    values = {"nose": "Hawk", "makeup": "Mine", "heritage": "Maori"}
    text = logic.build_hint("woman", 30, values, tables=tables)
    assert "adult Maori woman" in text
    assert "Face: a hawk nose." in text
    assert "Makeup: wearing my look, and my lips." in text
    assert "Hawk" in logic.fields("woman", tables)["nose"]


def test_removed_label_raises_naming_field():
    tables = copy.deepcopy(options.load_shipped())
    del tables["eye_color"]["Green"]
    with pytest.raises(ValueError, match="eye_color"):
        logic.build_hint("woman", 30, {"eye_color": "Green"}, tables=tables)


def test_removed_makeup_raises():
    tables = copy.deepcopy(options.load_shipped())
    del tables["makeup"]["Soft glam"]
    with pytest.raises(ValueError, match="makeup"):
        logic.build_hint("woman", 30, {"makeup": "Soft glam"}, tables=tables)


def test_lead_only():
    assert (
        logic.build_hint("woman", 25, {}) == "The character is an adult woman aged 25."
    )


def test_heritage_goes_in_lead():
    assert (
        logic.build_hint("man", 40, {"heritage": "Japanese"})
        == "The character is an adult Japanese man aged 40."
    )


def test_body_part():
    text = logic.build_hint(
        "woman",
        30,
        {"body_type": "Curvy", "breast_size": "Large", "butt_size": "Large"},
    )
    assert text.endswith("Body: a curvy body, large breasts, a large butt.")


def test_makeup_alone():
    text = logic.build_hint("woman", 30, {"makeup": "Soft glam"})
    assert (
        "Makeup: wearing soft glam makeup, smoothly blended taupe eyeshadow, "
        "softly defined eyeliner, fluttery lashes, warm blush, and satin nude lips."
    ) in text


def test_lip_colour_replaces_makeup_lips():
    text = logic.build_hint("woman", 30, {"makeup": "Soft glam", "lip_color": "Berry"})
    assert "warm blush, and berry lips." in text
    assert "satin nude lips" not in text


def test_lip_colour_without_makeup_goes_in_face():
    text = logic.build_hint("woman", 30, {"lip_color": "Berry"})
    assert "Face: berry lips." in text
    assert "Makeup:" not in text


def test_male_ignores_female_only_fields():
    text = logic.build_hint(
        "man",
        30,
        {"breast_size": "Large", "makeup": "Soft glam", "nipples": "Pierced"},
    )
    assert text == "The character is an adult man aged 30."


def test_male_facial_hair():
    text = logic.build_hint("man", 30, {"facial_hair": "Goatee"})
    assert "Face: a goatee." in text


def test_unclothed_detail():
    text = logic.build_hint("woman", 30, {"nipples": "Pierced", "areola": "Dark"})
    assert "Unclothed detail: pierced nipples, dark areolas." in text


def test_extra_is_trimmed_and_ends_with_full_stop():
    text = logic.build_hint("woman", 30, {}, extra="  has a scar on the chin ")
    assert text.endswith("Extra: has a scar on the chin.")


def test_extra_full_stop_not_doubled():
    text = logic.build_hint("woman", 30, {}, extra="has a scar.")
    assert text.endswith("Extra: has a scar.")


@pytest.mark.parametrize("extra", ["love it!", "what?"])
def test_extra_keeps_its_own_end_punctuation(extra):
    text = logic.build_hint("woman", 30, {}, extra=extra)
    assert text.endswith(f"Extra: {extra}")


def test_extra_without_letters_or_digits_adds_nothing():
    plain = logic.build_hint("woman", 30, {})
    assert logic.build_hint("woman", 30, {}, extra="...") == plain
    assert logic.build_hint("woman", 30, {}, extra=" ! ") == plain


@pytest.mark.parametrize("extra", ["", "   \n"])
def test_blank_extra_adds_nothing(extra):
    text = logic.build_hint("woman", 30, {}, extra=extra)
    assert text == "The character is an adult woman aged 30."


def test_unset_values_are_skipped():
    text = logic.build_hint("woman", 30, {"body_type": UNSET, "nose": UNSET})
    assert text == "The character is an adult woman aged 30."


def test_unknown_label_raises_naming_field():
    with pytest.raises(ValueError, match="eye_color"):
        logic.build_hint("woman", 30, {"eye_color": "Plaid"})


def test_unknown_gender_raises():
    with pytest.raises(ValueError, match="gender"):
        logic.build_hint("robot", 30, {})


def test_part_order():
    values = {
        "heritage": "Japanese",
        "body_type": "Curvy",
        "face_shape": "Round",
        "makeup": "Soft glam",
        "hair_color": "Copper",
        "skin_tone": "Olive",
        "tattoo": next(iter(logic.fields("woman")["tattoo"])),
        "expression": next(iter(logic.fields("woman")["expression"])),
        "nipples": "Pierced",
    }
    text = logic.build_hint("woman", 25, values, extra="Note")
    markers = [
        "The character",
        "Body:",
        "Face:",
        "Makeup:",
        "Hair:",
        "Skin:",
        "Tattoos:",
        "Expression:",
        "Unclothed detail:",
        "Extra:",
    ]
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)


def test_fields_order_and_gender_sets():
    female = list(logic.fields("woman"))
    male = list(logic.fields("man"))
    assert female[:2] == ["heritage", "body_type"]
    assert "breast_size" in female and "breast_size" not in male
    assert "facial_hair" in male and "facial_hair" not in female
    assert female[-2:] == ["nipples", "areola"]
    assert UNSET not in logic.fields("woman")["body_type"]


def test_fields_unknown_gender():
    with pytest.raises(ValueError):
        logic.fields("robot")
