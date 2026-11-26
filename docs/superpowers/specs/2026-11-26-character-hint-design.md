# Character Hint nodes: design

## Intent

The H3 Reference Prompter can only describe what its reference picture
shows. A user wants to state traits the picture cannot show, or wants to
change (body under clothes, eye colour, makeup, hair). Two new nodes build a
"character hint" from dropdowns, and the prompter takes that hint as an
optional input that steers its writer.

Inspired by the Female Person and Male Person nodes of
`comfyui-character-prompt-builder`. Our own code, our own word lists, no
credit line.

## Goals

- **Character Hint (Female)** and **Character Hint (Male)**: dropdown fields,
  one plain STRING output `hint`.
- H3 Reference Prompter: optional `character_hint` input. Traits in the hint
  win over the character picture's notes; the picture fills in the rest.
- US English ("butt").
- Only options MiniMax H3 Image really draws. Every option was A/B tested;
  results are in `output/charsheet/hint-tests-sheets/notes.md` on the
  maintainer's machine. `kikotools/tools/character_hint/options.py` is the
  result and is already written: it is the source of truth for the lists.

## Non-goals

- No custom socket type, no frontend code: standard widgets only.
- No outfit, pose, scene or camera fields. KikoCharSheet covers those.
- No height, waist, breast shape, pupil or nationality-mix fields: the model
  ignores them.

## Anti-goals

- The age slider must never let a nude draft through when a connected
  character picture reads as under-age. The picture check stays as it is.
- The hint must not weaken the youth-word refusal.

## Approaches

1. **Plain text hint, parsed lightly by the prompter (chosen).** The hint
   nodes write sentences; the prompter reads only two things from the text:
   the age ("aged N") and the "Unclothed detail:" sentence. Works with any
   node that takes text, and a hand-typed hint works too.
2. A custom `CHARACTER_HINT` dict type. Stricter, but the hint could then be
   used only with our prompter, and it cannot be previewed with a text node.
3. One node with a gender switch that hides fields in the frontend. Needs
   frontend code for no gain; the user chose two nodes.

## The hint text

`build_hint` writes, in this order, only the parts that have a value:

```
The character is an adult Japanese woman aged 25. Body: a curvy body, large
breasts, a large butt. Face: a round face, green eyes, hooded eyes, eyes
framed by defined eyelashes, a button nose, full lips, deep dimples. Makeup:
wearing soft glam makeup, ..., and berry lips. Hair: copper hair, chin length
hair, her hair in a bob cut, curtain bangs. Skin: olive skin, a hint of a tan,
a few freckles, a single beauty mark on the left cheek. Tattoos: a sleeve
tattoo. Expression: a smirking expression. Unclothed detail: large areolas,
pierced nipples. Extra: <free text>.
```

- Lead sentence: "The character is an adult [heritage ]woman|man aged N."
  Always present.
- Parts are "Label: phrase, phrase." Phrases come from the tables, joined
  with ", ".
- Makeup: "wearing <look>, and <lips>". When a lip colour is chosen it
  replaces the style's lips: "and <colour> lips". With a lip colour and no
  makeup style the Face part gets "<colour> lips".
- Facial hair (male) goes in the Face part.
- "Unclothed detail:" holds nipples and areola (female only).
- "Extra:" holds the node's free-text field, trimmed; a missing final full
  stop is added.

## Fields

Every dropdown starts with `-` (unset, the default). Tables are in
`options.py`.

- Both: `age` (INT slider 18 to 90, default 25), `heritage`, `body_type`,
  `face_shape`, `eye_color`, `eye_shape`, `eye_detail`, `nose`, `lip_shape`,
  `hair_color`, `hair_style`, `skin_tone`, `tan`, `freckles`, `acne`,
  `beauty_mark`, `dimples`, `tattoo`, `expression`, `extra` (multiline text).
- Female only: `breast_size`, `butt_size`, `lip_color`, `makeup`,
  `hair_length`, `bangs`, `nipples`, `areola`.
- Male only: `facial_hair`.

## Prompter changes

- New optional input `character_hint` (STRING, `forceInput`), a list like the
  other inputs and paired per item.
- The writer's message gets a block after the picture notes: the hint's
  traits win over the character notes; the writer works them into the
  subject sentences instead of copying the list.
- "Unclothed detail:" is removed from the hint unless the item is in nude
  mode (draft says nude or naked and no outfit picture).
- Age and nude drafts:
  - A character picture is connected: nothing changes. The picture's
    estimate must pass (`NUDE_MIN_AGE`). When it passes and the hint gives an
    age, the wording uses the hint's age.
  - No character picture, hint gives an age of 18 or more: the item passes
    and the wording uses that age.
  - No character picture and no age in the hint: refused as today.
  - The youth-word check also reads the hint.
- With one age the wording is "an adult woman aged 25", not "25 to 25".

## Left to the builder

Test layout, helper names inside the modules, and the exact instruction
wording, within the rules above.
