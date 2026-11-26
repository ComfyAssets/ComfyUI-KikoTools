import pytest

from kikotools.tools.character_hint import logic
from kikotools.tools.character_hint.options import UNSET


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
