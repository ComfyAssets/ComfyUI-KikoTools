"""Hardening tests for LoRA Folder Batch (bad input, containment, IS_CHANGED)."""

import math
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from kikotools.tools.xyz_helpers.lora_folder_batch import LoRAFolderBatchNode
from kikotools.tools.xyz_helpers.lora_folder_batch.logic import (
    MAX_STRENGTH_VALUES,
    create_lora_params,
    parse_strength_string,
    scan_folder_for_loras,
    sort_lora_files,
    validate_folder_path,
)


def _touch(path, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("x")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def _fake_folder_paths(*roots):
    fp = MagicMock()
    fp.folder_names_and_paths = {"loras": [list(roots)]}
    return patch.dict(sys.modules, {"folder_paths": fp})


class TestParseStrengthErrors:
    @pytest.mark.parametrize("bad", ["0.5...1.0+0", "0.5...1.0+-0.1", "0.5...1.0+-1"])
    def test_non_positive_step_raises(self, bad):
        with pytest.raises(ValueError, match="step"):
            parse_strength_string(bad)

    def test_reversed_range_raises(self):
        with pytest.raises(ValueError, match="reversed|start"):
            parse_strength_string("1.0...0.5")

    @pytest.mark.parametrize(
        "bad", ["abc", "0.5, x", "a...b", "1...2...3", "1...2+1+1", "1...2+x", "nan"]
    )
    def test_malformed_raises(self, bad):
        with pytest.raises(ValueError):
            parse_strength_string(bad)

    def test_infinite_raises(self):
        with pytest.raises(ValueError):
            parse_strength_string("0...inf")

    def test_too_many_values_raises(self):
        with pytest.raises(ValueError, match=str(MAX_STRENGTH_VALUES)):
            parse_strength_string("0...1000+0.0001")

    def test_exactly_cap_is_allowed(self):
        values = parse_strength_string(f"0...{MAX_STRENGTH_VALUES - 1}+1")
        assert len(values) == MAX_STRENGTH_VALUES

    def test_only_commas_raises(self):
        with pytest.raises(ValueError):
            parse_strength_string(" , ,")

    def test_valid_ranges_still_work(self):
        assert parse_strength_string("0.5...1.0+0.25") == [0.5, 0.75, 1.0]
        assert parse_strength_string("0.8...1.0") == [0.8, 0.9, 1.0]
        assert parse_strength_string("1.0...1.0") == [1.0]
        assert parse_strength_string("") == [1.0]

    def test_create_lora_params_rejects_empty_strengths(self):
        with pytest.raises(ValueError, match="strength"):
            create_lora_params(["a.safetensors"], [], "sequential")


class TestScanContainment:
    def test_sibling_directory_with_shared_prefix_not_contained(self, tmp_path):
        loras = tmp_path / "loras"
        backup = tmp_path / "loras_backup"
        _touch(str(loras / "a.safetensors"))
        _touch(str(backup / "b.safetensors"))
        with _fake_folder_paths(str(loras)):
            result = scan_folder_for_loras(str(backup))
        # Not inside the loras root, so names are relative to the scanned folder
        assert result == ["b.safetensors"]

    def test_absolute_path_inside_second_root(self, tmp_path):
        r1, r2 = tmp_path / "r1", tmp_path / "r2"
        _touch(str(r1 / "a.safetensors"))
        _touch(str(r2 / "sub" / "b.safetensors"))
        with _fake_folder_paths(str(r1), str(r2)):
            result = scan_folder_for_loras(str(r2 / "sub"))
        assert result == ["sub/b.safetensors"]

    def test_relative_searches_all_roots(self, tmp_path):
        r1, r2 = tmp_path / "r1", tmp_path / "r2"
        _touch(str(r1 / "flux" / "a.safetensors"))
        _touch(str(r2 / "flux" / "b.safetensors"))
        _touch(str(r2 / "only2" / "c.safetensors"))
        with _fake_folder_paths(str(r1), str(r2)):
            assert scan_folder_for_loras("flux") == [
                "flux/a.safetensors",
                "flux/b.safetensors",
            ]
            assert scan_folder_for_loras("only2") == ["only2/c.safetensors"]

    def test_relative_traversal_is_rejected(self, tmp_path):
        root = tmp_path / "loras"
        _touch(str(root / "a.safetensors"))
        _touch(str(tmp_path / "secret" / "s.safetensors"))
        with _fake_folder_paths(str(root)):
            assert scan_folder_for_loras("../secret") == []

    def test_symlink_escape_not_treated_as_contained(self, tmp_path):
        root = tmp_path / "loras"
        outside = tmp_path / "outside"
        _touch(str(outside / "o.safetensors"))
        root.mkdir()
        os.symlink(str(outside), str(root / "link"))
        with _fake_folder_paths(str(root)):
            assert scan_folder_for_loras("link") == []

    def test_missing_folder_returns_empty(self, tmp_path):
        with _fake_folder_paths(str(tmp_path)):
            assert scan_folder_for_loras("nope") == []

    def test_validate_folder_path_uses_all_roots(self, tmp_path):
        r1, r2 = tmp_path / "r1", tmp_path / "r2"
        r1.mkdir()
        (r2 / "flux").mkdir(parents=True)
        with _fake_folder_paths(str(r1), str(r2)):
            assert validate_folder_path("flux") is True
            assert validate_folder_path(".") is True
            assert validate_folder_path("missing") is False
            assert validate_folder_path(str(r2)) is True

    def test_validate_folder_path_no_roots(self):
        with _fake_folder_paths():
            assert validate_folder_path("flux") is False


class TestSortLoraFiles:
    def test_orders(self):
        files = ["b10.safetensors", "b2.safetensors", "a.safetensors"]
        assert sort_lora_files(files, "alphabetical")[0] == "a.safetensors"
        assert sort_lora_files(files, "oldest")[0] == "a.safetensors"
        assert sort_lora_files(files, "newest")[-1] == "a.safetensors"
        assert sort_lora_files(files, "natural")[1] == "b2.safetensors"
        assert sort_lora_files(files, "other") == files


class TestIsChanged:
    def _changed(self, **kw):
        base = dict(folder_path="flux", strength="1.0", batch_mode="sequential")
        base.update(kw)
        return LoRAFolderBatchNode.IS_CHANGED(**base)

    def test_stable_when_nothing_changes(self, tmp_path):
        _touch(str(tmp_path / "flux" / "a.safetensors"), 1000)
        with _fake_folder_paths(str(tmp_path)):
            assert self._changed() == self._changed()

    def test_changes_when_file_added(self, tmp_path):
        _touch(str(tmp_path / "flux" / "a.safetensors"), 1000)
        with _fake_folder_paths(str(tmp_path)):
            before = self._changed()
            _touch(str(tmp_path / "flux" / "b.safetensors"), 1000)
            assert self._changed() != before

    def test_changes_when_mtime_changes(self, tmp_path):
        p = str(tmp_path / "flux" / "a.safetensors")
        _touch(p, 1000)
        with _fake_folder_paths(str(tmp_path)):
            before = self._changed()
            os.utime(p, (2000, 2000))
            assert self._changed() != before

    def test_changes_with_inputs(self, tmp_path):
        _touch(str(tmp_path / "flux" / "a.safetensors"), 1000)
        with _fake_folder_paths(str(tmp_path)):
            assert self._changed(strength="0.5") != self._changed()
            assert self._changed(include_pattern="a") != self._changed()

    def test_pattern_filters_fingerprint(self, tmp_path):
        _touch(str(tmp_path / "flux" / "a.safetensors"), 1000)
        _touch(str(tmp_path / "flux" / "skip.safetensors"), 1000)
        with _fake_folder_paths(str(tmp_path)):
            before = self._changed(exclude_pattern="skip")
            os.utime(str(tmp_path / "flux" / "skip.safetensors"), (5, 5))
            assert self._changed(exclude_pattern="skip") == before

    def test_not_nan_or_time_based(self, tmp_path):
        with _fake_folder_paths(str(tmp_path)):
            value = self._changed()
        assert not (isinstance(value, float) and math.isnan(value))
        assert isinstance(value, str)

    def test_missing_folder_still_returns_string(self, tmp_path):
        with _fake_folder_paths(str(tmp_path)):
            assert isinstance(self._changed(folder_path="nope"), str)


class TestNodeBadStrength:
    def test_bad_strength_surfaces_error(self):
        node = LoRAFolderBatchNode()
        with (
            patch(
                "kikotools.tools.xyz_helpers.lora_folder_batch.node.validate_folder_path",
                return_value=True,
            ),
            patch(
                "kikotools.tools.xyz_helpers.lora_folder_batch.node.scan_folder_for_loras",
                return_value=["a.safetensors"],
            ),
        ):
            with pytest.raises(ValueError, match="step"):
                node.batch_loras("x", "0.5...1.0+0", "sequential")


NODE = "kikotools.tools.xyz_helpers.lora_folder_batch.node"


def _run_node(files, **kwargs):
    node = LoRAFolderBatchNode()
    args = dict(folder_path="x", strength="1.0", batch_mode="sequential")
    args.update(kwargs)
    with (
        patch(f"{NODE}.validate_folder_path", return_value=True),
        patch(f"{NODE}.scan_folder_for_loras", return_value=files),
    ):
        return node.batch_loras(**args)


class TestNodeBehaviour:
    FILES = [f"m-{i:06d}.safetensors" for i in range(1, 8)]

    def test_invalid_folder_raises(self):
        node = LoRAFolderBatchNode()
        with patch(f"{NODE}.validate_folder_path", return_value=False):
            with pytest.raises(ValueError, match="Invalid or inaccessible"):
                node.batch_loras("nope", "1.0", "sequential")

    def test_filters_applied(self):
        params, text, count = _run_node(
            self.FILES, include_pattern="00000[1-3]", exclude_pattern="000002"
        )
        assert count == 2
        assert params["loras"] == [self.FILES[0], self.FILES[2]]

    def test_filter_removes_everything(self):
        params, text, count = _run_node(self.FILES, include_pattern="zzz")
        assert (params, text, count) == ({"loras": [], "strengths": []}, "", 0)

    def test_max_loras_limits(self):
        _, _, count = _run_node(self.FILES, max_loras=3)
        assert count == 3

    def test_sort_order_newest(self):
        params, _, _ = _run_node(self.FILES, sort_order="newest")
        assert params["loras"][0] == self.FILES[-1]

    def test_combinatorial_strengths(self):
        params, _, count = _run_node(
            self.FILES[:2], strength="0.5,1.0", batch_mode="combinatorial"
        )
        assert params["strengths"] == [[0.5, 1.0], [0.5, 1.0]]
        assert count == 2

    def test_many_combinations_warning_path(self):
        files = [f"l{i}.safetensors" for i in range(120)]
        _, _, count = _run_node(files, max_loras=500)
        assert count == 120

    def test_auto_batch_selects_batch(self):
        params, text, count = _run_node(
            self.FILES, auto_batch="enabled", batch_size=3, batch_index=1
        )
        assert count == 3
        assert params["loras"] == self.FILES[3:6]
        assert text.startswith("=== Batch 2/3 (LoRAs 4-6) ===")

    def test_auto_batch_index_out_of_range_uses_first(self):
        params, text, _ = _run_node(
            self.FILES, auto_batch="enabled", batch_size=3, batch_index=9
        )
        assert params["loras"] == self.FILES[:3]
        assert "Batch 1/3" in text

    def test_files_without_epoch_listed_by_name(self):
        _, text, _ = _run_node(["plain.safetensors"])
        assert text == "plain"


class TestGetLoraFolders:
    def test_lists_subfolders(self, tmp_path):
        (tmp_path / "flux" / "style").mkdir(parents=True)
        with _fake_folder_paths(str(tmp_path)):
            from kikotools.tools.xyz_helpers.lora_folder_batch.logic import (
                get_lora_folders,
            )

            folders = get_lora_folders()
        assert folders[0] == "."
        assert set(folders) == {".", "flux", os.path.join("flux", "style")}

    def test_falls_back_without_roots(self):
        from kikotools.tools.xyz_helpers.lora_folder_batch.logic import (
            get_lora_folders,
        )

        with patch.dict(
            sys.modules, {"folder_paths": MagicMock(folder_names_and_paths={})}
        ):
            assert get_lora_folders()[0] == "."
