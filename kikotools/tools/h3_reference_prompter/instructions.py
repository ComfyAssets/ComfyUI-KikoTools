"""Instruction text and message builders for the H3 Reference Prompter.

Pass 1 describes each reference picture for its role. Pass 2 writes one
long MiniMax H3 Image prompt from the user's draft and those notes.
"""

from typing import List, Optional, Tuple

from .logic import ROLES, YOUTH_WORDS, find_tags, is_nude

AgeRange = Tuple[int, int]

_DESCRIBE_COMMON = (
    "You look at one reference picture and write factual notes about it. "
    "Write full sentences, not a keyword list. Describe only what you can "
    "see. Do not guess names, brands or stories. Do not add a greeting, a "
    "title or a closing remark. Aim for 80 to 160 words."
)

_DESCRIBE_ROLE = {
    "character": (
        "This picture shows the character. Describe the person: the age "
        "range and the build, the face shape, the eyes, the brows, the nose "
        "and the lips, the skin tone and skin texture, the hair (colour, "
        "length, style and parting), the fringe or bangs exactly as they "
        "fall (for example blunt and straight across the brows, or swept "
        "to one side), any distinctive marks such as freckles or moles, and "
        "the expression. Say exactly what the mouth does: closed, a closed "
        "smile, or a wide smile with the teeth showing. Say each trait once. "
        "Do not describe the clothing, the background or the lighting. "
        "Finish the notes with one last line in exactly this form, with "
        "nothing after it: Estimated age: N to M years. N and M are whole "
        "numbers: the youngest and the oldest the person could be, judged "
        "only from what you see. When the person could look younger than "
        "your first guess, give that lower number."
    ),
    "outfit": (
        "This picture shows the outfit. Go through every garment from top "
        "to bottom, one sentence per garment. For each garment give the "
        "colour, the material, the fit, and the construction details such "
        "as seams, buttons, zips, trims and prints, and how far it reaches "
        "on the body (for example cropped, hip length, knee length or "
        "ankle length; socks at the ankle, mid-calf or knee). Then describe "
        "the accessories (bags, belts, jewellery, hats) and the footwear, "
        "and say where each one is worn or carried: a hat worn on the head, "
        "a bag held in one hand or over the shoulder. An item shown floating "
        "above or beside the clothes is still worn in its usual place: "
        "never say an item floats, hovers or is suspended. Do "
        "not describe the person's face, hair or body, and do not describe "
        "the background."
    ),
    "pose": (
        "This picture shows a pose. Start with one sentence that names the "
        "overall position (standing, sitting on the floor, sitting on a "
        "seat, kneeling, crouching or lying) and which way the body faces "
        "the camera (front, side or back). Then describe the body position "
        "limb by limb: the head and where the gaze goes, the shoulders, the torso, "
        "the subject's left arm and right arm, the subject's left hand and "
        "right hand (what each one does), the hips, the subject's left leg "
        "and right leg, the subject's left foot and right foot, and where "
        "the weight rests. Each hand and each foot is in one place only: "
        "never put one hand in two places. Before you finish, read your "
        "sentences again and check that they agree with each other. If a "
        "hand, arm, leg or foot is hidden or cannot be seen, say that it is "
        "hidden instead of guessing. Always mean the subject's own left and "
        "right, not the left and right of the picture. Then "
        "describe the camera in four parts: the height (low, eye level or "
        "high), the side it sits on (front, left, right or behind), the "
        "distance (close, medium or far) and the direction it points. "
        "Never describe the mannequin or model itself: do not mention its "
        "surface, colour, build or face. Describe only the position of the "
        "body and the camera."
    ),
    "other": (
        "This picture is an extra reference. Describe what it shows: the "
        "main subject, the colours, the materials and surface detail, the "
        "layout, the lighting and the mood. Say what the picture could "
        "add to a new image."
    ),
}

