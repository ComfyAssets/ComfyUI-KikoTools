"""
KikoWorkflow Timer Node

A display-only node that shows real-time execution timing for ComfyUI workflows.
The timer is managed entirely on the frontend via WebSocket events.
"""

from ...base import ComfyAssetsBaseNode


class KikoWorkflowTimerNode(ComfyAssetsBaseNode):
    """
    A UI node that displays a real-time timer for workflow execution.

    The timer starts when execution begins and stops when the workflow
    completes, showing the total elapsed time in MM:SS:mmm format.

    This is a display-only node with no inputs or outputs - all timing
    logic is handled by the JavaScript frontend via WebSocket events.
    """

    DISPLAY_NAME = "Workflow Timer"
    CATEGORY = "🫶 ComfyAssets/🛠️ Utils"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "hidden": {
                "prompt": "PROMPT",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True

    def execute(self, **kwargs):
        """
        Execute method - returns empty since this is a display-only node.

        The actual timer functionality is handled entirely by the JavaScript
        frontend which hooks into ComfyUI's WebSocket events.

        Args:
            **kwargs: Hidden parameters (prompt, unique_id)

        Returns:
            Empty dict - no outputs
        """
        return {}
