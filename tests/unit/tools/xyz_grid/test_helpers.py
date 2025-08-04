"""Tests for XYZ grid helper utilities."""

import pytest
from kikotools.tools.xyz_grid.utils.constants import AxisType
from kikotools.tools.xyz_grid.utils.helpers import (
    parse_value_string,
    generate_axis_labels,
    calculate_grid_dimensions,
    create_unique_id
)


class TestParseValueString:
    """Test value string parsing."""
    
    def test_parse_comma_separated_strings(self):
        """Test parsing comma-separated string values."""
        result = parse_value_string("model1.ckpt, model2.safetensors, model3.pt", AxisType.MODEL)
        assert result == ["model1.ckpt", "model2.safetensors", "model3.pt"]
    
    def test_parse_comma_separated_numbers(self):
        """Test parsing comma-separated numeric values."""
        result = parse_value_string("5, 7.5, 10", AxisType.CFG_SCALE)
        assert result == [5.0, 7.5, 10.0]
        
        result = parse_value_string("20, 30, 40", AxisType.STEPS)
        assert result == [20, 30, 40]
    
    def test_parse_range_syntax(self):
        """Test parsing range syntax."""
        # Float range
        result = parse_value_string("5:10:1", AxisType.CFG_SCALE)
        assert result == [5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        
        # Integer range
        result = parse_value_string("10:30:10", AxisType.STEPS)
        assert result == [10, 20, 30]
        
        # Two-part range (default step)
        result = parse_value_string("1:5", AxisType.CLIP_SKIP)
        assert result == [1, 2, 3, 4, 5]
    
    def test_parse_empty_string(self):
        """Test parsing empty or whitespace strings."""
        assert parse_value_string("", AxisType.MODEL) == []
        assert parse_value_string("   ", AxisType.MODEL) == []
        assert parse_value_string("\n\t", AxisType.MODEL) == []
    
    def test_parse_single_value(self):
        """Test parsing single values."""
        assert parse_value_string("euler", AxisType.SAMPLER) == ["euler"]
        assert parse_value_string("7.5", AxisType.CFG_SCALE) == [7.5]
        assert parse_value_string("42", AxisType.SEED) == [42]


class TestGenerateAxisLabels:
    """Test label generation."""
    
    def test_basic_labels(self):
        """Test basic label generation."""
        values = ["euler", "dpm++", "ddim"]
        labels = generate_axis_labels(values, AxisType.SAMPLER)
        assert labels == ["euler", "dpm++", "ddim"]
    
    def test_labels_with_prefix(self):
        """Test labels with prefix."""
        values = [5, 10, 15]
        labels = generate_axis_labels(values, AxisType.CFG_SCALE, prefix="CFG=")
        assert labels == ["CFG=5", "CFG=10", "CFG=15"]
    
    def test_model_labels_strip_extension(self):
        """Test model labels strip file extensions."""
        values = ["model1.ckpt", "model2.safetensors", "checkpoint.pt"]
        labels = generate_axis_labels(values, AxisType.MODEL)
        assert labels == ["model1", "model2", "checkpoint"]
    
    def test_prompt_labels_truncate(self):
        """Test prompt labels truncate long text."""
        long_prompt = "This is a very long prompt that should be truncated for display purposes"
        values = [long_prompt, "Short prompt"]
        labels = generate_axis_labels(values, AxisType.PROMPT)
        assert len(labels[0]) <= 33  # 30 chars + "..."
        assert labels[1] == "Short prompt"


class TestCalculateGridDimensions:
    """Test grid dimension calculations."""
    
    def test_2d_grid(self):
        """Test 2D grid calculations."""
        result = calculate_grid_dimensions(3, 4)
        assert result == {
            "total_images": 12,
            "grids_count": 1,
            "cols": 3,
            "rows": 4
        }
    
    def test_3d_grid(self):
        """Test 3D grid calculations."""
        result = calculate_grid_dimensions(2, 3, 4)
        assert result == {
            "total_images": 24,
            "grids_count": 4,
            "cols": 2,
            "rows": 3
        }
    
    def test_single_axis(self):
        """Test single axis grid."""
        result = calculate_grid_dimensions(5, 1)
        assert result["total_images"] == 5
        assert result["cols"] == 5
        assert result["rows"] == 1


class TestCreateUniqueId:
    """Test unique ID generation."""
    
    def test_unique_ids_are_different(self):
        """Test that generated IDs are unique."""
        ids = [create_unique_id() for _ in range(100)]
        assert len(set(ids)) == 100
    
    def test_id_format(self):
        """Test ID format is consistent."""
        uid = create_unique_id()
        assert isinstance(uid, str)
        assert len(uid) == 8  # Should be 8 characters
        assert uid.replace("-", "").isalnum()  # Should be alphanumeric (with possible hyphens)