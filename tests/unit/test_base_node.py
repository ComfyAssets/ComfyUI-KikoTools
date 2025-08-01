"""
Unit tests for ComfyAssetsBaseNode
Tests the shared functionality for all ComfyAssets tools
"""

import pytest
from unittest.mock import patch

from kikotools.base import ComfyAssetsBaseNode


class TestComfyAssetsBaseNode:
    """Test the base node functionality"""

    def test_category_is_comfy_assets(self):
        """Test that CATEGORY is set to ComfyAssets"""
        assert ComfyAssetsBaseNode.CATEGORY == "ComfyAssets"

    def test_validate_inputs_default_implementation(self):
        """Test default validate_inputs does nothing"""
        node = ComfyAssetsBaseNode()

        # Should not raise any exceptions
        node.validate_inputs(test_param="value", another_param=123)

    def test_handle_error_logs_and_raises(self):
        """Test error handling logs and raises ValueError"""
        node = ComfyAssetsBaseNode()

        with patch("kikotools.base.base_node.logger") as mock_logger:
            with pytest.raises(ValueError, match="Test error message"):
                node.handle_error("Test error message")

            mock_logger.error.assert_called_once()
            assert "ComfyAssetsBaseNode: Test error message" in mock_logger.error.call_args[0][0]

    def test_handle_error_with_exception_logs_exception(self):
        """Test error handling with original exception logs both messages"""
        node = ComfyAssetsBaseNode()
        original_exception = RuntimeError("Original error")

        with patch("kikotools.base.base_node.logger") as mock_logger:
            with pytest.raises(ValueError, match="Handled error"):
                node.handle_error("Handled error", original_exception)

            # Should log both error and exception
            assert mock_logger.error.call_count == 1
            assert mock_logger.exception.call_count == 1

    def test_log_info_logs_with_class_name(self):
        """Test info logging includes class name"""
        node = ComfyAssetsBaseNode()

        with patch("kikotools.base.base_node.logger") as mock_logger:
            node.log_info("Test information")

            mock_logger.info.assert_called_once()
            assert "ComfyAssetsBaseNode: Test information" in mock_logger.info.call_args[0][0]

    def test_get_node_info_returns_metadata(self):
        """Test get_node_info returns correct metadata"""
        info = ComfyAssetsBaseNode.get_node_info()

        assert isinstance(info, dict)
        assert info["class_name"] == "ComfyAssetsBaseNode"
        assert info["category"] == "ComfyAssets"
        assert info["function"] == "Unknown"  # Base class doesn't have FUNCTION
        assert info["return_types"] == ()
        assert info["return_names"] == ()


class MockConcreteNode(ComfyAssetsBaseNode):
    """Mock concrete implementation for testing inheritance"""

    FUNCTION = "mock_function"
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("text", "number")

    def mock_execute(self):
        return "test", 42


class TestConcreteNodeInheritance:
    """Test how concrete nodes inherit from base"""

    def test_concrete_node_inherits_category(self):
        """Test concrete node inherits ComfyAssets category"""
        assert MockConcreteNode.CATEGORY == "ComfyAssets"

    def test_concrete_node_get_info_includes_specific_attributes(self):
        """Test concrete node info includes its specific attributes"""
        info = MockConcreteNode.get_node_info()

        assert info["class_name"] == "MockConcreteNode"
        assert info["category"] == "ComfyAssets"
        assert info["function"] == "mock_function"
        assert info["return_types"] == ("STRING", "INT")
        assert info["return_names"] == ("text", "number")

    def test_concrete_node_can_override_validation(self):
        """Test concrete nodes can override validation"""

        class StrictNode(ComfyAssetsBaseNode):
            def validate_inputs(self, **kwargs):
                if "required_param" not in kwargs:
                    raise ValueError("required_param is missing")

        node = StrictNode()

        # Should pass with required param
        node.validate_inputs(required_param="value")

        # Should fail without required param
        with pytest.raises(ValueError, match="required_param is missing"):
            node.validate_inputs(other_param="value")

    def test_concrete_node_error_handling_includes_correct_class_name(self):
        """Test error messages include correct class name"""
        node = MockConcreteNode()

        with patch("kikotools.base.base_node.logger") as mock_logger:
            with pytest.raises(ValueError):
                node.handle_error("Test error")

            # Should include MockConcreteNode, not ComfyAssetsBaseNode
            assert "MockConcreteNode: Test error" in mock_logger.error.call_args[0][0]

    def test_concrete_node_info_logging_includes_correct_class_name(self):
        """Test info logging includes correct class name"""
        node = MockConcreteNode()

        with patch("kikotools.base.base_node.logger") as mock_logger:
            node.log_info("Test info")

            # Should include MockConcreteNode, not ComfyAssetsBaseNode
            assert "MockConcreteNode: Test info" in mock_logger.info.call_args[0][0]
