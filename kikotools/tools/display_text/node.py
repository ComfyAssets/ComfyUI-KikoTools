"""Display Text node implementation."""

from ...base import ComfyAssetsBaseNode


class DisplayTextNode(ComfyAssetsBaseNode):
    """Displays text in the ComfyUI interface with copy-to-clipboard functionality."""

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    OUTPUT_NODE = True
    FUNCTION = "display_text"
    CATEGORY = "🫶 ComfyAssets/👁️ Display"

    DESCRIPTION = """
Displays text in the UI with a copy-to-clipboard feature.

Features:
- Shows text content in a readable format
- Copy button appears on hover
- Passes text through for chaining
"""

    def display_text(self, text):
        """Display the text and pass it through.

        Args:
            text: Input text to display

        Returns:
            Tuple containing the text
        """
        # The actual display happens in the frontend
        # We just pass the text through
        return {"ui": {"text": [text]}, "result": (text,)}


# Node display name
NODE_DISPLAY_NAME = "Display Text"
