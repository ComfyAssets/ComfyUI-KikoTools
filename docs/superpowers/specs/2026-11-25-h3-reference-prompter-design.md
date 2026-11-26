# H3 Reference Prompter: design

## Intent

Writing a good MiniMax H3 Image prompt for a character built from reference
pictures takes long, precise prose. Today the maintainer types a short prompt by
hand in the KikoCharSheet workflows, for example:

> <Picture 1> is the character. <Picture 2> is the outfit. <Picture 3> is the
> pose. Draw the character from <Picture 1> in the pose and camera angle of
> <Picture 3>; the mannequin is only a pose guide, not an appearance reference.
> Dress the character in the complete outfit from <Picture 2>, copying every
> garment, colour and material exactly from that picture. Photorealistic studio
> photograph, real person, natural skin texture, soft even lighting. Full body
> from head to toe, plain light grey studio background. . The pose: Low angle
> view, pose: Leaning-back sit, one knee raised (Sitting)

H3 Image does best with far longer, finer prompts. The new KikoTools node looks at
the reference face, the outfit and the pose, and rewrites the short prompt into a
very descriptive H3 Image prompt that keeps the `<Picture N>` reference tags. It
runs on a local model that reads both text and images.

Inspiration: ComfyUI-MiniMax-H3-Promptor (1038lab), whose reference mode describes
each reference with a vision model before writing the prompt. That pack targets H3
video and is GPL-3.0; only the idea is borrowed (see Constraints).

## Who uses it, and where

The maintainer, in the KikoCharSheet workflows (pose sheet and one-per-pose), on an
RTX 4090 (24 GB) running ComfyUI with `--disable-dynamic-vram`. The node sits
between the pickers and `MiniMaxH3ImageConditioning`, whose `images` inputs are
labelled `<Picture 1>`, `<Picture 2>`, … in input order.

## Goals

1. **Look at the references.** For each connected picture, describe what it shows
   for its role:
   - **character:** age range, build, face shape, eyes, brows, nose, lips, skin
     tone and texture, hair (colour, length, style, parting), distinctive marks,
     expression. Nothing about clothing or background.
   - **outfit:** every garment from top to bottom, each with colour, material,
     fit, construction details (seams, buttons, trims, prints), then accessories
     and footwear.
   - **pose:** the body position limb by limb (head and gaze, shoulders, torso,
     each arm, each hand, hips, each leg, each foot, where the weight rests), and
     the camera: height, side, distance and direction. The mannequin's own look
     (surface, colour, build, face) is never described.
2. **Write the H3 prompt.** One long English prompt in full sentences, in the
   order the guides recommend:
   1. the draft's reference sentences, keeping every `<Picture N>` tag exactly;
   2. the subject, head to hands, from the character notes, with key traits said
      in more than one way;
   3. the outfit, garment by garment, with materials and surface detail;
   4. the pose, with what each hand and foot does;
   5. the camera: height, side, distance, direction, and framing;
   6. a lighting sentence: source, hardness, what it touches;
   7. the background;
   8. the draft's style sentence;
   9. a short closing list of what must not appear (one problem per line, such as
      "No extra fingers or limbs", "No other people").
   Target 250 to 450 words.
3. **Respect the draft.** Instructions in the draft win over the model's notes,
   for example "leave out the shoes", a style sentence, or a pose name. The pose
   name from the draft is kept and the notes add detail to it.
4. **Many poses in one run.** In the one-per-pose workflow the pose input is a
   list. The model loads once per node run, the character and outfit pictures are
   described once, and each pose gets its own description and prompt.
5. **Any text-and-vision model from one picker.** Hugging Face model folders under
   `models/LLM` (searched recursively, so `models/LLM/Qwen-VL/<name>/` works),
   such as Qwen3.5-4B-Unredacted-MAX and Gemma 4 E4B, plus the vision-capable
   models the Kiko Prompt Enhancer already lists (single-file Qwen3-VL and
   Qwen3.5 text encoders, GGUF with an `mmproj`).
