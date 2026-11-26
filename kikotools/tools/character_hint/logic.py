"""Build the plain-text character hint from dropdown choices."""

from typing import Dict, List, Mapping, Optional, Sequence

from . import options as opt

FEMALE = "woman"
MALE = "man"

# Field name -> (female table, male table). None means the gender has no field.
# HERITAGE is a tuple whose label is also its phrase.
_FIELD_TABLES = {
    "heritage": (opt.HERITAGE, opt.HERITAGE),
    "body_type": (opt.FEMALE_BODY, opt.MALE_BODY),
    "breast_size": (opt.BREAST_SIZE, None),
    "butt_size": (opt.BUTT_SIZE, None),
    "face_shape": (opt.FACE_SHAPE, opt.FACE_SHAPE),
    "eye_color": (opt.EYE_COLOR, opt.EYE_COLOR),
    "eye_shape": (opt.EYE_SHAPE, opt.EYE_SHAPE),
    "eye_detail": (opt.EYE_DETAIL, opt.EYE_DETAIL),
    "nose": (opt.NOSE, opt.NOSE),
    "lip_shape": (opt.FEMALE_LIP_SHAPE, opt.MALE_LIP_SHAPE),
    "lip_color": (opt.LIP_COLOR, None),
    "makeup": (opt.MAKEUP, None),
    "facial_hair": (None, opt.FACIAL_HAIR),
    "hair_color": (opt.HAIR_COLOR, opt.HAIR_COLOR),
    "hair_length": (opt.HAIR_LENGTH, None),
    "hair_style": (opt.FEMALE_HAIR_STYLE, opt.MALE_HAIR_STYLE),
    "bangs": (opt.BANGS, None),
    "skin_tone": (opt.SKIN_TONE, opt.SKIN_TONE),
    "tan": (opt.TAN, opt.TAN),
    "freckles": (opt.FRECKLES, opt.FRECKLES),
    "acne": (opt.ACNE, opt.ACNE),
    "beauty_mark": (opt.BEAUTY_MARK, opt.BEAUTY_MARK),
    "dimples": (opt.DIMPLES, opt.DIMPLES),
    "tattoo": (opt.TATTOO, opt.TATTOO),
    "expression": (opt.EXPRESSION, opt.EXPRESSION),
    "nipples": (opt.NIPPLES, None),
    "areola": (opt.AREOLA, None),
}

# Part label -> fields it holds, in order. Lip colour and makeup are special.
_BODY = ("body_type", "breast_size", "butt_size")
_FACE_BEFORE_LIPS = ("face_shape", "eye_color", "eye_shape", "eye_detail", "nose")
_FACE_AFTER_LIPS = ("facial_hair", "dimples")
_HAIR = ("hair_color", "hair_length", "hair_style", "bangs")
_SKIN = ("skin_tone", "tan", "freckles", "acne", "beauty_mark")
_UNCLOTHED = ("nipples", "areola")


def _gender_index(gender: str) -> int:
    if gender == FEMALE:
        return 0
    if gender == MALE:
        return 1
    raise ValueError(f"Unknown gender '{gender}': use '{FEMALE}' or '{MALE}'")


def fields(gender: str) -> Dict[str, List[str]]:
    """Ordered field name -> labels (without UNSET) for the gender."""
    index = _gender_index(gender)
    result: Dict[str, List[str]] = {}
    for name, tables in _FIELD_TABLES.items():
        table = tables[index]
        if table is not None:
            result[name] = list(table)
    return result


def _phrase(gender: str, field: str, label: str) -> str:
    table = _FIELD_TABLES[field][_gender_index(gender)]
    if label not in table:
        raise ValueError(f"Unknown {field} '{label}'")
    if isinstance(table, tuple):
        return label
    return table[label]


def _chosen(gender: str, values: Mapping[str, str], field: str) -> Optional[str]:
    """The phrase for a field, or None when unset or not this gender's."""
    label = values.get(field)
    if not label or label == opt.UNSET:
        return None
    if _FIELD_TABLES[field][_gender_index(gender)] is None:
        return None
    return _phrase(gender, field, label)


def _phrases(gender: str, values: Mapping[str, str], names: Sequence[str]) -> List[str]:
    found = (_chosen(gender, values, name) for name in names)
    return [phrase for phrase in found if phrase]


def _part(label: str, phrases: List[str]) -> Optional[str]:
    if not phrases:
        return None
    return f"{label}: {', '.join(phrases)}."


def _makeup_phrases(gender: str, values: Mapping[str, str]) -> List[str]:
    style = values.get("makeup")
    if (
        not style
        or style == opt.UNSET
        or _FIELD_TABLES["makeup"][_gender_index(gender)] is None
    ):
        return []
    if style not in opt.MAKEUP:
        raise ValueError(f"Unknown makeup '{style}'")
    look, lips = opt.MAKEUP[style]
    colour = _chosen(gender, values, "lip_color")
    if colour:
        lips = f"{colour} lips"
    return [f"wearing {look}", f"and {lips}"]


def _lip_colour_for_face(gender: str, values: Mapping[str, str]) -> List[str]:
    makeup = values.get("makeup")
    if makeup and makeup != opt.UNSET:
        if _FIELD_TABLES["makeup"][_gender_index(gender)] is not None:
            return []
    colour = _chosen(gender, values, "lip_color")
    return [f"{colour} lips"] if colour else []


def _extra_part(extra: str) -> Optional[str]:
    text = (extra or "").strip()
    if not any(char.isalnum() for char in text):
        return None
    if not text.endswith((".", "!", "?")):
        text += "."
    return f"Extra: {text}"


def build_hint(
    gender: str, age: int, values: Mapping[str, str], extra: str = ""
) -> str:
    """Write the hint text; see the design spec's 'The hint text'."""
    _gender_index(gender)
    heritage = _chosen(gender, values, "heritage")
    who = f"{heritage} {gender}" if heritage else gender
    parts: List[Optional[str]] = [f"The character is an adult {who} aged {age}."]

    parts.append(_part("Body", _phrases(gender, values, _BODY)))
    face = (
        _phrases(gender, values, _FACE_BEFORE_LIPS)
        + _phrases(gender, values, ("lip_shape",))
        + _lip_colour_for_face(gender, values)
        + _phrases(gender, values, _FACE_AFTER_LIPS)
    )
    parts.append(_part("Face", face))
    parts.append(_part("Makeup", _makeup_phrases(gender, values)))
    parts.append(_part("Hair", _phrases(gender, values, _HAIR)))
    parts.append(_part("Skin", _phrases(gender, values, _SKIN)))
    parts.append(_part("Tattoos", _phrases(gender, values, ("tattoo",))))
    parts.append(_part("Expression", _phrases(gender, values, ("expression",))))
    parts.append(_part("Unclothed detail", _phrases(gender, values, _UNCLOTHED)))
    parts.append(_extra_part(extra))
    return " ".join(part for part in parts if part)
