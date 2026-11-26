"""Build the plain-text character hint from dropdown choices."""

from typing import Any, Dict, List, Mapping, Optional, Sequence

from . import options as opt

Tables = Mapping[str, Mapping[str, Any]]

FEMALE = "woman"
MALE = "man"

# Field name -> (female table name, male table name). None means the gender
# has no field. The tables themselves come from options.tables().
_FIELD_TABLES = {
    "heritage": ("heritage", "heritage"),
    "body_type": ("female_body", "male_body"),
    "breast_size": ("breast_size", None),
    "butt_size": ("butt_size", None),
    "face_shape": ("face_shape", "face_shape"),
    "facial_structure": ("facial_structure", "facial_structure"),
    "eye_color": ("eye_color", "eye_color"),
    "eye_shape": ("eye_shape", "eye_shape"),
    "eye_detail": ("eye_detail", "eye_detail"),
    "eyebrows": ("eyebrows", "eyebrows"),
    "nose": ("nose", "nose"),
    "lip_shape": ("female_lip_shape", "male_lip_shape"),
    "lip_color": ("lip_color", None),
    "makeup": ("makeup", None),
    "eyewear": ("eyewear", "eyewear"),
    "facial_hair": (None, "facial_hair"),
    "hair_color": ("hair_color", "hair_color"),
    "hair_texture": ("hair_texture", "hair_texture"),
    "hair_length": ("hair_length", None),
    "hair_style": ("female_hair_style", "male_hair_style"),
    "bangs": ("bangs", None),
    "skin_tone": ("skin_tone", "skin_tone"),
    "tan": ("tan", "tan"),
    "freckles": ("freckles", "freckles"),
    "acne": ("acne", "acne"),
    "beauty_mark": ("beauty_mark", "beauty_mark"),
    "dimples": ("dimples", "dimples"),
    "tattoo": ("tattoo", "tattoo"),
    "expression": ("expression", "expression"),
    "head_angle": ("head_angle", "head_angle"),
    "gaze": ("gaze", "gaze"),
    "nipples": ("nipples", None),
    "areola": ("areola", None),
}

# Part label -> fields it holds, in order. Lip colour and makeup are special.
_BODY = ("body_type", "breast_size", "butt_size")
_FACE_BEFORE_LIPS = (
    "face_shape",
    "facial_structure",
    "eye_color",
    "eye_shape",
    "eye_detail",
    "eyebrows",
    "nose",
)
_FACE_AFTER_LIPS = ("facial_hair", "dimples")
_HAIR = ("hair_color", "hair_texture", "hair_length", "hair_style", "bangs")
_POSE = ("head_angle", "gaze")
_SKIN = ("skin_tone", "tan", "freckles", "acne", "beauty_mark")
_UNCLOTHED = ("nipples", "areola")


def _gender_index(gender: str) -> int:
    if gender == FEMALE:
        return 0
    if gender == MALE:
        return 1
    raise ValueError(f"Unknown gender '{gender}': use '{FEMALE}' or '{MALE}'")


def _table_name(gender: str, field: str) -> Optional[str]:
    return _FIELD_TABLES[field][_gender_index(gender)]


def fields(gender: str, tables: Optional[Tables] = None) -> Dict[str, List[str]]:
    """Ordered field name -> labels (without UNSET) for the gender."""
    _gender_index(gender)
    current = opt.tables() if tables is None else tables
    result: Dict[str, List[str]] = {}
    for field in _FIELD_TABLES:
        name = _table_name(gender, field)
        if name is not None:
            result[field] = list(current[name])
    return result


def _phrase(gender: str, tables: Tables, field: str, label: str) -> str:
    table = tables[_table_name(gender, field)]
    if label not in table:
        raise ValueError(f"Unknown {field} '{label}'")
    return table[label]


def _chosen(
    gender: str, tables: Tables, values: Mapping[str, str], field: str
) -> Optional[str]:
    """The phrase for a field, or None when unset or not this gender's."""
    label = values.get(field)
    if not label or label == opt.UNSET:
        return None
    if _table_name(gender, field) is None:
        return None
    return _phrase(gender, tables, field, label)


def _phrases(
    gender: str, tables: Tables, values: Mapping[str, str], names: Sequence[str]
) -> List[str]:
    found = (_chosen(gender, tables, values, name) for name in names)
    return [phrase for phrase in found if phrase]


def _part(label: str, phrases: List[str]) -> Optional[str]:
    if not phrases:
        return None
    return f"{label}: {', '.join(phrases)}."


def _makeup_phrases(
    gender: str, tables: Tables, values: Mapping[str, str]
) -> List[str]:
    style = values.get("makeup")
    if not style or style == opt.UNSET or _table_name(gender, "makeup") is None:
        return []
    entry = tables["makeup"].get(style)
    if entry is None:
        raise ValueError(f"Unknown makeup '{style}'")
    lips = entry["lips"]
    colour = _chosen(gender, tables, values, "lip_color")
    if colour:
        lips = f"{colour} lips"
    return [f"wearing {entry['look']}", f"and {lips}"]


def _lip_colour_for_face(
    gender: str, tables: Tables, values: Mapping[str, str]
) -> List[str]:
    makeup = values.get("makeup")
    if makeup and makeup != opt.UNSET:
        if _table_name(gender, "makeup") is not None:
            return []
    colour = _chosen(gender, tables, values, "lip_color")
    return [f"{colour} lips"] if colour else []


def _extra_part(extra: str) -> Optional[str]:
    text = (extra or "").strip()
    if not any(char.isalnum() for char in text):
        return None
    if not text.endswith((".", "!", "?")):
        text += "."
    return f"Extra: {text}"


def build_hint(
    gender: str,
    age: int,
    values: Mapping[str, str],
    extra: str = "",
    tables: Optional[Tables] = None,
) -> str:
    """Write the hint text; see the design spec's 'The hint text'."""
    _gender_index(gender)
    tbl = opt.tables() if tables is None else tables
    heritage = _chosen(gender, tbl, values, "heritage")
    who = f"{heritage} {gender}" if heritage else gender
    parts: List[Optional[str]] = [f"The character is an adult {who} aged {age}."]

    def phrases(*names: str) -> List[str]:
        return _phrases(gender, tbl, values, names)

    parts.append(_part("Body", phrases(*_BODY)))
    face = (
        phrases(*_FACE_BEFORE_LIPS)
        + phrases("lip_shape")
        + _lip_colour_for_face(gender, tbl, values)
        + phrases(*_FACE_AFTER_LIPS)
    )
    parts.append(_part("Face", face))
    parts.append(_part("Makeup", _makeup_phrases(gender, tbl, values)))
    parts.append(_part("Eyewear", phrases("eyewear")))
    parts.append(_part("Hair", phrases(*_HAIR)))
    parts.append(_part("Skin", phrases(*_SKIN)))
    parts.append(_part("Tattoos", phrases("tattoo")))
    parts.append(_part("Expression", phrases("expression")))
    parts.append(_part("Pose", phrases(*_POSE)))
    parts.append(_part("Unclothed detail", phrases(*_UNCLOTHED)))
    parts.append(_extra_part(extra))
    return " ".join(part for part in parts if part)
