"""Tests for LoRA Folder Batch node."""

import pytest
from unittest.mock import patch, MagicMock
import os
import tempfile
from kikotools.tools.xyz_helpers.lora_folder_batch import LoRAFolderBatchNode
from kikotools.tools.xyz_helpers.lora_folder_batch.logic import (
    scan_folder_for_loras,
    natural_sort,
    filter_loras_by_pattern,
    parse_strength_string,
    create_lora_params,
    create_lora_params_batched,
    get_lora_info,
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

    def test_natural_sort_with_paths(self):
        """Test natural sorting with subdirectory paths."""
        files = [
            "subdir2/model-10.safetensors",
            "model-2.safetensors",
            "subdir1/model-20.safetensors",
            "subdir1/model-3.safetensors",
            "model-100.safetensors",
        ]
        sorted_files = natural_sort(files)

        # Should handle mixed paths and numbers correctly
        assert len(sorted_files) == 5
        # Files with smaller numbers should come first within their directories
        assert sorted_files.index("model-2.safetensors") < sorted_files.index(
            "model-100.safetensors"
        )
        assert sorted_files.index("subdir1/model-3.safetensors") < sorted_files.index(
            "subdir1/model-20.safetensors"
        )

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

    def test_scan_folder_recursive(self):
        """Test recursive scanning of LoRA files in subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested directory structure
            os.makedirs(os.path.join(temp_dir, "flux", "style"))
            os.makedirs(os.path.join(temp_dir, "flux", "character"))
            os.makedirs(os.path.join(temp_dir, "sdxl"))

            # Create test files
            test_files = [
                os.path.join(temp_dir, "root-lora.safetensors"),
                os.path.join(temp_dir, "flux", "flux-lora.safetensors"),
                os.path.join(temp_dir, "flux", "style", "style-lora.safetensors"),
                os.path.join(temp_dir, "flux", "character", "char-lora.safetensors"),
                os.path.join(temp_dir, "sdxl", "sdxl-lora.safetensors"),
                os.path.join(temp_dir, "not-a-lora.txt"),  # Should be ignored
            ]

            for file_path in test_files:
                with open(file_path, "w") as f:
                    f.write("test")

            # Create a mock folder_paths module
            mock_folder_paths = MagicMock()
            mock_folder_paths.folder_names_and_paths = {"loras": [[temp_dir]]}

            # Mock the import
            import sys

            sys.modules["folder_paths"] = mock_folder_paths

            try:
                # Test scanning from root - should find all .safetensors files
                results = scan_folder_for_loras(".")
                assert len(results) == 5
                assert "root-lora.safetensors" in results
                assert "flux/flux-lora.safetensors" in results
                assert "flux/style/style-lora.safetensors" in results
                assert "flux/character/char-lora.safetensors" in results
                assert "sdxl/sdxl-lora.safetensors" in results
                assert "not-a-lora.txt" not in str(results)

                # Test scanning from subdirectory
                results = scan_folder_for_loras("flux")
                assert len(results) == 3
                assert "flux/flux-lora.safetensors" in results
                assert "flux/style/style-lora.safetensors" in results
                assert "flux/character/char-lora.safetensors" in results
            finally:
                # Clean up the mock
                if "folder_paths" in sys.modules:
                    del sys.modules["folder_paths"]


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
        assert "auto_batch" in optional
        assert "batch_size" in optional
        assert "batch_index" in optional

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
        assert LoRAFolderBatchNode.RETURN_TYPES == (
            "LORA_PARAMS",
            "STRING",
            "INT",
        )
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

    def test_create_lora_params_batched(self):
        """Test the batched LoRA params creation."""
        lora_files = [f"lora_{i:03d}.safetensors" for i in range(75)]
        strengths = [0.5, 1.0]

        # Test with batch size of 25
        batches = create_lora_params_batched(lora_files, strengths, "sequential", 25)

        assert len(batches) == 3  # 75 / 25 = 3 batches

        # Check first batch
        assert len(batches[0]["loras"]) == 25
        assert batches[0]["batch_info"]["index"] == 0
        assert batches[0]["batch_info"]["total"] == 3
        assert batches[0]["batch_info"]["start_idx"] == 0
        assert batches[0]["batch_info"]["end_idx"] == 25
        assert batches[0]["batch_info"]["size"] == 25

        # Check second batch
        assert len(batches[1]["loras"]) == 25
        assert batches[1]["batch_info"]["index"] == 1
        assert batches[1]["batch_info"]["start_idx"] == 25
        assert batches[1]["batch_info"]["end_idx"] == 50

        # Check third batch
        assert len(batches[2]["loras"]) == 25
        assert batches[2]["batch_info"]["index"] == 2
        assert batches[2]["batch_info"]["start_idx"] == 50
        assert batches[2]["batch_info"]["end_idx"] == 75

    def test_auto_batch_node_integration(self, node):
        """Test auto-batching in the node."""
        # Create mock LoRA files
        lora_files = [f"lora_{i:03d}.safetensors" for i in range(75)]

        with patch(
            "kikotools.tools.xyz_helpers.lora_folder_batch.node.validate_folder_path"
        ) as mock_validate:
            with patch(
                "kikotools.tools.xyz_helpers.lora_folder_batch.node.scan_folder_for_loras"
            ) as mock_scan:
                mock_validate.return_value = True
                mock_scan.return_value = lora_files

                # Test batch 0
                params, lora_list, count = node.batch_loras(
                    folder_path="test",
                    strength="1.0",
                    batch_mode="sequential",
                    auto_batch="enabled",
                    batch_size=25,
                    batch_index=0,
                )

                assert count == 25
                assert "Batch 1/3" in lora_list
                assert len(params["loras"]) == 25
                assert params["loras"][0] == "lora_000.safetensors"

                # Test batch 1
                params, lora_list, count = node.batch_loras(
                    folder_path="test",
                    strength="1.0",
                    batch_mode="sequential",
                    auto_batch="enabled",
                    batch_size=25,
                    batch_index=1,
                )

                assert count == 25
                assert "Batch 2/3" in lora_list
                assert params["loras"][0] == "lora_025.safetensors"

                # Test batch 2
                params, lora_list, count = node.batch_loras(
                    folder_path="test",
                    strength="1.0",
                    batch_mode="sequential",
                    auto_batch="enabled",
                    batch_size=25,
                    batch_index=2,
                )

                assert count == 25
                assert "Batch 3/3" in lora_list
                assert params["loras"][0] == "lora_050.safetensors"
