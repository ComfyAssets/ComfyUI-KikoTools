"""Unit tests for DisplayAny node."""

import json
import numpy as np
import pytest
import torch

from kikotools.tools.display_any import DisplayAnyNode
from kikotools.tools.display_any.logic import (
    format_display_value,
    get_tensor_shapes,
    validate_display_mode,
)
from kikotools.tools.display_any.node import AnyType


class TestAnyType:
    """Test cases for AnyType class."""

    def test_anytype_not_equal(self):
        """Test that AnyType is never equal to other types."""
        any_type = AnyType("*")

        # Should not be equal to any other type
        assert not (any_type != "STRING")
        assert not (any_type != "IMAGE")
        assert not (any_type != "LATENT")
        assert not (any_type != 123)
        assert not (any_type != None)
        assert not (any_type != ["LIST"])

    def test_anytype_string_representation(self):
        """Test string representation of AnyType."""
        any_type = AnyType("*")
        assert str(any_type) == "*"


class TestDisplayAnyNode:
    """Test cases for DisplayAnyNode."""

    def test_node_properties(self):
        """Test node has correct properties."""
        assert DisplayAnyNode.CATEGORY == "🫶 ComfyAssets/👁️ Display"
        assert DisplayAnyNode.FUNCTION == "display"
        assert DisplayAnyNode.RETURN_TYPES == ("STRING",)
        assert DisplayAnyNode.RETURN_NAMES == ("display_text",)
        assert DisplayAnyNode.OUTPUT_NODE is True

    def test_input_types(self):
        """Test INPUT_TYPES configuration."""
        input_types = DisplayAnyNode.INPUT_TYPES()

        # Check required inputs
        assert "required" in input_types
        assert "input" in input_types["required"]
        # Check that input is AnyType with wildcard
        input_type = input_types["required"]["input"]
        assert len(input_type) == 2
        assert isinstance(input_type[0], AnyType)
        assert str(input_type[0]) == "*"
        assert input_type[1] == {}
        assert "mode" in input_types["required"]
        assert input_types["required"]["mode"] == (["raw value", "tensor shape"],)

    def test_validate_inputs(self):
        """Test VALIDATE_INPUTS always returns True."""
        assert DisplayAnyNode.VALIDATE_INPUTS() is True
        assert DisplayAnyNode.VALIDATE_INPUTS(input="test") is True
        assert DisplayAnyNode.VALIDATE_INPUTS(input=123, mode="raw value") is True

    def test_display_raw_value_string(self):
        """Test displaying raw string value."""
        node = DisplayAnyNode()
        result = node.display("Hello, World!", "raw value")

        assert "ui" in result
        assert "text" in result["ui"]
        assert result["ui"]["text"] == ["Hello, World!"]
        assert "result" in result
        assert result["result"] == ("Hello, World!",)

    def test_display_raw_value_number(self):
        """Test displaying raw number value."""
        node = DisplayAnyNode()
        result = node.display(42, "raw value")

        assert result["ui"]["text"] == ["42"]
        assert result["result"] == ("42",)

    def test_display_raw_value_list(self):
        """Test displaying raw list value."""
        node = DisplayAnyNode()
        test_list = [1, 2, 3, "test"]
        result = node.display(test_list, "raw value")

        expected_text = json.dumps(test_list, indent=2)
        assert result["ui"]["text"] == [expected_text]
        assert result["result"][0] == json.dumps(test_list, indent=2)

    def test_display_raw_value_dict(self):
        """Test displaying raw dictionary value."""
        node = DisplayAnyNode()
        test_dict = {"key": "value", "number": 123}
        result = node.display(test_dict, "raw value")

        expected_text = json.dumps(test_dict, indent=2)
        assert result["ui"]["text"] == [expected_text]
        assert result["result"][0] == json.dumps(test_dict, indent=2)

    def test_display_tensor_shape_numpy(self):
        """Test displaying numpy tensor shape."""
        node = DisplayAnyNode()
        tensor = np.random.rand(4, 3, 224, 224)
        result = node.display(tensor, "tensor shape")

        assert result["ui"]["text"] == ["[[4, 3, 224, 224]]"]
        assert result["result"] == ("[[4, 3, 224, 224]]",)

    @pytest.mark.skipif(not torch, reason="PyTorch not installed")
    def test_display_tensor_shape_torch(self):
        """Test displaying PyTorch tensor shape."""
        node = DisplayAnyNode()
        tensor = torch.randn(2, 10, 512, 512)
        result = node.display(tensor, "tensor shape")

        assert result["ui"]["text"] == ["[[2, 10, 512, 512]]"]
        assert result["result"] == ("[[2, 10, 512, 512]]",)

    def test_display_nested_tensors(self):
        """Test displaying shapes from nested structure with tensors."""
        node = DisplayAnyNode()
        nested_data = {
            "images": np.random.rand(1, 3, 256, 256),
            "masks": [
                np.random.rand(256, 256),
                np.random.rand(256, 256, 1),
            ],
            "metadata": {"info": "test", "tensor": np.random.rand(10)},
        }
        result = node.display(nested_data, "tensor shape")

        expected = "[[1, 3, 256, 256], [256, 256], [256, 256, 1], [10]]"
        assert result["ui"]["text"] == [expected]
        assert result["result"] == (expected,)

    def test_display_no_tensors(self):
        """Test displaying when no tensors are present."""
        node = DisplayAnyNode()
        data = {"text": "hello", "number": 42, "list": [1, 2, 3]}
        result = node.display(data, "tensor shape")

        assert result["ui"]["text"] == ["No tensors found in input"]
        assert result["result"] == ("No tensors found in input",)

    def test_invalid_mode_defaults_to_raw(self):
        """Test that invalid mode defaults to raw value."""
        node = DisplayAnyNode()
        result = node.display("test", "invalid_mode")

        assert result["ui"]["text"] == ["test"]
        assert result["result"] == ("test",)


