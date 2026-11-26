# H3 Reference Prompter

Writes one long prompt for MiniMax H3 Image from a short draft and up to three reference pictures, using a local vision model. Nothing leaves your machine.

**Category:** 🫶 ComfyAssets/🧠 Prompts

## What it does

You write a short draft that names the pictures with tags, such as `<Picture 1> is the character. <Picture 2> is the outfit. <Picture 3> is the pose.` The node looks at each picture, then writes a detailed prompt that describes the subject, outfit, pose, camera, lighting and background.

The whole draft is written at the start of the prompt, word for word, one line per draft line. The model adds the detail after it: subject, outfit, pose, camera, lighting and background. If the model repeats a draft sentence, the repeat is dropped. Draft instructions win over what the pictures show, for example "leave out the shoes" or a style sentence.

## Inputs

| Input | Notes |
|-------|-------|
| `prompt` | The draft. Tags `<Picture 1>` to `<Picture 3>` are kept exactly |
| `model` | The vision model, see [Models](#models) |
| `role_1`, `role_2`, `role_3` | What each picture shows: `auto` (default), `character`, `outfit`, `pose` or `other`. See [Roles](#roles) |
| `seed` | Base seed |
| `image_1` to `image_3` | Optional pictures. `image_N` is always `<Picture N>`; slots are never renumbered |
| `temperature` | Advanced, default 0.7 |
| `describe_tokens` | Advanced, default 512. Length limit for each picture description |
| `write_tokens` | Advanced, default 1536. Length limit for the written prompt |
| `keep_loaded` | Advanced, default off. Keep the prompt model in memory after the run. A kept `hf:` model sits outside ComfyUI's memory management |

A picture slot must hold one image. A batch of more than one image in a slot stops with an error naming the slot.

## Roles

`auto` reads each slot's role from the draft's sentences `<Picture N> is the character.`, `<Picture N> is the outfit.` and `<Picture N> is the pose.` (in any case; KikoCharSheet's Chinese sentences, such as `<Picture 2>是姿势。`, are read too). A slot the draft does not name falls back to its old default: `image_1` character, `image_2` outfit, `image_3` pose. A role you pick by hand always wins over `auto`.

Roles are read per item, so each draft of a one-per-pose run gets its own. The notes and the notes cache use the role that was read.

KikoCharSheet numbers only the pictures that are present, in the order character, outfit, pose. Without an outfit picture (the Nude costume) the pose is `<Picture 2>`, and `auto` describes it as a pose. A workflow saved with fixed roles keeps them; set the roles to `auto` to follow the draft.

## Outputs

`prompt` and `notes`. Both are lists, with one entry per item. The notes hold the description of each picture, labelled with its tag and role.

The panel on the node shows each prompt with its word count, previous and next buttons, a copy button and collapsible notes.

## Picture tags

The prompt must contain exactly the tags the draft has. The draft itself opens the prompt, so its tags are always there; if the model adds a tag the draft does not have, the node retries once, then stops with an error naming the unexpected tags. A draft with no tags at all works too, and the prompt then has none.

The draft's sentences end at `.`, `!`, `?` and at line breaks; a short title such as `Dr.` or `Mrs.` does not end a sentence. The draft keeps its lines. Fragments with no letter or digit, such as a stray lone period, are left out.

If the model writes nothing after the draft (an empty reply, or one cut off inside its thinking), the node retries once, together with any tag problem. If it is still empty, it stops with an error naming the model; raise `write_tokens` or pick another model. A run with an empty draft and no picture stops at once with an error.

## Two passes

1. Each picture is described once, according to its role. Pictures are scaled down to about 1 MP (1,048,576 pixels) for this; smaller ones keep their size. The description is cached for the ComfyUI session, so the same picture, role, model and `describe_tokens` are not described again.
2. The prompt is written from the draft and the descriptions.

With a transformers (`hf:`) model both passes run in batches. All the pictures of a run that are not cached yet are described in one batch, and all the prompts are written in another. Only prompts with wrong tags or no text are retried, together in one more batch. Batches hold at most four requests. Batching needs transformers 5 or newer, and only Qwen3-VL and Qwen3.5 folders run batched; with an older transformers or another architecture, such as Gemma 4, the same requests run one at a time, in the same order. GGUF and native models run one call at a time.

The pose description never describes the mannequin's own look (surface, colour, build, face), only the pose.

## Nude mode

KikoCharSheet's 18+ mode has a costume with no picture, Nude. It writes "The character's outfit: completely nude, wearing no clothing and no footwear." into the draft and sends no outfit picture.

A blank placeholder picture (a small, uniformly white image, such as KikoCharSheet's Nude costume image) counts as no picture: it is not described and does not count for roles or nude detection.

**Detection.** Two checks look at each item's draft:

- **Age check and word check:** they run whenever the draft contains `nude` or `naked` (whole word, any case) or the Chinese `裸`, whatever the roles and pictures are. The draft is copied into the prompt, so its nude wording reaches the image model either way. A workflow with fixed roles, or a draft such as "nude lipstick" with an outfit picture, is checked too.
- **Body section:** it is written only when, in addition, no connected picture has the outfit role. With an outfit picture, the outfit is described as usual and the writer is only told the person is an adult.

**Body section.** In nude mode the writer gets one more instruction block. In place of the outfit part, it describes the unclothed adult body plainly: build, proportions, skin tone and skin texture following the character notes, and natural adult anatomy, in the register of a figure-drawing or photography reference. It writes no sexual acts, no sexual poses and no arousal or explicit-focus language, and adds no clothing, footwear or accessories unless the draft names them. The person is called an adult woman aged N to M (or "in her twenties" when the range lies there), or an adult man when the character notes describe a man. All other writer rules still apply.

**Age check.** The character describer always ends its notes with `Estimated age: N to M years.` In nude mode the node checks every item after the pictures are described and before anything is written. It stops the run with an error when:

- no character picture is connected;
- the estimate is missing or cannot be read;
- the lower bound is under 20, so a picture whose estimate could be under 20 is refused;
- the character notes use a youth word: teen, teenage, teenager, adolescent, schoolgirl, child, childlike, kid, minor, underage or loli (whole words, any case, plurals included, so "late teens" counts);
- the draft uses one of those words.

The error says that nude prompts need an adult character picture whose estimated age is 20 or older, and gives the estimate it found. Nothing is written for any item; like other errors, ComfyUI's model list is repaired and the prompt model is freed.

**Output check.** After writing, the model's part (not the draft) must not contain a youth word. A hit is retried once, together with any tag problem, with a message naming the word. If the word is still there, the run stops with an error. Outside nude mode, nothing is checked. The word "girl" is never checked.

The age estimate comes from the vision model and can be wrong. The check refuses doubtful pictures; it does not prove anyone's age.

**Real people.** Never use pictures of real people for nude prompts. KikoCharSheet's gallery portraits are AI-generated; an uploaded portrait may show a real person, so never combine an upload with Nude.

## One prompt per pose

When `prompt` and `image_3` arrive as lists, for example from a pose picker that returns several poses, the node writes one prompt per item. Single values, such as one character and one outfit, are used for every item and described once. Each item gets its own prompt and notes. The model loads once for the whole run.

Seeds: one batched call samples with one seed, so with a transformers model every item uses the base seed, and the same inputs and seed still give the same prompts. With GGUF and native models, which run one call at a time, the seed of each item is the base seed plus the item index.

## Models

The picker lists three kinds of model:

- `hf: <folder>`: transformers folders under `ComfyUI/models/LLM`, searched recursively, whose `config.json` lists a Qwen3-VL, Qwen3.5 or Gemma 4 vision architecture. For example:
  - Recommended: `ComfyUI/models/LLM/Qwen-VL/Huihui-Qwen3-VL-8B-Instruct-abliterated/` from https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated. It gave the best images in side-by-side tests. It uses about 17 GB of VRAM while it runs; ComfyUI's models are freed first.
  - `ComfyUI/models/LLM/Qwen-VL/Qwen3.5-4B-Unredacted-MAX/` from https://huggingface.co/prithivMLmods/Qwen3.5-4B-Unredacted-MAX
  - a Gemma 4 E4B folder from https://huggingface.co/collections/huihui-ai/gemma-4-abliterated
- `native: <file>`: the vision text encoders that the Kiko Prompt Enhancer lists.
- `gguf: <file>`: GGUF models that have an `mmproj` file. A GGUF model loads twice per run: with its `mmproj` to describe the pictures and without it to write the prompts. If a GGUF model fails to load, the node tells you to use a transformers folder instead.

The picker defaults to a name containing `Huihui-Qwen3-VL-8B-Instruct-abliterated`, then any name containing `Qwen3-VL-8B`, then the first `hf:` entry, then the first entry.

A workflow saved with a model this machine does not have still loads. It stops when it runs, with a message naming the model and the folders searched, and reminding you that the model must be a vision model and that a GGUF needs its `mmproj`.

## Memory

Before the model loads, the node frees ComfyUI's loaded models with the same safe unload as Kiko Purge VRAM. A prompt model kept from an earlier run on another backend (for example an `hf:` model when this run uses a GGUF) is freed too, even with `keep_loaded` on. Afterwards the node unloads the prompt model, unless `keep_loaded` is on. A kept `hf:` model sits outside ComfyUI's memory management: ComfyUI cannot free it when it needs room, and Kiko Purge VRAM does not free it either. To get that memory back, turn `keep_loaded` off and run the prompter again.

## Example

Draft:

```
<Picture 1> is the character. <Picture 2> is the outfit. <Picture 3> is the pose.
Draw the character from <Picture 1> in the pose of <Picture 3>, dressed in the
outfit from <Picture 2>. Photorealistic studio photograph, soft even lighting.
```

The prompt it writes (shape, with a short excerpt) has these parts, in order:

1. The whole draft, written word for word by the node.

Then the model's part:

2. The subject, from head to hands.
3. The outfit, garment by garment.
4. The pose, in the view and position the draft names, with each hand and foot.
5. The camera: height, side, distance, direction and framing.
6. A lighting sentence: source, hardness and what it touches.
7. The background.
8. A short closing list of what must not appear, one problem per line.

Excerpt:

> She wears a cream-colored off-the-shoulder ribbed knit top with a ruffled neckline edged in delicate eyelet lace, a fitted silhouette; over it, a beige trench coat made of smooth fabric with a loose double-breasted cut ... Shot from a medium distance at eye level, camera positioned directly in front and pointing straight ahead, framing her from head to toe without cropping any extremities. Soft even studio lighting illuminates her evenly from the front, casting minimal shadows ... No extra fingers or limbs. No other people.

The target length for the model's part is 250 to 450 words, in English.

## Example workflow

[h3_reference_prompter_charsheet_test.json](../workflows/h3_reference_prompter_charsheet_test.json) uses the [KikoCharSheet](https://github.com/ComfyAssets/ComfyUI-KikoCharSheet) pickers for the portrait, costume and poses. It shows the draft, the prompt and the notes in Display Text nodes and does not draw an image.
