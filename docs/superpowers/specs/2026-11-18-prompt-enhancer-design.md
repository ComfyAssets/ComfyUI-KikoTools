# Kiko Prompt Enhancer: design

Date: 2026-11-18. Status: approved 2026-11-18.

## Intent

A new ComfyAssets node that turns a short prompt into the prompt style a given
base model was trained on. You pick the base model from a dropdown. The node loads
that model's system prompt, runs it through the text encoder you already have
loaded, and outputs the enhanced positive prompt.

Why: every model family wants a different prompt. Illustrious wants Danbooru tags
in a fixed order, Flux.2 Klein wants 30-80 words of subject-first prose, and
Qwen-Image wants a 400-500 word walk around the frame. Wan image-to-video wants
motion only. Today each of our workflows wires the core `TextGenerate` node to a
hand-pasted system prompt, which drifts between workflows and does not exist at
all for the tag-based families.

## Goals

- One node: encoder, prompt, an optional image, a model choice and an enhanced
  prompt out.
- One researched system prompt per model family, shipped with the pack.
- Users can override any shipped prompt, or add new models, without editing the
  pack and without losing their edits on update.
- Text-only works with any text-generating encoder. Attaching an image needs a
  vision-capable encoder; the prompt then combines the text and what the image
  shows.
- LoRA trigger words reach the output unchanged, through a dedicated
  `trigger_words` input that is placed before the enhanced prompt. Quoted text
  in the prompt is kept exactly as written.

## Non-goals

- No negative prompt output. Most of our default setups run at CFG 1, where the
  negative is skipped. System prompts phrase "avoid" ideas positively instead
  ("sharp focus throughout", "fixed camera").
- No cloud or extra LLM backends (Ollama, llama.cpp GGUF) in this version. The
  node's interface leaves room to add them later.
- No edit-model families (KreaEdit3, Klein edit) in the first set of prompts.
- No sampler or CFG recommendations.
- No workflow migration in this job. Our own workflows move onto the node in a
  separate comfy-tools change, after the node has been tested and approved.

## Anti-goals

- The node must not add content rules of its own. Official enhancer prompts
  embed policies, such as Krea 2's clothing rule and Wan's NSFW substitution.
  Ours stay faithful to what the user asked for.
- It must not invent subjects, change counts or colours, or drop anything the user
  stated.
- Pack updates must never overwrite a user's edited prompt.

## Approaches considered

- **A. A style picker that outputs a system prompt, fed into core
  `TextGenerateV2`.** This is the least code, but it means two nodes in every
  workflow, no check for a missing vision encoder, and no output clean-up.
- **B. One all-in-one enhancer node calling core's generation code (chosen).**
  One node can check for vision, add per-model notes when an image is attached,
  and clean the output. It needs no new dependencies.
- **C. B plus other backends.** Deferred; nothing in B blocks adding it.

## Decided

### Node

- Display name "Kiko Prompt Enhancer"; node id `KikoPromptEnhancer`; category
  `🫶 ComfyAssets/🧠 Prompts`. It follows the pack's existing node style
  (`ComfyAssetsBaseNode`, `INPUT_TYPES`).
- Inputs:
  - `clip` (CLIP): the text-generating encoder, such as Qwen3.5, Qwen3-VL or
    Qwen3. This is the same object core `TextGenerateV2` takes.
  - `prompt` (multiline STRING).
  - `base_model`: a combo with one entry per system prompt file found.
  - `trigger_words` (optional single-line STRING; can be typed or linked).
  - `seed` (INT).
  - `image` (IMAGE, optional).
  - Advanced: `temperature`, `max_length`, `thinking` (default off).
- Outputs:
  - `prompt` (STRING): the enhanced positive prompt.
  - `system_prompt` (STRING): the exact system prompt used, for inspection.
- Generation uses the same calls as core `TextGenerateV2.execute`:
  `clip.tokenize(..., system_prompt=..., image=...)`, `clip.generate`, then
  `clip.decode`. Thinking text is stripped the same way core does it.
