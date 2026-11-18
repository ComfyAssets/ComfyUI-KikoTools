"""The system prompts that ship with the Kiko Prompt Enhancer."""

import pytest

from kikotools.tools.prompt_enhancer import library

MAX_WORDS = {
    "sdxl-realism": 60,
    "illustrious": 60,
    "anima": 120,
    "flux2-klein": 120,
    "z-image": 250,
    "moss": 500,
    "krea2": 150,
    "qwen-image": 520,
    "wan-t2v": 200,
    "wan-i2v": 100,
}
POLICY_PHRASES = (
    "clothing covers",
    "cannot generate",
    "refuse",
    "inappropriate",
    "sanitize",
)


def shipped(stem):
    path = library.SHIPPED_DIR / f"{stem}.md"
    return library.parse_prompt_file(
        stem, path.read_text(encoding="utf-8"), path, False
    )


def test_every_expected_prompt_ships():
    stems = {path.stem for path in library.SHIPPED_DIR.glob("*.md")}
    assert set(MAX_WORDS) <= stems


@pytest.mark.parametrize("stem", sorted(MAX_WORDS))
def test_max_words_matches_table(stem):
    assert shipped(stem).max_words == MAX_WORDS[stem]


@pytest.mark.parametrize("stem", sorted(MAX_WORDS))
def test_shared_rules_present(stem):
    text = shipped(stem).text
    assert "exactly as written" in text
    assert "double quotes" in text
    assert "preamble" in text


@pytest.mark.parametrize("stem", sorted(MAX_WORDS))
def test_every_prompt_has_image_section(stem):
    assert shipped(stem).image_text


def test_wan_i2v_has_image_section():
    image_text = shipped("wan-i2v").image_text.lower()
    assert "already shows" in image_text


@pytest.mark.parametrize("stem", sorted(MAX_WORDS))
def test_no_content_policy_phrases(stem):
    prompt = shipped(stem)
    text = (prompt.text + "\n" + prompt.image_text).lower()
    for phrase in POLICY_PHRASES:
        assert phrase not in text
