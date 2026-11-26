# H3 Reference Prompter

Writes one long prompt for MiniMax H3 Image from a short draft and up to three reference pictures, using a local vision model. Nothing leaves your machine.

**Category:** 🫶 ComfyAssets/🧠 Prompts

## What it does

You write a short draft that names the pictures with tags, such as `<Picture 1> is the character. <Picture 2> is the outfit. <Picture 3> is the pose.` The node looks at each picture, then writes a detailed prompt that describes the subject, outfit, pose, camera, lighting and background.

The draft's sentences that carry a `<Picture N>` tag are written at the start of the prompt unchanged. The model writes everything after them. Draft instructions win over what the pictures show, for example "leave out the shoes" or a style sentence.

## Inputs

| Input | Notes |
|-------|-------|
| `prompt` | The draft. Tags `<Picture 1>` to `<Picture 3>` are kept exactly |
| `model` | The vision model, see [Models](#models) |
| `role_1`, `role_2`, `role_3` | What each picture shows: `character`, `outfit`, `pose` or `other`. Defaults: character, outfit, pose |
| `seed` | Base seed |
| `image_1` to `image_3` | Optional pictures. `image_N` is always `<Picture N>`; slots are never renumbered |
| `temperature` | Advanced, default 0.7 |
| `describe_tokens` | Advanced, default 512. Length limit for each picture description |
| `write_tokens` | Advanced, default 1536. Length limit for the written prompt |
| `keep_loaded` | Advanced, default off. Keep the prompt model in memory after the run |

A picture slot must hold one image. A batch of more than one image in a slot stops with an error naming the slot.

## Outputs

`prompt` and `notes`. Both are lists, with one entry per item. The notes hold the description of each picture, labelled with its tag and role.

The panel on the node shows each prompt with its word count, previous and next buttons, a copy button and collapsible notes.

## Picture tags

The prompt must contain exactly the tags the draft has. If the model drops or adds a tag, the node retries once. If the tags are still wrong, it stops with an error naming the missing and unexpected tags. A draft with no tags at all works too, and the prompt then has none.

## Two passes

1. Each picture is described once, according to its role. The description is cached for the ComfyUI session, so the same picture, role and model are not described again.
2. The prompt is written from the draft and the descriptions.

The pose description never describes the mannequin's own look (surface, colour, build, face), only the pose.

## One prompt per pose

When `prompt` and `image_3` arrive as lists, for example from a pose picker that returns several poses, the node writes one prompt per item. Single values, such as one character and one outfit, are used for every item and described once. Each item gets its own prompt and notes. The seed of each item is the base seed plus the item index. The model loads once for the whole run.

## Models

The picker lists three kinds of model:

- `hf: <folder>`: transformers folders under `ComfyUI/models/LLM`, searched recursively, whose `config.json` lists a Qwen3.5, Qwen3-VL or Gemma 4 vision architecture. For example:
  - `ComfyUI/models/LLM/Qwen-VL/Qwen3.5-4B-Unredacted-MAX/` from https://huggingface.co/prithivMLmods/Qwen3.5-4B-Unredacted-MAX
  - a Gemma 4 E4B folder from https://huggingface.co/collections/huihui-ai/gemma-4-abliterated
- `native: <file>`: the vision text encoders that the Kiko Prompt Enhancer lists.
- `gguf: <file>`: GGUF models that have an `mmproj` file. If a GGUF model fails to load, the node tells you to use a transformers folder instead.

A workflow saved with a model this machine does not have still loads. It stops when it runs, with a message naming the model and the folders searched.

## Memory

Before the model loads, the node frees ComfyUI's loaded models with the same safe unload as Kiko Purge VRAM. Afterwards it unloads the prompt model, unless `keep_loaded` is on.

## Example

Draft:

```
<Picture 1> is the character. <Picture 2> is the outfit. <Picture 3> is the pose.
Draw the character from <Picture 1> in the pose of <Picture 3>, dressed in the
outfit from <Picture 2>. Photorealistic studio photograph, soft even lighting.
```

The prompt it writes (shape, with a short excerpt) has these parts, in order:

1. The draft's reference sentences, unchanged.
2. The subject, from head to hands.
3. The outfit, garment by garment.
4. The pose, with each hand and foot.
5. The camera: height, side, distance, direction and framing.
6. A lighting sentence: source, hardness and what it touches.
7. The background.
8. The draft's style sentence.
9. A short closing list of what must not appear, one problem per line.

Excerpt:

> She wears a cream-colored off-the-shoulder ribbed knit top with a ruffled neckline edged in delicate eyelet lace, a fitted silhouette; over it, a beige trench coat made of smooth fabric with a loose double-breasted cut ... Shot from a medium distance at eye level, camera positioned directly in front and pointing straight ahead, framing her from head to toe without cropping any extremities. Soft even studio lighting illuminates her evenly from the front, casting minimal shadows ... No extra fingers or limbs. No other people.

The target length is 250 to 450 words, in English.

## Example workflow

[h3_reference_prompter_charsheet_test.json](../workflows/h3_reference_prompter_charsheet_test.json) uses the [KikoCharSheet](https://github.com/ComfyAssets/ComfyUI-KikoCharSheet) pickers for the portrait, costume and poses. It shows the draft, the prompt and the notes in Display Text nodes and does not draw an image.
