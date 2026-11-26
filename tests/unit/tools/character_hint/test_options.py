import pytest

from kikotools.tools.character_hint import options

TABLES = {
    name: value
    for name, value in vars(options).items()
    if name.isupper() and isinstance(value, dict)
}


def test_tables_are_found():
    assert "MAKEUP" in TABLES and "FEMALE_BODY" in TABLES


@pytest.mark.parametrize("name", sorted(TABLES))
def test_table_is_non_empty(name):
    assert TABLES[name]


def test_heritage_is_non_empty():
    assert options.HERITAGE


@pytest.mark.parametrize("name", sorted(TABLES))
def test_no_label_is_unset(name):
    assert options.UNSET not in TABLES[name]


def test_heritage_has_no_unset():
    assert options.UNSET not in options.HERITAGE


@pytest.mark.parametrize("name", sorted(set(TABLES) - {"MAKEUP"}))
def test_no_phrase_is_empty(name):
    for label, phrase in TABLES[name].items():
        assert phrase.strip(), (name, label)


def test_no_makeup_part_is_empty_or_ends_with_punctuation():
    for label, (look, lips) in options.MAKEUP.items():
        for part in (look, lips):
            assert part.strip(), label
            assert part[-1] not in ".,;:!?", (label, part)


def test_word_bum_appears_nowhere():
    texts = list(options.HERITAGE)
    for table in TABLES.values():
        for label, phrase in table.items():
            texts.append(label)
            texts.extend(phrase if isinstance(phrase, tuple) else [phrase])
    assert not any("bum" in text.lower() for text in texts)


def test_flat_is_not_a_breast_size():
    assert "Flat" not in options.BREAST_SIZE
