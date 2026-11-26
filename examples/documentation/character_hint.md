# Character Hint (Female / Male)

Two nodes that build a short text description of a character from dropdowns: **Character Hint (Female)** and **Character Hint (Male)**. The output is plain text. Use it to state traits a reference picture cannot show, or to change traits it does show.

**Category:** 🫶 ComfyAssets/🧠 Prompts

## What it does

Every field starts at `-`, which means unset. Only the fields you set are written. The node has one output, `hint` (STRING).

The hint is written in a fixed order: who the character is, then Body, Face, Makeup, Eyewear, Hair, Skin, Tattoos, Expression, Pose, Unclothed detail and Extra. The lead sentence is always there. It names the age and, if you set one, the heritage.

## How to wire it

- Connect `hint` to the `character_hint` input of the [H3 Reference Prompter](h3_reference_prompter.md#character-hint). See [How the hint and the picture combine](#how-the-hint-and-the-picture-combine).
- The hint is plain text, so you can also send it to a text preview node, or type a hint by hand and connect that instead. The prompter reads only the age ("aged N") and the "Unclothed detail:" sentence from the text. The rest goes to the writer as written.

## Fields

The female and male nodes share most fields. Fields that only one of them has are marked.

### Body

| Field | Notes |
|-------|-------|
| `age` | Slider from 18 to 90, default 25. Always written |
| `heritage` | 64 choices, such as Japanese, Brazilian, Nigerian, Polish. Written in the lead sentence |
| `body_type` | Different lists. Female: Slim, Muscular, Curvy, Voluptuous, Chubby, Heavyset, Obese. Male: Lean, Ripped, Jacked, Powerlifter, Dad bod, Heavyset |
| `breast_size` | Female only. Small, Large, Very large |
| `butt_size` | Female only. Flat, Large, Very large |

### Face

| Field | Notes |
|-------|-------|
| `face_shape` | Round, Oblong, Square or Heart-shaped |
| `facial_structure` | Angular jawline, Soft jawline, High cheekbones, Cleft chin. Written after the face shape |
| `eye_color` | 12 colors, from Dark brown to Violet, Silver and Pink |
| `eye_shape` | Monolid, Hooded, Deep-set |
| `eye_detail` | Defined eyelashes, Fine lines, Gold flecks, Heterochromia, Bloodshot |
| `eyebrows` | High arch or Thick |
| `nose` | Small, Button, Upturned, Very large |
| `lip_shape` | Female: Thin, Full, Wide, Cupid's bow. Male: Thin, Full |
| `facial_hair` | Male only. 8 choices, such as Clean shaven, Stubble, Goatee, Full beard. Clean shaven asks for no beard, mustache or stubble |
| `dimples` | Subtle or Deep |

### Makeup

Female only.

| Field | Notes |
|-------|-------|
| `makeup` | 40 styles, such as No makeup, Natural, Soft glam, Gothic, 1950s pin-up, Soft Korean, Gyaru, Smokey eye, Cat eye, Glitter, Classic red lip. Each style has its own look and lips |
| `lip_color` | 13 colors, such as Natural, Coral, Berry, Red, Burgundy, Black. With a makeup style, the color replaces that style's lips. Without one, "<color> lips" goes in the Face part |

### Eyewear

Both nodes. Written as its own "Eyewear:" part, after Makeup and before Hair.

| Field | Notes |
|-------|-------|
| `eyewear` | Thin wire frames, Thick acetate frames, Round glasses, Sunglasses, No glasses |

### Hair

| Field | Notes |
|-------|-------|
| `hair_color` | 28 choices, such as Black, Chestnut, Auburn, Copper, Strawberry blonde |
| `hair_texture` | Pin-straight, Loosely wavy, Curly, Tightly coiled. Written after the hair color |
| `hair_length` | Female only. Buzzed, Chin length, Shoulder length, Long |
| `hair_style` | Different lists. Female has 35, such as Bob, Pixie cut, Shag cut, Three-strand braid. Male has 19, such as Buzz cut, High fade, Pompadour |
| `bangs` | Female only. Curtain, Side-swept, Wispy, Blunt, No bangs |

### Skin

| Field | Notes |
|-------|-------|
| `skin_tone` | 12 choices, from Porcelain to deeper tones, including Olive |
| `tan` | Light tan or Deep tan |
| `freckles` | A few, Prominent or No freckles |
| `acne` | A few blemishes, Some acne, Pronounced acne |
| `beauty_mark` | Left cheek or Right cheek |

### Other

| Field | Notes |
|-------|-------|
| `tattoo` | Small, Sleeve, Neck or Hand tattoo, or No tattoos |
| `expression` | 33 choices, such as Neutral, Smiling, Amused, Playful, Sad, Tired, Relieved |
| `head_angle` | Facing forward, Three-quarter left or right, Full profile left or right, Chin raised, Chin lowered, Tilted left or right. Written in the "Pose:" part, see [Pose](#pose) |
| `gaze` | Into the lens, Up, Down, Off-camera left or right. Written in the "Pose:" part |
| `nipples`, `areola` | Female only. Written as "Unclothed detail:", see [Unclothed detail](#unclothed-detail) |
| `extra` | Free text. It is trimmed and a full stop is added unless it already ends with `.`, `!` or `?`. Text with no letter or digit adds nothing |

## Pose

`head_angle` and `gaze` are written as one "Pose:" part, after Expression, for example "Pose: head in three-quarter view, with the nose pointing toward the left edge of the image, eyes looking downward." Left and right are as seen in the image. With the prompter, Pose options override the pose picture for the head and eyes only. The rest of the pose still comes from the draft and the pose notes.

## The "No ..." options

`No tattoos`, `No freckles`, `No bangs`, `No glasses` and the Clean shaven option of `facial_hair` ask the prompt to drop a trait the reference picture has. With the prompter, the writer leaves the trait out and says plainly that the person has none. The image model may still copy the trait from the reference picture, so the picture is not guaranteed to follow.

## Example output

Female, with a number of fields set:

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

The output is one paragraph. The line breaks above are only for reading. The `...` stands for the rest of the soft glam look.

## How the hint and the picture combine

With the H3 Reference Prompter, the traits in the hint win over the character picture's notes. The picture fills in what the hint leaves unset. For example, a hint that sets only `eye_color` to Green changes the eyes and keeps everything else the picture shows.

The prompter also writes the hint into the final prompt word for word, right after the draft, so every selected trait reaches the image model. The writer adds detail around it and does not repeat it.

## Age rule

The age slider starts at 18. The Prompter checks the age of the character before it writes a nude draft (a draft that says nude or naked, with no outfit picture).

- With no character picture, the hint's age is what the draft is checked against. An age of 18 or more passes. A hint with no age is refused.
- With a character picture, the picture's age estimate still decides. The hint cannot override it. A picture that may show someone under 20 is refused whatever the hint says. When the picture passes, the prompt uses the hint's age.
- A youth word in the hint (teen, child, minor and the like) stops the run, as it does in the draft.
- A nude draft is refused when the draft or the hint states an age under 18 (such as "12 years old" or "aged 15"), and a hand-typed hint must start with a sentence like "The character is an adult woman aged 25." for its age to count.

See [Nude mode](h3_reference_prompter.md#nude-mode).

## Unclothed detail

`nipples` and `areola` are written as "Unclothed detail:". The prompter uses that sentence only when the draft says nude or naked and no outfit picture is connected. In any other case it removes the sentence before the writer sees the hint.

## Your own options

The shipped lists are in `kikotools/tools/character_hint/options.json`. Do not edit that file, because a pack update replaces it.

To change the lists, make this file instead: `ComfyUI/user/kikotools/character_hint.json`. It survives updates. A copy of the example below ships as `character_hint.example.json` in the same folder as `options.json`.

```json
{
  "heritage": {
    "Maori": "Maori"
  },
  "makeup": {
    "Festival glitter": {
      "look": "festival makeup, scattered face gems, bright glitter eyeshadow, bold liner",
      "lips": "glossy coral lips"
    }
  },
  "hair_color": {
    "Copper": "bright copper hair"
  },
  "tattoo": {
    "Sleeve tattoo": null
  }
}
```

How it works:

- Each key is a table name, such as `heritage`, `makeup`, `hair_color` or `tattoo`. The names are the keys in `options.json`.
- Inside a table, `"Label": "phrase"` adds a new option at the end of the list. If the label already exists, it changes the phrase and keeps the position.
- `"Label": null` removes the option.
- `makeup` is different. Each style is an object with a `look` and `lips`, both required.
- You cannot change `-`, the age limits, or empty a whole table.
- A bad entry is skipped and a warning goes to the ComfyUI log. It starts with "Character Hint options" and names the file. The other entries still apply.
- Refresh the browser page to see your edits in the dropdowns. You do not need to restart ComfyUI.
- If you remove an option, a saved workflow that used it fails with an error that names the field.

The shipped options were tested against MiniMax H3 Image. Your own additions were not.

## Tested options

Every option was tested against MiniMax H3 Image, and only options the model draws are in the lists. Some choices were left out on purpose because the model ignores them: height, waist, breast shape, face shapes other than round, oblong, square and heart-shaped, and pupils.

Code: `kikotools/tools/character_hint/`.
