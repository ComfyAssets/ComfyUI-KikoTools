"""ComfyUI node implementation for Project File Path."""

from datetime import date
from typing import Any, Dict, Tuple

from ...base import ComfyAssetsBaseNode
from .logic import SEPARATOR_OPTIONS, build_project_path


def _today() -> date:
    return date.today()


class ProjectFilePathNode(ComfyAssetsBaseNode):
    """
    Builds a save prefix like 'MyProject/2026-10-13/images/image'.

    Wire the output into a save node's filename_prefix. Every component is
    sanitized so the result stays inside ComfyUI's output folder.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "root": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Optional top folder inside the output folder",
                    },
                ),
                "project_name": ("STRING", {"default": "MyProject"}),
                "subfolder": (
                    "STRING",
                    {"default": "images", "tooltip": "Use a/b for nested folders"},
                ),
                "filename": (
                    "STRING",
                    {
                        "default": "image",
                        "tooltip": "File extensions like .png are removed",
                    },
                ),
            },
            "optional": {
                "date_folder": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Insert a YYYY-MM-DD folder after the project",
                    },
                ),
                "separator": (list(SEPARATOR_OPTIONS), {"default": "auto"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("path",)
    FUNCTION = "generate_path"
    CATEGORY = "🫶 ComfyAssets/🛠️ Utils"

    @classmethod
    def IS_CHANGED(cls, date_folder: bool = False, **kwargs) -> str:
        # Output depends only on the inputs, except for the date folder:
        # re-run when the day changes so open workflows get the new date.
        return _today().isoformat() if date_folder else ""

    def generate_path(
        self,
        root: str,
        project_name: str,
        subfolder: str,
        filename: str,
        date_folder: bool = False,
        separator: str = "auto",
    ) -> Tuple[str]:
        try:
            path = build_project_path(
                root,
                project_name,
                subfolder,
                filename,
                date_folder=date_folder,
                separator=separator,
                today=_today(),
            )
        except ValueError as e:
            self.handle_error(str(e), e)
        return (path,)
