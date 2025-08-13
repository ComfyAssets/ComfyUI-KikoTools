"""Tests for LoRA Folder Batch node."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from kikotools.tools.xyz_helpers.lora_folder_batch import LoRAFolderBatchNode
from kikotools.tools.xyz_helpers.lora_folder_batch.logic import (
    scan_folder_for_loras,
    natural_sort,
    filter_loras_by_pattern,
    parse_strength_string,
    create_lora_params,
    get_lora_info,
    validate_folder_path,
)


class TestLoRAFolderBatchLogic:
    """Test the logic functions for LoRA Folder Batch."""

    def test_natural_sort(self):
        """Test natural sorting of filenames."""
        files = [
            "model-v1-000100.safetensors",
            "model-v1-000020.safetensors",
            "model-v1-000004.safetensors",
            "model-v1.safetensors",
        ]
        sorted_files = natural_sort(files)

        # Natural sort should put numbered epochs in order
        assert "000004" in sorted_files[0]
        assert "000020" in sorted_files[1]
        assert "000100" in sorted_files[2]
        # Base file could be first or last depending on implementation
        assert "model-v1.safetensors" in sorted_files

    def test_filter_loras_by_pattern(self):
        """Test filtering LoRAs by patterns."""
        files = [
            "model-v1.safetensors",
            "model-v2.safetensors",
            "test-model.safetensors",
            "backup-model.safetensors",
        ]

        # Test include pattern
        filtered = filter_loras_by_pattern(files, include_pattern="model-v")
        assert len(filtered) == 2
        assert "model-v1.safetensors" in filtered
        assert "model-v2.safetensors" in filtered

        # Test exclude pattern
        filtered = filter_loras_by_pattern(files, exclude_pattern="test|backup")
        assert len(filtered) == 2
        assert "test-model.safetensors" not in filtered
        assert "backup-model.safetensors" not in filtered

    def test_parse_strength_string_single(self):
        """Test parsing single strength value."""
        strengths = parse_strength_string("0.75")
        assert strengths == [0.75]

    def test_parse_strength_string_multiple(self):
        """Test parsing multiple strength values."""
        strengths = parse_strength_string("0.5, 0.75, 1.0")
        assert strengths == [0.5, 0.75, 1.0]

    def test_parse_strength_string_range(self):
        """Test parsing strength range."""
        strengths = parse_strength_string("0.5...1.0+0.25")
        assert strengths == [0.5, 0.75, 1.0]

        # Test default step
        strengths = parse_strength_string("0.8...1.0")
        assert len(strengths) == 3  # 0.8, 0.9, 1.0

    def test_parse_strength_string_empty(self):
        """Test parsing empty strength string."""
        strengths = parse_strength_string("")
        assert strengths == [1.0]

    def test_create_lora_params_sequential(self):
        """Test creating LORA_PARAMS in sequential mode."""
        loras = ["lora1.safetensors", "lora2.safetensors"]
        strengths = [0.5, 1.0]

        params = create_lora_params(loras, strengths, "sequential")

        assert params["loras"] == loras
        assert len(params["strengths"]) == 2
        assert params["strengths"][0] == [0.5]
        assert params["strengths"][1] == [1.0]

    def test_create_lora_params_combinatorial(self):
        """Test creating LORA_PARAMS in combinatorial mode."""
        loras = ["lora1.safetensors", "lora2.safetensors"]
        strengths = [0.5, 1.0]

        params = create_lora_params(loras, strengths, "combinatorial")

        assert params["loras"] == loras
        assert len(params["strengths"]) == 2
        assert params["strengths"][0] == [0.5, 1.0]
        assert params["strengths"][1] == [0.5, 1.0]

    def test_get_lora_info(self):
        """Test extracting info from LoRA filename."""
        info = get_lora_info("model-v8-000012.safetensors")
        assert info["epoch"] == 12
        assert "v8" in info["version"]

        info = get_lora_info("simple-model.safetensors")
        assert info["epoch"] is None
        assert info["version"] is None


class TestLoRAFolderBatchNode:
    """Test the LoRA Folder Batch node."""

    @pytest.fixture
    def node(self):
        """Create a node instance."""
        return LoRAFolderBatchNode()

    def test_input_types(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = LoRAFolderBatchNode.INPUT_TYPES()
        assert "required" in input_types
        assert "optional" in input_types

        required = input_types["required"]
        assert "folder_path" in required
        assert "strength" in required
        assert "batch_mode" in required

        optional = input_types["optional"]
        assert "include_pattern" in optional
        assert "exclude_pattern" in optional

    def test_batch_loras_empty_folder(self, node):
        """Test with empty folder."""
        with patch(
            "kikotools.tools.xyz_helpers.lora_folder_batch.node.validate_folder_path"
        ) as mock_validate:
            with patch(
                "kikotools.tools.xyz_helpers.lora_folder_batch.logic.scan_folder_for_loras"
            ) as mock_scan:
                mock_validate.return_value = True
                mock_scan.return_value = []

                result = node.batch_loras(
                    folder_path="test", strength="1.0", batch_mode="sequential"
                )

                assert result[0] == {"loras": [], "strengths": []}
                assert result[1] == ""
                assert result[2] == 0

    def test_batch_loras_with_files(self, node):
        """Test with LoRA files found."""
        with patch(
            "kikotools.tools.xyz_helpers.lora_folder_batch.node.validate_folder_path"
        ) as mock_validate:
            with patch(
                "kikotools.tools.xyz_helpers.lora_folder_batch.node.scan_folder_for_loras"
            ) as mock_scan:
                mock_validate.return_value = True
                mock_scan.return_value = [
                    "model-000004.safetensors",
                    "model-000008.safetensors",
                ]

                result = node.batch_loras(
                    folder_path="test", strength="1.0", batch_mode="sequential"
                )

                params, lora_list, count = result
                assert count == 2
                assert len(params["loras"]) == 2
                assert "model-000004" in lora_list
                assert "epoch 4" in lora_list

    def test_node_properties(self):
        """Test node properties."""
        assert LoRAFolderBatchNode.CATEGORY == "🫶 ComfyAssets/🧰 xyz-helpers"
        assert LoRAFolderBatchNode.FUNCTION == "batch_loras"
        assert LoRAFolderBatchNode.RETURN_TYPES == ("LORA_PARAMS", "STRING", "INT")
        assert LoRAFolderBatchNode.RETURN_NAMES == (
            "lora_params",
            "lora_list",
            "lora_count",
        )

    def test_is_changed(self):
        """Test IS_CHANGED method returns unique value."""
        result1 = LoRAFolderBatchNode.IS_CHANGED()
        import time

        time.sleep(0.01)
        result2 = LoRAFolderBatchNode.IS_CHANGED()
        assert result1 != result2