6. **Free the GPU around generation.** Before loading, free ComfyUI's loaded
   models with the safe unload from Kiko Purge VRAM (PR #140); after the run,
   unload the prompt model unless `keep_loaded` is on.

## Non-goals

- H3 video prompts (timed shots, audio, music), the Promptor's other task modes,
  its composer and editor, and cloud providers.
- Chinese output.
- Downloading models; the README says where to put them.
- Generating images; the node only writes text.
- Changing the Kiko Prompt Enhancer's behaviour.

## Anti-goals (a failure even if it runs)

- Inventing details the pictures do not show, or contradicting them.
- Describing the pose mannequin's appearance, so H3 copies the mannequin's look.
- Dropping, renumbering or adding `<Picture N>` tags.
- Keyword lists or a style string at the start instead of sentences.
- Overriding an explicit instruction in the draft.
- Leaving a model resident so the H3 image model runs out of memory.

## Constraints

- **Licence.** KikoTools is MIT. ComfyUI-MiniMax-H3-Promptor and ComfyUI-QwenVL
  are GPL-3.0. Write our own code and our own instruction text; copy nothing from
  either. No credit line for it in the README or the node (maintainer's decision).
- **Runtime.** The maintainer's ComfyUI has transformers 5.19 (supports `qwen3_5`,
  `qwen3_vl`, `gemma4`, `gemma4_unified`) and llama-cpp-python 0.3.36 (Gemma 4
  vision through it is unverified). Use bf16 on CUDA; CPU only as a slow fallback.
- **Memory.** The H3 image model uses about 18 GB on a 24 GB card, so the prompt
  model must be out of VRAM before it loads.
- **KikoTools conventions.** New tool under `kikotools/tools/`, `ComfyAssetsBaseNode`,
  category `🫶 ComfyAssets/🧠 Prompts`, the web UI toolkit in `web/ui/`
  (`core.js`, `controls.css`), tests that need no GPU, coverage floor 85%.

## Approaches

1. **A new KikoTools node sharing the Prompt Enhancer's model code (chosen).**
   Reuses its model picker, unloading and GGUF path; adds a loader for Hugging
   Face folders; two passes (describe each picture, then write). Small models
   describe one picture at a time far better than three at once.
2. A new style inside the Prompt Enhancer. Least new code, but it takes one image,
   it is built to restyle prompts for a base model, and its loader cannot read the
   Hugging Face folders.
3. Delegate to ComfyUI-QwenVL as the Promptor does. No model code, but a GPL
   dependency, Qwen only (no Gemma 4), and coupled to another pack's internals.

## Decided

- Node name **H3 Reference Prompter**, node id `KikoH3ReferencePrompter`. (My
  call; the maintainer can rename.)
- **Inputs:** `prompt` (the draft, multiline), `model` (picker), `image_1`,
  `image_2`, `image_3` (optional, mapped to `<Picture 1>`–`<Picture 3>`), a role
  per image (`character`, `outfit`, `pose`, `other`; defaults character, outfit,
  pose, matching KikoCharSheet), `seed`, and advanced `temperature`,
  `max_length`, `keep_loaded`. (Explicit roles are my call: a 4B model inferring
  roles from the draft is the likelier failure.)
- **Outputs:** `prompt` (the H3 prompt) and `notes` (the per-picture
  descriptions, for checking what the model saw).
- **Two passes**, as above. Pass 1 caches each picture's notes by image content,
  role and model, so list runs describe the character and outfit once.
- **Tag check.** The result must contain every `<Picture N>` tag of the draft and
  no others. If it does not, retry once; if it still fails, raise an error naming
  the missing or extra tags rather than returning a broken prompt.
- Thinking or reasoning output is turned off where the model supports it and
  stripped if present.
- **Frontend:** the node shows the last prompt with a copy button and a
  collapsible notes panel, built with `web/ui/core.js` and `controls.css` like the
  other KikoTools nodes.

## Builder questions, settled (all marked as my calls unless noted)

- **Safe unload (#140).** Build on `feat/purge-vram-match-pixaroma` until PR #140
  merges, then merge main in. Call `unload_models_safely()` from
  `kikotools/tools/kiko_purge_vram/logic.py` before loading the prompt model; on a
  failed load or generation, call `repair_loaded_models()` before re-raising. Do
  not fall back to a bare `mm.unload_all_models()`. If #140 has not merged when
  this is ready, this PR waits for it.
- **Lists.** Fact from the one-per-pose workflow (KikoCharSheet
  `kiko-charsheet-one-per-pose-v2.json`): the Pose Picker outputs `poses` (images)
  and `pose_prompts_en` (texts) as lists, and the prompt is built by joining the
  prompt body with each pose text, so `prompt` and `image_3` both arrive as lists
  of the same length. The node takes every input as a list (`INPUT_IS_LIST`);
  each input of length 1 is used for every item; inputs longer than 1 must share
  one length, else the node raises an error naming the lengths. Outputs are lists
  (`OUTPUT_IS_LIST`) with one prompt and one notes string per item. The seed is
  the first seed plus the item index, so items differ but runs repeat.
- **Tags follow slots.** `image_N` is always `<Picture N>`, matching how the
  workflow wires `images.image_1`–`image_3` on the conditioning node. Slots are
  never renumbered when one is empty.
  - A draft tag whose slot has no image is allowed: that picture gets no notes and
    the writer uses the draft's words for it.
  - A connected image whose tag the draft never mentions is described, and the
    writer must not add its tag (the result may use only the draft's tags); the
    notes output records it.
  - The check: the result contains exactly the set of tags in the draft.
- **Roles.** `other` gets a general description of what the picture shows that is
  relevant to the draft. Two slots may share a role; each is described and the
  writer covers them in slot order within that role's section. A role with no
  picture is written from the draft's words only.
- **Models.** Acceptance is judged on Qwen3.5-4B-Unredacted-MAX through
  transformers (the maintainer's named model); Gemma 4 E4B through transformers
  should work and is a second check. GGUF vision models are listed when they have
  an `mmproj`; a load failure (for example Gemma 4 vision on llama-cpp 0.3.36)
  raises a clear error naming the model and suggesting the transformers folder.
  `trust_remote_code` is never enabled.
- **Picker.** A shared listing in a new module returns the Enhancer's existing
  vision-capable entries plus a new `hf` kind for transformers folders. The
  Enhancer's own picker and behaviour do not change (it does not list `hf`
  entries). The native, ComfyUI-managed path is allowed: two passes fit its one
  image per call.
- **Cache and re-runs.** The pass-1 cache lives in memory for the ComfyUI session
  only, keyed by a hash of the image tensor, the role and the model name. Default
  ComfyUI caching applies (no `IS_CHANGED` override); a changed image, prompt or
  model re-runs the node. The frontend shows the last run's prompts, one per
  item, with the item count.

## Left to the builder

- Module layout inside `kikotools/tools/<new_tool>/`, and what to share with or
  move out of `prompt_enhancer/` (model discovery, GGUF backend).
- The exact instruction text for each pass, written fresh, following the two
  guides: https://platform.minimax.io/docs/guides/image-generation and
  https://openart.ai/blog/minimax-h3-image-prompt-guide/ .
- How a Hugging Face folder is recognised as a text-and-vision model (for example
  `config.json` architectures) and how its chat template is applied per family.
- Generation defaults (temperature, token limits per pass).
- Test fakes for the model backends.