class TestDisplayAnyLogic:
    """Test cases for DisplayAny logic functions."""

    def test_get_tensor_shapes_single(self):
        """Test getting shape from single tensor."""
        tensor = np.random.rand(3, 224, 224)
        shapes = get_tensor_shapes(tensor)

        assert len(shapes) == 1
        assert shapes[0] == [3, 224, 224]

    def test_get_tensor_shapes_nested_dict(self):
        """Test getting shapes from nested dictionary."""
        data = {
            "level1": {
                "tensor1": np.random.rand(10, 20),
                "level2": {"tensor2": np.random.rand(5, 5, 5)},
            }
        }
        shapes = get_tensor_shapes(data)

        assert len(shapes) == 2
        assert [10, 20] in shapes
        assert [5, 5, 5] in shapes

    def test_get_tensor_shapes_nested_list(self):
        """Test getting shapes from nested list."""
        data = [
            np.random.rand(1, 2, 3),
            [np.random.rand(4, 5), np.random.rand(6, 7, 8)],
            "not a tensor",
        ]
        shapes = get_tensor_shapes(data)

        assert len(shapes) == 3
        assert [1, 2, 3] in shapes
        assert [4, 5] in shapes
        assert [6, 7, 8] in shapes

    def test_get_tensor_shapes_tuple(self):
        """Test getting shapes from tuple."""
        data = (np.random.rand(2, 2), np.random.rand(3, 3))
        shapes = get_tensor_shapes(data)

        assert len(shapes) == 2
        assert [2, 2] in shapes
        assert [3, 3] in shapes

    def test_format_display_value_raw(self):
        """Test formatting for raw value display."""
        result = format_display_value({"key": "value"}, "raw value")
        # Now returns JSON formatted string for dicts
        expected = json.dumps({"key": "value"}, indent=2)
        assert result == expected

    def test_format_display_value_tensor_shape(self):
        """Test formatting for tensor shape display."""
        tensor = np.random.rand(10, 10)
        result = format_display_value(tensor, "tensor shape")
        assert result == "[[10, 10]]"

    def test_format_display_value_no_tensors(self):
        """Test formatting when no tensors present."""
        result = format_display_value("just a string", "tensor shape")
        assert result == "No tensors found in input"

    def test_validate_display_mode(self):
        """Test display mode validation."""
        assert validate_display_mode("raw value") is True
        assert validate_display_mode("tensor shape") is True
        assert validate_display_mode("invalid") is False
        assert validate_display_mode("") is False
        assert validate_display_mode(None) is False


class TestDisplayAnyEdgeCases:
    """Test edge cases for DisplayAny."""

    def test_display_none(self):
        """Test displaying None value."""
        node = DisplayAnyNode()
        result = node.display(None, "raw value")
        assert result["ui"]["text"] == ["None"]

    def test_display_empty_list(self):
        """Test displaying empty list."""
        node = DisplayAnyNode()
        result = node.display([], "raw value")
        assert result["ui"]["text"] == ["[]"]

    def test_display_empty_dict(self):
        """Test displaying empty dictionary."""
        node = DisplayAnyNode()
        result = node.display({}, "raw value")
        assert result["ui"]["text"] == ["{}"]

    def test_display_complex_nested_structure(self):
        """Test displaying complex nested structure."""
        node = DisplayAnyNode()
        complex_data = {
            "images": [np.random.rand(1, 3, 64, 64) for _ in range(3)],
            "config": {
                "steps": 20,
                "cfg": 7.5,
                "sampler": "euler",
                "latents": np.random.rand(1, 4, 32, 32),
            },
            "prompts": ["test1", "test2"],
        }
        result = node.display(complex_data, "tensor shape")

        # Should find 4 tensors total (3 images + 1 latent)
        shapes_text = result["ui"]["text"][0]  # Get first element of array
        assert "[1, 3, 64, 64]" in shapes_text
        assert "[1, 4, 32, 32]" in shapes_text

    def test_display_very_long_string(self):
        """Test displaying very long string."""
        node = DisplayAnyNode()
        long_string = "x" * 10000
        result = node.display(long_string, "raw value")
        assert result["ui"]["text"] == [long_string]

    def test_display_unicode(self):
        """Test displaying unicode characters."""
        node = DisplayAnyNode()
        unicode_text = "Hello 世界 🌍"
        result = node.display(unicode_text, "raw value")
        assert result["ui"]["text"] == [unicode_text]
