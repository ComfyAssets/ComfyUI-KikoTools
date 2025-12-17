"""Unit tests for Width Height to VEC2 node."""

import pytest

from kikotools.tools.width_height_to_vec2 import WidthHeightToVec2Node


class TestWidthHeightToVec2Node:
    """Test cases for WidthHeightToVec2Node."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = WidthHeightToVec2Node()

    def test_basic_int_conversion(self):
        """Test basic integer inputs."""
        result = self.node.convert_to_vec2(512, 768)
        assert result == ((512, 768),)

    def test_float_conversion(self):
        """Test float inputs are converted to int."""
        result = self.node.convert_to_vec2(512.7, 768.3)
        assert result == ((512, 768),)

    def test_string_conversion(self):
        """Test string inputs are parsed correctly."""
        result = self.node.convert_to_vec2("1024", "768")
        assert result == ((1024, 768),)

    def test_string_with_decimal(self):
        """Test string with decimal point."""
        result = self.node.convert_to_vec2("1024.5", "768.0")
        assert result == ((1024, 768),)

    def test_clamp_max_values(self):
        """Test values are clamped to maximum."""
        result = self.node.convert_to_vec2(10000, 9999)
        assert result == ((8192, 8192),)

    def test_clamp_min_values(self):
        """Test values are clamped to minimum."""
        result = self.node.convert_to_vec2(0, -5)
        assert result == ((1, 1),)

    def test_return_type_is_tuple_of_tuple(self):
        """Test return type is correct for ComfyUI."""
        result = self.node.convert_to_vec2(512, 512)
        assert isinstance(result, tuple)
        assert len(result) == 1
        assert isinstance(result[0], tuple)
        assert len(result[0]) == 2

    def test_input_types_defined(self):
        """Test INPUT_TYPES is properly defined."""
        input_types = WidthHeightToVec2Node.INPUT_TYPES()
        assert "required" in input_types
        assert "width" in input_types["required"]
        assert "height" in input_types["required"]

    def test_return_types_defined(self):
        """Test RETURN_TYPES is properly defined."""
        assert WidthHeightToVec2Node.RETURN_TYPES == ("VEC2",)
        assert WidthHeightToVec2Node.RETURN_NAMES == ("vec2",)

    def test_category_set(self):
        """Test node category is set."""
        assert "ComfyAssets" in WidthHeightToVec2Node.CATEGORY


class TestWidthHeightToVec2Errors:
    """Test error handling for WidthHeightToVec2Node."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = WidthHeightToVec2Node()

    def test_invalid_string_raises_error(self):
        """Test invalid string input raises error."""
        with pytest.raises(ValueError) as excinfo:
            self.node.convert_to_vec2("not_a_number", 512)
        assert "Cannot convert width" in str(excinfo.value)