- If an image is attached and the encoder cannot read images, the node fails
  with a clear error naming the encoder and suggesting a vision encoder. It does
  not silently ignore the image.

### System prompt files

- They are shipped in `kikotools/tools/prompt_enhancer/system_prompts/*.md`, one
  file per base model.
- The combo value is the file stem (`flux2-klein`, `wan-i2v`), so saved
  workflows keep working and overrides match by the same key. There is no separate
  display name. *(Builder's call.)*
- Each file starts with a small header:
  - `max_words` (output cap);
  - an optional `image` section, appended when an image is attached. For
    example, Wan I2V: "describe only motion and camera; do not restate what the
    image shows".
- The user override folder is `ComfyUI/user/kikotools/system_prompts/`:
  - a file with the same name as a shipped one replaces it;
  - a file with a new name adds a new combo entry;
  - updates never touch this folder.
- A node context-menu action copies the selected shipped prompt into the
  override folder, as a starting point for editing.

### Initial base models

These come from the research done on 2026-11-18.

| Entry | Style | Length |
|---|---|---|
| SDXL realism | short plain-language lead, then photo and lighting tags; no quality boosters | one 75-token CLIP chunk |
| Illustrious / NoobAI | quality and rating tags, then count, character, series, artist, general tags | 20-40 tags |
| Anima | tag block (`score_7`, rating tag, `@artist`), then 2-4 sentences | no cap |
| Flux.2 Klein | subject-first prose, positive phrasing | 30-80 words, max ~300 |
| Z-Image | dense, objective prose; no metaphors or "8K" | one paragraph, 512 tokens |
| MOSS-Image | English prose caption (tags allowed) | 200-500 words |
| Krea 2 | one faithful prose paragraph; a "no text" sentence unless text was asked for | 30-150 words |
| Qwen-Image 2.1 | observer paragraph with a positional walk of the frame | 400-500 words |
| Wan T2V | up to 4 cinematic tags, then subject, action and background motion | 60-200 words |
| Wan I2V | motion and camera only | under 100 words |

Rules shared by every prompt:
- keep the user's subjects, counts, colours and medium;
- keep quoted text exact, inside double quotes;
- keep LoRA trigger words exactly as written;
- output the prompt only, with no preamble.

### Compatibility

- The node requires a ComfyUI recent enough that `clip.tokenize` accepts
  `system_prompt` (added 2026-09-22). On older cores it fails with a clear
  "update ComfyUI" error instead of a `TypeError`. The README states the
  requirement. *(Builder's call.)*

### Trigger words

- `trigger_words` never reaches the enhancer. After generation, the node puts
  them in front of the output exactly as typed, joined with `", "`. For example:
  `mabes9sans, a woman in a red raincoat...` or `mabes9sans, 1girl, ...`. They
  go first because earlier words weigh more on every listed model, and because a
  trigger appended to a long prompt on SDXL or Illustrious lands in a later CLIP
  chunk. When `trigger_words` is empty, nothing is added.
- As a fallback, every system prompt also says to keep unusual tokens and names
  in the user's prompt exactly as written.

### Source material

- The system prompts are written from the 2026-11-18 research notes, which are
  kept outside this repo. Those notes give per-family sources: official model
  cards, the official enhancer prompts (Krea 2 `expansion.txt`, MOSS skill,
  Qwen-Image 2.1 rewriter, Z-Image `pe.py`, Wan `system_prompt.py`, BFL FLUX.2
  upsampler) and community guides for the SDXL and Illustrious families. Each
  shipped prompt adapts its family's official prompt where one exists, with the
  content policies removed.

## Left to the builder

- How to detect that a CLIP object can read images. Prefer a capability check on
  the tokenizer if one exists; otherwise attempt the tokenize call and turn the
  failure into the clear error described above.
- The exact header format (YAML front matter or similar) and how the combo
  orders its entries.
- Post-processing for `max_words`: trim at a sentence boundary, or only warn.
- Tests: file discovery and override precedence, header parsing, the vision
  error path, and output clean-up, all with a mocked CLIP. Plus one manual run
  per base model against a real encoder.

## Addendum 2026-11-18: model picker, text/vision mode, GGUF backend

Vito's first test of v7 raised three needs: he couldn't choose the LLM, he prefers uncensored models, and he wants
an explicit choice between text and vision. He decided:

- **Model picker.** A `model` combo lists both kinds of local LLM:
  - `native: <path>`: safetensors files under `text_encoders` that `comfy.sd.detect_te_model` identifies as a
    generate-capable Qwen LLM (Qwen2.5-VL, Qwen3, Qwen3-VL, Qwen3.5). The node loads them with
    `comfy.sd.load_clip`, using a `clip_type` chosen per detected model, so ComfyUI manages their memory as usual.
  - `gguf: <path>`: `*.gguf` LLM files under `models/LLM` and `text_encoders`, run through `llama_cpp`. Files whose
    name contains `mmproj` are projectors, not entries. A projector in the same folder makes the entry
    vision-capable. umt5 and other non-LLM GGUFs are skipped, and so are JoyCaption files.
  - `llama_cpp` stays optional. If it can't be imported, the GGUF entries are not listed and one info line is logged.
    No new requirement is added to `requirements.txt`.
- **`clip` becomes optional and overrides the picker.** When an encoder is wired in, the node uses it and ignores
  `model`, which avoids loading a second copy. This keeps v7-style wiring working. `VALIDATE_INPUTS` accepts any
  `model`, so a saved model missing on this machine doesn't block a run with a clip connected.
- **Default model.** The first uncensored/abliterated/heretic `native:` entry, then the first such entry of any kind,
  then the first entry.
- **`mode` combo: `text` | `vision`.**
  - `text` never sends an image, even when one is connected.
  - `vision` requires an image (error: "vision mode needs an image") and a vision-capable model (error naming the
    model). It sends the image and appends the prompt file's `## With an image` section.
- **GGUF runs.**
  - Before loading, the node frees ComfyUI's models (`comfy.model_management.unload_all_models()` plus
    `soft_empty_cache()`).
  - `flash_attn=True` on CUDA. Without it, the 27B vision projector's warmup reservation overflows 24 GB, as found
    with the QwenVL patch.
  - A vision entry uses `llama_cpp`'s Qwen VL chat handler (MTMD if present, else Qwen25VL; neither is a clear error) with its
    projector.
  - The same system prompt, temperature, seed, top_k/top_p/min_p and max_length (as `max_tokens`) apply.
  - Thinking is off unless `thinking` is on; thinking is switched through the model's own chat template
    (enable_thinking).
  - A `keep_loaded` boolean (default off) keeps the GGUF model between runs. Off frees it after each run.
- **Same output path.** Every backend goes through the existing clean, cap and trigger steps.

### Also in this round (from the first live test)
- **krea2 "no text" sentence.** It moves out of the LLM's hands. A new optional front-matter key, `no_text_sentence:`,
  holds the sentence, and the node appends it only when the cleaned output contains no quoted text (straight or typographic quotes).
  krea2.md drops its rule-7 closing-sentence instruction and sets the key.
- **Trigger stripping.** It only tidies commas and spaces where a trigger was removed, so quoted text such as
  `"1,000"` is never rewritten.

### Left to the builder
- The detected-model-to-`clip_type` map. Prefer the type the matching official workflows use, for example Qwen3.5
  9B to `moss_image`, Qwen3-VL 4B to `flux3`, Qwen3 4B to `lumina2`, Qwen2.5-VL 7B to `qwen_image`. Verify each
  generates live.
- Caching the scan of the model list. Header reads are cheap; cache by mtime.
- The GGUF context size: 8192 by default, raised if the image tokens need more.
