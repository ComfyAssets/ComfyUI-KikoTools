import copy
import json
import logging
import os
import sys
import types
from pathlib import Path

import pytest

from kikotools.tools.character_hint import options
from kikotools.tools.character_hint.options import UNSET, apply_override

HERE = Path(options.__file__).parent


def base():
    return copy.deepcopy(options.load_shipped())


def test_shipped_has_exactly_the_table_names():
    assert list(options.load_shipped()) == list(options.TABLE_NAMES)


def test_shipped_tables_are_clean():
    for name, table in options.load_shipped().items():
        assert table, name
        for label, phrase in table.items():
            assert label.strip() and label != UNSET, (name, label)
            if name == "makeup":
                assert set(phrase) == {"look", "lips"}, label
                for part in phrase.values():
                    assert part.strip(), label
                    assert part[-1] not in ".,;:!?", (label, part)
            else:
                assert isinstance(phrase, str) and phrase.strip(), (name, label)


def test_word_bum_appears_nowhere():
    text = (HERE / "options.json").read_text(encoding="utf-8").lower()
    assert "bum" not in text


def test_flat_is_not_a_breast_size():
    assert "Flat" not in options.load_shipped()["breast_size"]


def test_makeup_has_40_styles():
    assert len(options.load_shipped()["makeup"]) == 40


def test_heritage_phrase_is_label():
    for label, phrase in options.load_shipped()["heritage"].items():
        assert label == phrase


def test_broken_shipped_file_raises(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"heritage": {}}')
    monkeypatch.setattr(options, "SHIPPED_PATH", bad)
    options._reset_cache()
    with pytest.raises(ValueError):
        options.load_shipped()


def test_example_file_applies_without_problems():
    example = json.loads((HERE / "character_hint.example.json").read_text("utf-8"))
    tables, problems = apply_override(options.load_shipped(), example)
    assert problems == []
    assert "Festival glitter" in tables["makeup"]
    assert "Maori" in tables["heritage"]
    assert tables["hair_color"]["Copper"] == "bright copper hair"
    assert "Sleeve tattoo" not in tables["tattoo"]


# apply_override


def test_add_appends_last():
    tables, problems = apply_override(base(), {"nose": {"Hawk": "a hawk nose"}})
    assert problems == []
    assert list(tables["nose"])[-1] == "Hawk"
    assert tables["nose"]["Hawk"] == "a hawk nose"


def test_replace_keeps_position():
    original = base()
    label = list(original["nose"])[0]
    tables, problems = apply_override(original, {"nose": {label: "a new nose"}})
    assert problems == []
    assert list(tables["nose"]) == list(original["nose"])
    assert tables["nose"][label] == "a new nose"


def test_remove():
    original = base()
    label = list(original["nose"])[0]
    tables, problems = apply_override(original, {"nose": {label: None}})
    assert problems == []
    assert label not in tables["nose"]


def test_makeup_add_replace_remove():
    original = base()
    first, second = list(original["makeup"])[:2]
    entry = {"look": "a look", "lips": "red lips"}
    tables, problems = apply_override(
        original, {"makeup": {"New": entry, first: entry, second: None}}
    )
    assert problems == []
    assert list(tables["makeup"])[-1] == "New"
    assert tables["makeup"][first] == entry
    assert list(tables["makeup"])[0] == first
    assert second not in tables["makeup"]


def test_base_is_not_mutated():
    original = base()
    snapshot = copy.deepcopy(original)
    apply_override(original, {"nose": {"X": "x"}, "makeup": {"Y": None}})
    assert original == snapshot


VALID = {"dimples": {"Good": "a good dimple"}}


@pytest.mark.parametrize(
    "bad",
    [
        {"nose": "text"},
        {"nose": ["a"]},
        {"unknown_table": {"A": "a"}},
        {"nose": {"": "x"}},
        {"nose": {"   ": "x"}},
        {"nose": {UNSET: "x"}},
        {"nose": {"A": ""}},
        {"nose": {"A": "   "}},
        {"nose": {"A": 5}},
        {"nose": {"A": ["x"]}},
        {"nose": {"Missing label": None}},
        {"makeup": {"A": "text"}},
        {"makeup": {"A": {"look": "x"}}},
        {"makeup": {"A": {"lips": "x"}}},
        {"makeup": {"A": {"look": "", "lips": "x"}}},
        {"makeup": {"A": {"look": "x", "lips": 3}}},
        {"makeup": {"Missing": None}},
    ],
)
def test_bad_entry_is_skipped_with_a_problem(bad):
    original = base()
    tables, problems = apply_override(original, {**bad, **VALID})
    assert len(problems) == 1
    assert tables["dimples"]["Good"] == "a good dimple"
    for name in ("makeup", "heritage"):
        assert tables[name] == original[name]