_WRITER_SYSTEM = """\
You write one long image prompt for the MiniMax H3 Image model. You get a \
short draft from the user and notes about the reference pictures. Write in \
English, in full sentences, as one prompt of 250 to 450 words. Never write a \
keyword list. Do not open with a string of art-medium words. Give only the prompt: no \
greeting, no title, no explanation, no quotes.

The user's whole draft is already written word for word before your text. \
Never repeat or rewrite its sentences. Start directly with the subject. The \
word target above is for your part only.

Write these parts in this order, as plain paragraphs. Never write part \
numbers, part names or labels in the prompt: do not write lines such as \
"The subject:" or "The camera:". Just write the \
sentences.
1. The subject, from the head down to the hands: age and build, face, \
hair, clothing in one line, expression, then each hand. Later in the \
prompt, mention the key traits once more in other words, inside a sentence \
about something else; never write a separate summary such as \
"Same description:".
2. The outfit, garment by garment, with the colour, the specific material \
and the surface detail of each one (weave, sheen, stitching, wear).
3. The pose, described in the view and position the draft names: what each \
hand does, what each foot does, and where the weight rests. The draft's view \
and position win over the notes.
4. The camera: the height, the side, the distance, the direction it points, \
and how the frame is cropped.
5. The lighting, in its own sentence: where the light comes from, how hard or \
soft it is, and what it touches.
6. The background, with its colour and material.
7. A short closing list of what must not appear: three to six lines, one \
problem per line, each line about a different problem, each a short \
sentence such as "No extra fingers or limbs." and "No other people." Never \
repeat a line. Nothing comes after the closing list: stop there.

Rules:
- Write no <Picture N> tag, unless you repeat one of the draft's tags to \
point at a picture, exactly as written. Never write a tag that is not in the \
draft. If the draft has no tags, write none.
- The draft wins. If the draft and the notes disagree, follow the draft. If \
the draft says to leave something out, leave it out. The notes only add \
detail to the pose the draft names.
- A mannequin or model in a pose picture is only a position guide. Never \
describe its look: no surface, no colour, no build, no face. The character \
picture decides how the person looks.
- Every accessory is worn or carried in its usual place: a hat is on the \
head, a bag is held or worn on the shoulder. Never write that an item \
floats or hovers, even if the notes say so.
- Take the lighting and the background from the draft first, then from the \
notes. If neither has them, write one plain, neutral choice that fits the \
draft's style, such as soft even studio light or a plain light-grey backdrop.
- A note that says there is no picture means: use the draft's own words for \
that part.
- For the subject, the outfit and the pose, use only what the draft and the \
notes say and invent nothing. Do not invent names, brands or extra people.
- Notes for a picture with the role other are extra material: use them where \
they fit, as setting or prop detail. Never describe a person from them unless \
the draft says so.
- When two pictures have the same role, cover both inside that role's part, \
in slot order: the lower picture number first.\
"""


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise ValueError(f"Unknown role {role!r}; expected one of: {', '.join(ROLES)}")


def describe_system(role: str) -> str:
    """System text for describing one picture of the given role."""
    _check_role(role)
    return f"{_DESCRIBE_COMMON}\n\n{_DESCRIBE_ROLE[role]}"


def describe_user(role: str, draft: str) -> str:
    """User message asking for notes on this picture only."""
    _check_role(role)
    return (
        f"Write notes about this picture only. Its role is: {role}. "
        "Use short full sentences. Do not write any <Picture N> tags in "
        "your notes.\n\n"
        "The user's draft, for context only. Do not describe anything from "
        "the draft that you cannot see in this picture:\n"
        f"{draft}"
    )


def writer_system() -> str:
    """System text for the pass-2 writer."""
    return _WRITER_SYSTEM


