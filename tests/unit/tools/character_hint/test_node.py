import pytest

import kikotools
from kikotools.tools.character_hint import logic
from kikotools.tools.character_hint.node import (
    CharacterHintFemaleNode,
    CharacterHintMaleNode,
)
from kikotools.tools.character_hint.options import UNSET

NODES = [CharacterHintFemaleNode, CharacterHintMaleNode]


@pytest.mark.parametrize("node_class", NODES)
def test_age_first_with_min_18(node_class):
    required = node_class.INPUT_TYPES()["required"]
    assert next(iter(required)) == "age"
    kind, config = required["age"]
    assert kind == "INT"
    assert config["min"] == 18 and config["max"] == 90 and config["default"] == 25
    assert config["display"] == "slider"


@pytest.mark.parametrize("node_class", NODES)
def test_combos_start_and_default_unset(node_class):
    required = node_class.INPUT_TYPES()["required"]
    for name, spec in required.items():
        if name == "age":
            continue
        choices = spec[0]
        assert choices[0] == UNSET, name
        assert spec[1]["default"] == UNSET, name


@pytest.mark.parametrize("node_class", NODES)
def test_extra_is_optional_multiline(node_class):
    extra = node_class.INPUT_TYPES()["optional"]["extra"]
    assert extra[0] == "STRING" and extra[1]["multiline"] is True


def test_gender_specific_inputs():
    female = CharacterHintFemaleNode.INPUT_TYPES()["required"]
    male = CharacterHintMaleNode.INPUT_TYPES()["required"]
    assert "breast_size" in female and "breast_size" not in male
    assert "facial_hair" in male and "facial_hair" not in female


@pytest.mark.parametrize("node_class", NODES)
@pytest.mark.parametrize(
    "name",
    [
        "facial_structure",
        "eyebrows",
        "eyewear",
        "hair_texture",
        "head_angle",
        "gaze",
    ],
)
def test_new_fields_are_dropdowns(node_class, name):
    choices = node_class.INPUT_TYPES()["required"][name][0]
    assert choices[0] == UNSET and len(choices) > 2


@pytest.mark.parametrize("node_class", NODES)
def test_pose_fields_follow_expression(node_class):
    names = list(node_class.INPUT_TYPES()["required"])
    start = names.index("expression")
    assert names[start : start + 3] == ["expression", "head_angle", "gaze"]


@pytest.mark.parametrize("node_class", NODES)
def test_return_shape(node_class):
    assert node_class.RETURN_TYPES == ("STRING",)
    assert node_class.RETURN_NAMES == ("hint",)
    assert node_class.FUNCTION == "build"
    assert node_class.CATEGORY == "🫶 ComfyAssets/🧠 Prompts"


def test_female_build_matches_logic():
    values = {"heritage": "Japanese", "body_type": "Curvy"}
    result = CharacterHintFemaleNode().build(30, extra="hi", **values)
    assert result == (logic.build_hint(logic.FEMALE, 30, values, "hi"),)


def test_male_build_matches_logic():
    values = {"facial_hair": "Goatee"}
    result = CharacterHintMaleNode().build(40, **values)
    assert result == (logic.build_hint(logic.MALE, 40, values),)


def test_user_makeup_style_shows_and_builds(write_user_file):
    write_user_file({"makeup": {"Mine": {"look": "my look", "lips": "my lips"}}})
    choices = CharacterHintFemaleNode.INPUT_TYPES()["required"]["makeup"][0]
    assert choices[-1] == "Mine"
    (text,) = CharacterHintFemaleNode().build(30, makeup="Mine")
    assert "Makeup: wearing my look, and my lips." in text


def test_removed_option_leaves_the_list_and_build_raises(write_user_file):
    write_user_file({"eye_color": {"Green": None}})
    choices = CharacterHintFemaleNode.INPUT_TYPES()["required"]["eye_color"][0]
    assert "Green" not in choices
    with pytest.raises(ValueError, match="eye_color"):
        CharacterHintFemaleNode().build(30, eye_color="Green")


def test_input_types_follow_file_edits(write_user_file):
    assert "Hawk" not in CharacterHintMaleNode.INPUT_TYPES()["required"]["nose"][0]
    write_user_file({"nose": {"Hawk": "a hawk nose"}})
    assert "Hawk" in CharacterHintMaleNode.INPUT_TYPES()["required"]["nose"][0]


def test_registered():
    maps = kikotools.NODE_CLASS_MAPPINGS
    names = kikotools.NODE_DISPLAY_NAME_MAPPINGS
    assert maps["KikoCharacterHintFemale"] is CharacterHintFemaleNode
    assert maps["KikoCharacterHintMale"] is CharacterHintMaleNode
    assert names["KikoCharacterHintFemale"] == "Character Hint (Female)"
    assert names["KikoCharacterHintMale"] == "Character Hint (Male)"


def test_is_changed_is_the_hint_text():
    values = {"eye_color": "Green"}
    stamp = CharacterHintFemaleNode.IS_CHANGED(30, extra="x", **values)
    assert stamp == logic.build_hint(logic.FEMALE, 30, values, "x")


def test_is_changed_follows_a_replaced_phrase(write_user_file):
    before = CharacterHintFemaleNode.IS_CHANGED(30, eye_color="Green")
    write_user_file({"eye_color": {"Green": "emerald eyes"}})
    after = CharacterHintFemaleNode.IS_CHANGED(30, eye_color="Green")
    assert before != after and "emerald eyes" in after


def test_is_changed_survives_a_removed_option(write_user_file):
    write_user_file({"eye_color": {"Green": None}})
    stamp = CharacterHintFemaleNode.IS_CHANGED(30, eye_color="Green")
    assert "eye_color" in stamp
