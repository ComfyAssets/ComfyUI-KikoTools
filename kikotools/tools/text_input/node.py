"""Text Input node implementation."""

from ...base import ComfyAssetsBaseNode


class TextInputNode(ComfyAssetsBaseNode):
    """Provides a text input field for manual text entry in ComfyUI workflows."""

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        return {
            "required": {
                "text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "dynamicPrompts": True,
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "execute"
    CATEGORY = "🫶 ComfyAssets/📝 Text"

    DESCRIPTION = """
Simple text input field for entering text manually.

Features:
- Multiline text editing
- Supports wildcards and dynamic prompts
- Direct connection to CLIP text encoders
- Unicode and special character support

Use Cases:
- Positive/negative prompts
- Custom text for workflows
- Manual text editing
- Prompt templates
"""

    def execute(self, text):
        """Process the input text and return it.

        Args:
            text: Input text from the widget

        Returns:
            Tuple containing the text
        """
        return (text,)


# Node display name
NODE_DISPLAY_NAME = "Text Input"
