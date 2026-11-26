"""Character Hint nodes: dropdowns in, one plain-text hint out."""

from typing import Any, Dict, Tuple

from ...base.base_node import ComfyAssetsBaseNode
from . import logic, options
from .options import DEFAULT_AGE, MAX_AGE, MIN_AGE, UNSET


class _CharacterHintNode(ComfyAssetsBaseNode):
    """Shared behaviour; subclasses set GENDER."""

    GENDER = ""
    CATEGORY = "🫶 ComfyAssets/🧠 Prompts"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("hint",)
    FUNCTION = "build"

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        required: Dict[str, Any] = {
            "age": (
                "INT",
                {
                    "default": DEFAULT_AGE,
                    "min": MIN_AGE,
                    "max": MAX_AGE,
                    "step": 1,
                    "display": "slider",
                },
            )
        }
        for name, labels in logic.fields(cls.GENDER, options.tables()).items():
            required[name] = ([UNSET, *labels], {"default": UNSET})
        return {
            "required": required,
            "optional": {
                "extra": (
                    "STRING",
                    {"multiline": True, "default": "", "tooltip": "Free text"},
                )
            },
        }

    def build(self, age: int, extra: str = "", **values: str) -> Tuple[str]:
        return (logic.build_hint(self.GENDER, age, values, extra, options.tables()),)


class CharacterHintFemaleNode(_CharacterHintNode):
    GENDER = logic.FEMALE


class CharacterHintMaleNode(_CharacterHintNode):
    GENDER = logic.MALE
