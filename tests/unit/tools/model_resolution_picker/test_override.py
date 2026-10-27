import asyncio
import json
import logging
import os
import sys
import types
from pathlib import Path

import pytest

from kikotools.tools.model_resolution_picker import families, override
from kikotools.tools.model_resolution_picker.node import get_families


@pytest.fixture(autouse=True)
def fake_user_dir(tmp_path, monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "folder_paths",
        types.SimpleNamespace(get_user_directory=lambda: str(tmp_path)),
    )
    override._reset_cache()
    yield tmp_path
    override._reset_cache()


def write_override(tmp_path: Path, data) -> Path:
    path = tmp_path / "kikotools" / "model_resolutions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data))
    return path


def sdxl_entry(sizes):
    payload = families.families_payload()["families"]
    base = next(f for f in payload if f["label"] == "SDXL")
    return {**base, "sizes": {**base["sizes"], **sizes}}


def test_override_path_points_into_user_directory(tmp_path):
    assert override.override_path() == tmp_path / "kikotools" / "model_resolutions.json"


def test_override_path_none_without_folder_paths(monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", None)
    assert override.override_path() is None
    assert override.current_table()[1] == []


def test_override_path_none_without_get_user_directory(monkeypatch):
    monkeypatch.setitem(sys.modules, "folder_paths", types.SimpleNamespace())
    assert override.override_path() is None


def test_no_file_returns_shipped_data():
    data, warnings = override.current_table()
    assert data is families.SHIPPED_DATA
    assert warnings == []


def test_override_replaces_family_sizes(tmp_path):
    entry = sdxl_entry({"1:1": [[1024, 1024], [1280, 1280]]})
    write_override(tmp_path, {"families": [entry]})
    assert families.resolve_family("SDXL").sizes["1:1"] == ((1024, 1024), (1280, 1280))
    shipped = next(f for f in families.FAMILIES if f.label == "SDXL")
    assert shipped.sizes["1:1"] == ((1024, 1024),)


def test_new_family_is_appended_and_resolvable(tmp_path):
    entry = {**sdxl_entry({"1:1": [[1024, 1024]]}), "label": "My Model"}
    write_override(tmp_path, {"families": [entry]})
    labels = [f["label"] for f in families.families_payload()["families"]]
    assert labels[-1] == "My Model"
    assert labels[:-1] == families.family_labels()
    assert families.resolve_family("My Model").label == "My Model"


def test_remove_hides_family(tmp_path):
    write_override(tmp_path, {"remove": ["SD 1.5"]})
    labels = [f["label"] for f in families.families_payload()["families"]]
    assert "SD 1.5" not in labels
    assert families.resolve_family("SD 1.5") is None


def test_default_is_replaced(tmp_path):
    write_override(tmp_path, {"default": "Illustrious XL"})
    assert families.families_payload()["default"] == "Illustrious XL"


def test_top_level_chips_and_version_are_ignored(tmp_path):
    write_override(tmp_path, {"version": 99, "chips": ["1:1"], "mirror": {}})
    data, warnings = override.current_table()
    assert warnings == []
    assert data["chips"] == families.SHIPPED_DATA["chips"]
    assert data["version"] == families.SHIPPED_DATA["version"]


def test_merge_never_mutates_inputs():
    shipped = json.loads(json.dumps(families.SHIPPED_DATA))
    snapshot = json.loads(json.dumps(shipped))
    ov = {"families": [sdxl_entry({"1:1": [[1024, 1024]]})], "remove": ["SD 1.5"]}
    ov_snapshot = json.loads(json.dumps(ov))
    merged = override.merge_override(shipped, ov)
    merged["families"][0]["label"] = "x"
    assert shipped == snapshot
    assert ov == ov_snapshot


@pytest.mark.parametrize(
    "bad",
    [
        {"families": "nope"},
        {"families": [1]},
        {"families": [{"label": 3}]},
        {"remove": "SD 1.5"},
        {"remove": [1]},
        {"default": 5},
    ],
)
def test_merge_rejects_malformed_override(bad):
    with pytest.raises(ValueError):
        override.merge_override(families.SHIPPED_DATA, bad)


def test_invalid_json_is_ignored_with_one_warning(tmp_path, caplog):
    path = write_override(tmp_path, "{not json")
    with caplog.at_level(logging.WARNING):
        data, warnings = override.current_table()
    assert data is families.SHIPPED_DATA
    assert len(warnings) == 1
    assert warnings[0].startswith("Override ignored: ")
    assert str(path) in warnings[0]
    assert warnings[0] in caplog.text


def test_non_object_json_is_ignored(tmp_path):
    write_override(tmp_path, "[1, 2]")
    data, warnings = override.current_table()
    assert data is families.SHIPPED_DATA
    assert warnings[0].startswith("Override ignored: ")


def test_invariant_break_ignores_whole_override(tmp_path):
    entry = sdxl_entry({"1:1": [[1000, 1000]]})
    write_override(tmp_path, {"families": [entry], "remove": ["SD 1.5"]})
    data, warnings = override.current_table()
    assert data is families.SHIPPED_DATA
    assert len(warnings) == 1 and warnings[0].startswith("Override ignored: ")
    assert "SDXL" in warnings[0]
    assert families.resolve_family("SD 1.5") is not None
    assert families.resolve_family("SDXL").sizes["1:1"] != ((1000, 1000),)


def test_edit_with_newer_mtime_is_picked_up(tmp_path):
    path = write_override(tmp_path, {"remove": ["SD 1.5"]})
    assert families.resolve_family("SD 1.5") is None
    path.write_text(json.dumps({"remove": ["Anima"]}))
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert families.resolve_family("SD 1.5") is not None
    assert families.resolve_family("Anima") is None


def test_result_is_cached_until_mtime_changes(tmp_path):
    write_override(tmp_path, {"remove": ["SD 1.5"]})
    first, _ = override.current_table()
    second, _ = override.current_table()
    assert first is second


def test_path_change_invalidates_cache(tmp_path, monkeypatch):
    write_override(tmp_path, {"remove": ["SD 1.5"]})
    assert override.current_table()[0] is not families.SHIPPED_DATA
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setitem(
        sys.modules,
        "folder_paths",
        types.SimpleNamespace(get_user_directory=lambda: str(other)),
    )
    assert override.current_table()[0] is families.SHIPPED_DATA


def test_route_payload_includes_warnings(tmp_path):
    response = asyncio.run(get_families(None))
    assert json.loads(response.body)["warnings"] == []
    write_override(tmp_path, "{bad")
    response = asyncio.run(get_families(None))
    warnings = json.loads(response.body)["warnings"]
    assert len(warnings) == 1 and warnings[0].startswith("Override ignored:")


def test_deeply_nested_json_is_ignored_without_raising(tmp_path):
    write_override(tmp_path, "[" * 100000 + "]" * 100000)
    data, warnings = override.current_table()
    assert data is families.SHIPPED_DATA
    assert len(warnings) == 1 and warnings[0].startswith("Override ignored: ")
    assert families.families_payload()["warnings"] == warnings


def test_remove_wins_over_families_with_the_same_label(tmp_path):
    entry = sdxl_entry({"1:1": [[1024, 1024], [1280, 1280]]})
    entry = {**entry, "label": "Illustrious XL"}
    write_override(tmp_path, {"families": [entry], "remove": ["Illustrious XL"]})
    labels = [f["label"] for f in families.families_payload()["families"]]
    assert "Illustrious XL" not in labels
    assert override.current_table()[1] == []


def test_default_naming_a_removed_family_ignores_override(tmp_path):
    write_override(tmp_path, {"remove": ["Anima"], "default": "Anima"})
    data, warnings = override.current_table()
    assert data is families.SHIPPED_DATA
    assert len(warnings) == 1 and "Anima" in warnings[0]