def nude_block(age: AgeRange) -> str:
    """Extra writer instructions for a nude item whose character passed the
    adult check with the (low, high) estimated age."""
    low, high = age
    wording = f'"an adult woman aged {low} to {high}"'
    if high < 30:
        wording += ' or "an adult woman in her twenties"'
    banned = ", ".join(f'"{word}"' for word in YOUTH_WORDS + ("girl",))
    return (
        "Nude mode. The draft says the person is nude, and there is no outfit "
        "picture. In place of the outfit part, describe the unclothed adult "
        "body plainly: the build, the proportions, and the skin tone and skin "
        "texture, carrying on from the character notes, with natural adult "
        "anatomy. Write it in the register of a figure-drawing or photography "
        "reference: calm, factual and neutral. No sexual acts, no sexual "
        "poses, and no language about arousal or with an explicit focus on "
        "any part of the body; describe the pose only as a body position. "
        f"Call the person {wording}. If the character notes say the person "
        f'is a man, write "an adult man aged {low} to {high}" instead. Never '
        f"use these words: {banned}. No clothing, no footwear and no "
        "accessories, unless the draft names them."
    )


def adult_block(age: AgeRange) -> str:
    """Writer instructions for a draft that says nude while an outfit picture
    is connected: the outfit stays, the person is named as an adult."""
    low, high = age
    banned = ", ".join(f'"{word}"' for word in YOUTH_WORDS + ("girl",))
    return (
        "The draft mentions nudity. The person is an adult: call them "
        f'"an adult woman aged {low} to {high}", or "an adult man" if the '
        f"character notes say so. Never use these words: {banned}."
    )


def writer_user(
    lead: str,
    notes: List[Tuple[int, str, Optional[str]]],
    adult: Optional[AgeRange] = None,
) -> str:
    """User message: the written lead (whole draft) and per-picture notes.

    ``adult`` is the checked age range of a nude item; it adds nude_block.
    """
    in_draft = find_tags(lead)
    lines = []
    for slot, role, text in sorted(notes, key=lambda note: note[0]):
        label = f"<Picture {slot}> ({role})"
        if text is None and slot not in in_draft:
            continue
        if text is None:
            lines.append(
                f"Notes for {label}: no picture is connected; use the "
                "draft's own words for this part."
            )
        elif slot in in_draft:
            lines.append(f"Notes for {label}: {text}")
        else:
            lines.append(
                f"Notes for {label}, context only: {text} "
                "The draft does not use this tag, so do not write its tag."
            )
    notes_block = "\n".join(lines) if lines else "No notes."
    blocks = []
    if lead:
        blocks.append(
            "The whole draft is already written word for word at the start "
            "of the prompt. Do not repeat or rewrite it. Your job is the "
            "detail that follows it:\n" + lead
        )
    blocks.append(notes_block)
    if adult is not None:
        connected = [role for _, role, text in notes if text is not None]
        body = is_nude(lead, connected)
        blocks.append(nude_block(adult) if body else adult_block(adult))
    blocks.append("Write the final prompt now.")
    return "\n\n".join(blocks)


def retry_user(
    problems: Tuple[List[int], List[int]],
    blank: bool = False,
    banned: Optional[str] = None,
) -> str:
    """Short correction for an empty reply, missing and extra tags, and a
    word a nude prompt must not use."""
    missing, extra = problems
    parts = []
    if banned:
        parts.append(
            f'Your last prompt used the word "{banned}". Remove the word '
            f'"{banned}" and call the person an adult woman, or an adult man '
            "if the character notes say the person is a man."
        )
    if blank:
        parts.append(
            "Your last reply was empty or stopped before the prompt began. "
            "Do not think aloud; start the prompt at once."
        )
    if missing or extra:
        parts.append("Your last prompt had a problem with the picture tags.")
    if missing:
        names = ", ".join(f"<Picture {n}>" for n in missing)
        parts.append(f"These tags are missing and must appear exactly: {names}.")
    if extra:
        names = ", ".join(f"<Picture {n}>" for n in extra)
        parts.append(f"Remove these tags, the draft does not have them: {names}.")
    parts.append(
        "Write the whole prompt again, keeping every other rule, and give "
        "only the prompt."
    )
    return " ".join(parts)
