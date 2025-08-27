"""Tool registry for KikoTools.

This module provides the central registration system for all KikoTools nodes.
"""

import importlib
from typing import Dict, Any
from pathlib import Path


class ToolRegistry:
    """Central registry for all KikoTools."""

    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.node_classes: Dict[str, Any] = {}

    def register_tool(self, tool_name: str, node_class: Any) -> None:
        """Register a tool and its node class.

        Args:
            tool_name: Name of the tool
            node_class: The ComfyUI node class
        """
        self.tools[tool_name] = node_class

        # Also register by class name for ComfyUI
        class_name = node_class.__name__
        self.node_classes[class_name] = node_class

    def discover_tools(self) -> None:
        """Automatically discover and load all tools in the tools directory."""
        tools_dir = Path(__file__).parent.parent / "tools"

        if not tools_dir.exists():
            return

        for tool_dir in tools_dir.iterdir():
            if tool_dir.is_dir() and not tool_dir.name.startswith("_"):
                self._load_tool(tool_dir.name)

    def _load_tool(self, tool_name: str) -> None:
        """Load a single tool module.

        Args:
            tool_name: Name of the tool directory
        """
        try:
            # Try to import the tool's node module
            module = importlib.import_module(f"kikotools.tools.{tool_name}.node")

            # Look for node classes (classes with ComfyUI node attributes)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "INPUT_TYPES")
                    and hasattr(attr, "FUNCTION")
                ):
                    self.register_tool(tool_name, attr)

                    # If the tool has settings, register them
                    if hasattr(attr, "SETTINGS"):
                        from .settings import settings_registry

                        settings_registry.register_tool_settings(
                            tool_name,
                            getattr(
                                attr,
                                "DISPLAY_NAME",
                                tool_name.replace("_", " ").title(),
                            ),
                            attr.SETTINGS,
                        )

        except ImportError:
            # Tool might not have a node.py file yet
            pass

    def get_node_class_mappings(self) -> Dict[str, Any]:
        """Get node class mappings for ComfyUI registration."""
        return self.node_classes.copy()

    def get_node_display_name_mappings(self) -> Dict[str, str]:
        """Get display name mappings for ComfyUI."""
        mappings = {}
        for class_name, node_class in self.node_classes.items():
            if hasattr(node_class, "DISPLAY_NAME"):
                mappings[class_name] = node_class.DISPLAY_NAME
            else:
                # Generate a display name from class name
                mappings[class_name] = class_name.replace("Kiko", "").replace(
                    "Node", ""
                )
        return mappings
