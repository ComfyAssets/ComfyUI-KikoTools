"""Tests for the shared model-folder scanner."""

import os
import sys
from unittest.mock import MagicMock, patch

from kikotools.base.model_folders import scan_model_entries, natural_sort


def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("x")


def _fake_folder_paths(key, *roots):
    fp = MagicMock()
    fp.folder_names_and_paths = {key: [list(roots)]}
    return patch.dict(sys.modules, {"folder_paths": fp})


class TestScanModelEntries:
    def test_scans_the_requested_folder_key(self, tmp_path):
        ckpt = tmp_path / "checkpoints"
        _touch(str(ckpt / "Illustrious" / "b_v2.safetensors"))
        _touch(str(ckpt / "Illustrious" / "a_v10.safetensors"))
        _touch(str(ckpt / "Illustrious" / "notes.md"))
        with _fake_folder_paths("checkpoints", str(ckpt)):
            entries = scan_model_entries("Illustrious", "checkpoints")
        assert [name for name, _ in entries] == [
            "Illustrious/a_v10.safetensors",
            "Illustrious/b_v2.safetensors",
        ]
        assert entries[0][1] == str(ckpt / "Illustrious" / "a_v10.safetensors")

    def test_relative_folder_escaping_the_root_is_ignored(self, tmp_path):
        ckpt = tmp_path / "checkpoints"
        _touch(str(tmp_path / "outside" / "x.safetensors"))
        with _fake_folder_paths("checkpoints", str(ckpt)):
            assert scan_model_entries("../outside", "checkpoints") == []

    def test_unknown_key_returns_empty(self, tmp_path):
        with _fake_folder_paths("loras", str(tmp_path)):
            assert scan_model_entries(".", "checkpoints") == []


def test_natural_sort_orders_numbers_numerically():
    assert natural_sort(["v10", "v2", "v1"]) == ["v1", "v2", "v10"]


def test_natural_sort_ignores_case():
    assert natural_sort(["IllustrijGEN3", "aij_v10", "Illustrijv21", "animij_v6"]) == [
        "aij_v10",
        "animij_v6",
        "IllustrijGEN3",
        "Illustrijv21",
    ]
