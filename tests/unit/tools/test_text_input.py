"""
Unit tests for Text Input node
Following TDD principles - these tests define the expected behavior
"""

from kikotools.tools.text_input.node import TextInputNode


class TestTextInputNode:
    """Test the Text Input ComfyUI node"""

    def test_node_has_correct_comfyui_attributes(self):
        """Test node has all required ComfyUI attributes"""
        # Check class attributes exist
        assert hasattr(TextInputNode, "INPUT_TYPES")
        assert hasattr(TextInputNode, "RETURN_TYPES")
        assert hasattr(TextInputNode, "RETURN_NAMES")
        assert hasattr(TextInputNode, "FUNCTION")
        assert hasattr(TextInputNode, "CATEGORY")

        # Check category is correct
        assert TextInputNode.CATEGORY == "🫶 ComfyAssets/📝 Text"

        # Check return types
        assert TextInputNode.RETURN_TYPES == ("STRING",)
        assert TextInputNode.RETURN_NAMES == ("text",)

        # Check function name
        assert TextInputNode.FUNCTION == "execute"

    def test_input_types_structure(self):
        """Test INPUT_TYPES has correct structure"""
        input_types = TextInputNode.INPUT_TYPES()

        assert "required" in input_types

        # Check text input configuration
        assert "text" in input_types["required"]
        text_config = input_types["required"]["text"]
        assert text_config[0] == "STRING"
        assert "multiline" in text_config[1]
        assert text_config[1]["multiline"] is True
        assert "default" in text_config[1]
        assert text_config[1]["default"] == ""

    def test_execute_returns_input_text(self):
        """Test that execute method returns the input text"""
        node = TextInputNode()

        test_text = "Hello, ComfyUI!"
        result = node.execute(test_text)

        assert isinstance(result, tuple)
        assert len(result) == 1
        assert result[0] == test_text

    def test_execute_handles_empty_string(self):
        """Test that execute handles empty string input"""
        node = TextInputNode()

        result = node.execute("")

        assert isinstance(result, tuple)
        assert len(result) == 1
        assert result[0] == ""

    def test_execute_handles_multiline_text(self):
        """Test that execute handles multiline text"""
        node = TextInputNode()

        multiline_text = """Line 1
Line 2
Line 3"""

        result = node.execute(multiline_text)

        assert isinstance(result, tuple)
        assert result[0] == multiline_text
        assert "\n" in result[0]

    def test_execute_handles_special_characters(self):
        """Test that execute handles special characters"""
        node = TextInputNode()

        special_text = "Special: @#$%^&*()[]{}|\\;:'\",.<>?/`~"
        result = node.execute(special_text)

        assert result[0] == special_text

    def test_execute_handles_unicode(self):
        """Test that execute handles unicode characters"""
        node = TextInputNode()

        unicode_text = "Unicode: 你好 🎨 émoji café"
        result = node.execute(unicode_text)

        assert result[0] == unicode_text

    def test_execute_handles_very_long_text(self):
        """Test that execute handles very long text"""
        node = TextInputNode()

        long_text = "A" * 10000
        result = node.execute(long_text)

        assert result[0] == long_text
        assert len(result[0]) == 10000

    def test_inherits_from_base_node(self):
        """Test that node inherits from ComfyAssetsBaseNode"""
        from kikotools.base import ComfyAssetsBaseNode

        assert issubclass(TextInputNode, ComfyAssetsBaseNode)

        # Test inherited functionality
        node = TextInputNode()
        node_info = node.get_node_info()

        assert node_info["category"] == "🫶 ComfyAssets/📝 Text"
        assert node_info["class_name"] == "TextInputNode"

    def test_node_description_exists(self):
        """Test that node has a description"""
        assert hasattr(TextInputNode, "DESCRIPTION")
        assert isinstance(TextInputNode.DESCRIPTION, str)
        assert len(TextInputNode.DESCRIPTION) > 0


class TestTextInputIntegration:
    """Test real-world usage scenarios"""

    def test_simple_text_passthrough(self):
        """Test simple text input and output"""
        node = TextInputNode()

        input_text = "This is a test prompt for Stable Diffusion"
        output = node.execute(input_text)

        assert output[0] == input_text

    def test_prompt_workflow_scenario(self):
        """Test typical prompt workflow usage"""
        node = TextInputNode()

        positive_prompt = "beautiful sunset, high quality, detailed, 8k"
        result = node.execute(positive_prompt)

        # Should pass through unchanged for connecting to CLIP text encoder
        assert result[0] == positive_prompt

    def test_multiline_prompt_scenario(self):
        """Test multiline prompt with embedding syntax"""
        node = TextInputNode()

        complex_prompt = """masterpiece, best quality, (detailed face:1.2)
1girl, standing, outdoor
<lora:style_v1:0.7>
--neg-- blurry, low quality"""

        result = node.execute(complex_prompt)

        assert result[0] == complex_prompt
        assert result[0].count("\n") == 3

    def test_empty_text_workflow(self):
        """Test workflow with empty text (valid use case for negative prompt)"""
        node = TextInputNode()

        result = node.execute("")

        # Empty string is valid - some users leave negative prompt empty
        assert result[0] == ""

    def test_text_with_comfyui_wildcards(self):
        """Test text containing ComfyUI wildcard syntax"""
        node = TextInputNode()

        wildcard_text = "{summer|winter|autumn} scene with {cat|dog}"
        result = node.execute(wildcard_text)

        assert result[0] == wildcard_text

    def test_node_chaining_scenario(self):
        """Test that output can be used in node chaining"""
        node1 = TextInputNode()
        node2 = TextInputNode()

        # First node produces text
        output1 = node1.execute("First node text")

        # Second node could receive it (though unusual pattern)
        output2 = node2.execute(output1[0])

        assert output2[0] == "First node text"