def test_non_string_label_is_a_problem():
    # JSON keys are always strings, so call the pure function with a real one.
    tables, problems = apply_override(base(), {"nose": {1: "x", "Good": "g"}})
    assert len(problems) == 1 and "Good" in tables["nose"]


def test_problem_mentions_table_and_label():
    _, problems = apply_override(base(), {"nose": {"Missing label": None}})
    assert "nose" in problems[0] and "Missing label" in problems[0]


def test_emptying_a_table_is_refused():
    original = base()
    removal = {label: None for label in original["bangs"]}
    tables, problems = apply_override(original, {"bangs": removal, **VALID})
    assert tables["bangs"] == original["bangs"]
    assert len(problems) == 1 and "bangs" in problems[0]
    assert tables["dimples"]["Good"] == "a good dimple"


def test_non_object_top_level_gives_a_problem():
    original = base()
    tables, problems = apply_override(original, ["x"])
    assert tables == original and len(problems) == 1


# tables()


def test_no_user_file_gives_shipped(fake_user_dir):
    assert options.tables() == options.load_shipped()


def test_no_folder_paths_gives_shipped(monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", None)
    assert options.tables() == options.load_shipped()


def test_folder_paths_without_user_directory_gives_shipped(monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", types.SimpleNamespace())
    assert options.tables() == options.load_shipped()


def test_valid_user_file_is_applied(write_user_file):
    write_user_file({"nose": {"Hawk": "a hawk nose"}})
    assert options.tables()["nose"]["Hawk"] == "a hawk nose"
    assert "Hawk" not in options.load_shipped()["nose"]


def test_invalid_json_warns_once_and_uses_shipped(write_user_file, caplog):
    path = write_user_file("{not json")
    with caplog.at_level(logging.WARNING):
        assert options.tables() == options.load_shipped()
        options.tables()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert str(path) in warnings[0].getMessage()


def test_non_object_json_warns(write_user_file, caplog):
    write_user_file("[1, 2]")
    with caplog.at_level(logging.WARNING):
        assert options.tables() == options.load_shipped()
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_problems_are_logged_one_line_each(write_user_file, caplog):
    path = write_user_file(
        {"nose": {"Gone": None, "Good": "a good nose"}, "nope": {"A": "a"}}
    )
    with caplog.at_level(logging.WARNING):
        result = options.tables()
    lines = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(lines) == 2
    assert all(str(path) in line for line in lines)
    assert result["nose"]["Good"] == "a good nose"


def test_unreadable_file_warns(write_user_file, caplog):
    path = write_user_file({})
    path.write_bytes(b"\xff\xfe\x00bad")
    with caplog.at_level(logging.WARNING):
        assert options.tables() == options.load_shipped()
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


def test_edited_file_is_picked_up(write_user_file):
    path = write_user_file({"nose": {"Hawk": "a hawk nose"}})
    assert "Hawk" in options.tables()["nose"]
    path.write_text(json.dumps({"nose": {"Eagle": "an eagle nose"}}))
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000_000))
    result = options.tables()["nose"]
    assert "Eagle" in result and "Hawk" not in result


def test_deleted_file_goes_back_to_shipped(write_user_file):
    path = write_user_file({"nose": {"Hawk": "a hawk nose"}})
    assert "Hawk" in options.tables()["nose"]
    path.unlink()
    assert options.tables() == options.load_shipped()


NEW_TABLES = (
    "facial_structure",
    "eyebrows",
    "eyewear",
    "hair_texture",
    "head_angle",
    "gaze",
)


def test_new_tables_are_shipped_and_listed():
    assert len(options.TABLE_NAMES) == 36
    for name in NEW_TABLES:
        assert name in options.TABLE_NAMES
        assert options.load_shipped()[name]


def test_new_table_sizes():
    shipped = options.load_shipped()
    sizes = {name: len(shipped[name]) for name in NEW_TABLES}
    assert sizes == {
        "facial_structure": 4,
        "eyebrows": 2,
        "eyewear": 5,
        "hair_texture": 4,
        "head_angle": 9,
        "gaze": 5,
    }


def test_added_options_and_changed_phrase():
    shipped = options.load_shipped()
    assert shipped["facial_hair"]["Clean shaven"] == (
        "a clean-shaven upper lip, cheeks, jaw and chin, "
        "with no beard, mustache or stubble"
    )
    assert shipped["tattoo"]["No tattoos"] == "no tattoos"
    assert list(shipped["freckles"])[-1] == "No freckles"
    assert list(shipped["bangs"])[-1] == "No bangs"
    labels = list(shipped["female_hair_style"])
    assert labels[labels.index("Single braid") + 1] == "Three-strand braid"
    assert list(shipped["face_shape"])[-2:] == ["Square", "Heart-shaped"]
    assert list(shipped["nose"])[-1] == "Upturned"
    assert list(shipped["expression"])[-3:] == ["Sad", "Tired", "Relieved"]
