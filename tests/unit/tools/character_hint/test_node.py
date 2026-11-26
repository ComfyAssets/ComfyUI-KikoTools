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


def test_registered():
    maps = kikotools.NODE_CLASS_MAPPINGS
    names = kikotools.NODE_DISPLAY_NAME_MAPPINGS
    assert maps["KikoCharacterHintFemale"] is CharacterHintFemaleNode
    assert maps["KikoCharacterHintMale"] is CharacterHintMaleNode
    assert names["KikoCharacterHintFemale"] == "Character Hint (Female)"
    assert names["KikoCharacterHintMale"] == "Character Hint (Male)"
