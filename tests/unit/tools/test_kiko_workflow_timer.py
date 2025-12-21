"""
Unit tests for KikoWorkflowTimerNode.

Since this is a display-only node with all logic handled by JavaScript,
these tests focus on validating the node's structure and ComfyUI integration.
"""


class TestKikoWorkflowTimerNode:
    """Test suite for KikoWorkflowTimerNode."""

    def test_node_import(self):
        """Test that the node can be imported successfully."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        assert KikoWorkflowTimerNode is not None

    def test_node_has_required_attributes(self):
        """Test that the node has all required ComfyUI attributes."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        # Check required ComfyUI attributes
        assert hasattr(KikoWorkflowTimerNode, "INPUT_TYPES")
        assert hasattr(KikoWorkflowTimerNode, "RETURN_TYPES")
        assert hasattr(KikoWorkflowTimerNode, "FUNCTION")
        assert hasattr(KikoWorkflowTimerNode, "CATEGORY")

    def test_node_input_types(self):
        """Test that INPUT_TYPES is correctly defined."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        input_types = KikoWorkflowTimerNode.INPUT_TYPES()

        # Should have required dict (empty)
        assert "required" in input_types
        assert input_types["required"] == {}

        # Should have hidden inputs for prompt and unique_id
        assert "hidden" in input_types
        assert "prompt" in input_types["hidden"]
        assert "unique_id" in input_types["hidden"]
        assert input_types["hidden"]["prompt"] == "PROMPT"
        assert input_types["hidden"]["unique_id"] == "UNIQUE_ID"

    def test_node_return_types(self):
        """Test that the node has empty return types (display-only)."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        assert KikoWorkflowTimerNode.RETURN_TYPES == ()

    def test_node_is_output_node(self):
        """Test that OUTPUT_NODE is set to True."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        assert KikoWorkflowTimerNode.OUTPUT_NODE is True

    def test_node_category(self):
        """Test that the node has correct category."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        assert "ComfyAssets" in KikoWorkflowTimerNode.CATEGORY

    def test_node_display_name(self):
        """Test that the node has a display name."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        assert hasattr(KikoWorkflowTimerNode, "DISPLAY_NAME")
        assert KikoWorkflowTimerNode.DISPLAY_NAME == "Workflow Timer"

    def test_node_execute_returns_empty(self):
        """Test that execute() returns empty dict."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        node = KikoWorkflowTimerNode()
        result = node.execute()

        assert result == {}

    def test_node_execute_with_kwargs(self):
        """Test that execute() handles kwargs correctly."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode

        node = KikoWorkflowTimerNode()
        result = node.execute(prompt={}, unique_id="test-123")

        assert result == {}

    def test_node_inherits_from_base(self):
        """Test that node inherits from ComfyAssetsBaseNode."""
        from kikotools.tools.kiko_workflow_timer.node import KikoWorkflowTimerNode
        from kikotools.base import ComfyAssetsBaseNode

        assert issubclass(KikoWorkflowTimerNode, ComfyAssetsBaseNode)


class TestKikoWorkflowTimerModuleInit:
    """Test the module's __init__.py exports."""

    def test_module_exports_node(self):
        """Test that the module exports the node class."""
        from kikotools.tools.kiko_workflow_timer import KikoWorkflowTimerNode

        assert KikoWorkflowTimerNode is not None

    def test_module_all_exports(self):
        """Test that __all__ is correctly defined."""
        from kikotools.tools import kiko_workflow_timer

        assert hasattr(kiko_workflow_timer, "__all__")
        assert "KikoWorkflowTimerNode" in kiko_workflow_timer.__all__
