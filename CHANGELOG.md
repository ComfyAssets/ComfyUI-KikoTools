# Changelog

## Unreleased

### Fixed

- H3 Reference Prompter: the prompt box no longer squashes to one line after a
  run, and the node can be resized. A new result grows the node so about 320 px
  of prompt shows, the prompt box never gets smaller than 120 px, and a taller
  node gives the prompt box more room, in both the classic and the Nodes 2.0
  renderer.

## 1.10.0

### H3 Reference Prompter

- New node in 🫶 ComfyAssets/🧠 Prompts. It writes one long MiniMax H3 Image
  prompt from a short draft and up to three reference pictures (character,
  outfit, pose or other), using a local vision model.
- The whole draft is written first, word for word, by the node; the model adds
  the detail after it and never repeats the draft's sentences. The prompt
  keeps exactly the draft's tags; after one retry the node stops with an error
  naming the tags.
- Two passes: each picture is described once and cached for the session, then
  the prompt is written.
- One-per-pose runs give one prompt and one set of notes per item.
- Transformers models describe all the pictures of a run in one batch and write
  all the prompts in another; only prompts with wrong tags or no text are
  retried, again in one batch. Batching needs transformers 5 or newer and runs
  only for Qwen3-VL and Qwen3.5 folders; other cases run one request at a
  time. Batched items all use the base seed. GGUF and native models run one
  call at a time, with the base seed plus the item index. A GGUF model loads
  twice per run, with and without its `mmproj`.
- Pictures are scaled down to about 1 MP before they are described.
- An empty written prompt is retried once, then stops with an error that
  suggests raising `write_tokens`.
- Models: transformers folders under `models/LLM` (Qwen3-VL, Qwen3.5, Gemma 4),
  the Prompt Enhancer's vision text encoders, and GGUF models with an `mmproj`.
  The picker defaults to Huihui-Qwen3-VL-8B-Instruct-abliterated, then any
  Qwen3-VL-8B, then the first transformers folder. The 8B uses about 17 GB of
  VRAM while it runs.
- ComfyUI's loaded models are freed first with the safe unload from Kiko Purge
  VRAM; the prompt model is unloaded afterwards unless `keep_loaded` is on. A
  kept model of another backend is freed when the backend changes. A kept
  `hf:` model sits outside ComfyUI's memory management.
- A panel on the node shows each prompt with its word count, previous and next
  buttons, a copy button and collapsible notes.
- Example workflow: `h3_reference_prompter_charsheet_test.json`.
- A blank placeholder picture (a small, uniformly white image, such as
  KikoCharSheet's Nude costume image) counts as no picture.
- Roles default to `auto`, which reads the draft's `<Picture N> is the
  character/outfit/pose.` sentences and falls back to character, outfit, pose;
  a role picked by hand wins. A KikoCharSheet Nude run no longer describes the
  pose mannequin as an outfit.
- A closing list of what must not appear is cut to six items in a row, so a
  run-on list cannot swell the prompt.
- Nude mode: a draft that says nude, naked or 裸 always gets the adult age
  check, whatever the roles; with no outfit picture it also gets a plain,
  non-sexual description of the unclothed adult body. The run is
  refused unless the character picture's estimated age is 20 or older and no
  youth word appears in the notes, the draft or the written part. Never use
  pictures of real people.

### Kiko Purge VRAM

- Reworked to free memory the way Free VRAM Pixaroma does. Three modes now:
  `all` (default), `models` and `cache`. Steps run in a fixed order: unload
  models, collect garbage when `collect_garbage` is on (in every mode), then empty the
  cache.
- Old mode names still load and run: `soft` and `aggressive` map to `all`,
  `models_only` maps to `models`, and `cache_only` maps to `cache`.
- **A non-zero `memory_threshold_mb` in a saved workflow now means "skip when at
  least this many MB are free" instead of "purge when this many MB are used".**
  Set it to `0` to always purge.
- With nothing wired into `anything`, the node does nothing and says so in the
  report.
- New `collect_garbage` switch (on by default) controls the garbage-collection
  step.
- New `every_run` switch (on by default). Turn it off to let ComfyUI cache the
  node so nodes after it do not re-run.
- A failing step now stops the run with an error, after the node repairs
  ComfyUI's loaded-model list so later jobs keep working. The traceback is
  logged.
- The `models` step drains ComfyUI's loaded-model list one entry at a time, then
  calls `unload_all_models()` so other packs' hooks still run. Calling
  `unload_all_models()` alone can fail when one unload frees another model
  mid-loop and leave ComfyUI unable to start the next job.
- Out-of-memory errors are re-raised unchanged so ComfyUI still handles them.
- Behaviour based on Free VRAM Pixaroma from
  [ComfyUI-Pixaroma](https://github.com/pixaroma/ComfyUI-Pixaroma) by Pixaroma.

## 1.9.0

### Model Resolution Picker

- New `MiniMax H3 Image` family: 16x VAE, step 32, 1K / 2K / 4K tiers from
  MiniMax's reference size formula, defaulting to 2048×2048. The 2K and 4K sizes
  match MiniMax's published table; 1K sizes are rounded onto the 32 grid.
  Switching to `MiniMax H3 Image` from 1024×1024 keeps the 1K preview tier; pick
  2048×2048 for the area the model is tuned for. The `MiniMax H3 (keyframes)` row
  for the H3 video model is unchanged.

## 1.8.0

### Local Image Loader

- Ctrl-click (Cmd-click on a Mac) images in the gallery to pick refs in order.
  Each picked image shows its number, and the `Refs: N` bar has a `Clear refs`
  button. A plain click still selects the single `image` output.
- New `refs` output for the `refs_bundle` input of Create H3 RefMod in
  ComfyUI-MiniMaxH3Mod. The first pick sets the size. The node scales each other
  pick to cover that size and crops the center, the same rule Create H3 RefMod
  uses.
- New `refs_preview` output: the same images as one IMAGE batch, so you can see
  what Create H3 RefMod will encode. It shares memory with `refs`.
- Refs are images only, up to 256. The workflow saves the picks.

### Kiko Prompt Enhancer

- Qwen3-VL 4B and 8B text encoders now write a full prompt. They returned only
  the trigger words and the no-text sentence, because the model picker loaded
  them as CLIP types that cannot generate text. 4B now loads as `krea2` and 8B
  as `ideogram4`. (#135)

## 1.7.0

### Model Recommended Settings

- New node that outputs the steps, CFG, sampler and scheduler a model's author
  recommends, ready to wire into KSampler. It reads the Civitai info LoRA
  Manager or Civitai Helper already stored for the model (a `.metadata.json` or
  `.civitai.info` next to the file, or LoRA Manager's central sidecar folder);
  nothing is downloaded. Wire `model_name` from Checkpoint Folder Iterator's
  `ckpt_name` and every model in a sweep runs with its own settings.
- Settings the description calls recommended win, read from that passage on, so
  an older version's settings earlier in the text are ignored. Otherwise the
  most common values on the example images come first. Civitai sampler names
  ("DPM++ 2M Karras") and ComfyUI names (`er_sde`, `sgm_uniform`) are both
  understood.
- A sampler or scheduler that is not installed (e.g. `bong_tangent`) falls back
  to the widget, or to a substitute from `ComfyUI/user/kikotools/model_settings.json`,
  which also holds per-model overrides. `use_model_*` switches keep a field on
  its widget, and `info` says where every value came from.

### Checkpoint Folder Iterator

- New `model_type` input. `diffusion_model` scans `models/diffusion_models` and
  loads each file like Load Diffusion Model (MOSS, Flux and other split
  models); CLIP and VAE come from their own loaders. The input is last and
  defaults to `checkpoint`, so saved workflows keep their widget values.

### Model Compare Sheet

- A sweep that changes mid-way starts a new grid. Each run records a
  fingerprint of the queued prompt; when the prompt, settings, LoRAs or the
  sheet's image source change, the tiles already in the folder move to
  `<run_name>_<timestamp>` as they do at index 0. The model index, seeds and
  the sheet's layout (columns, tile width, font size) do not count. Folders
  from earlier versions have no fingerprint and are left alone.

## 1.6.0

### Prompt Enhancer

- New Kiko Prompt Enhancer node. It rewrites a short prompt in the style of the
  chosen base model, with an optional image and trigger words that are placed
  first in the result and removed from the prompt before the LLM sees it. It
  ships ten system prompts (anima, flux2-klein, illustrious, krea2, moss,
  qwen-image, sdxl-realism, wan-i2v, wan-t2v, z-image). Files in
  `ComfyUI/user/kikotools/system_prompts/` replace or add prompts, and updates
  leave that folder alone. Needs ComfyUI from September 2026 or newer.
- A `model` picker lists `native:` text encoders from `text_encoders` and
  `gguf:` models from `models/LLM` or `text_encoders`; it defaults to the first
  uncensored, abliterated or heretic `native:` entry, then the first such entry
  of any kind. JoyCaption GGUFs are not listed. GGUF needs `llama-cpp-python`
  (optional, not installed by KikoTools) and unloads ComfyUI's models first;
  `keep_loaded` keeps it in memory between runs. Thinking is switched through
  the model's own chat template (`enable_thinking`). A vision GGUF needs an
  `mmproj` file in the same folder.
- A `mode` input (`text` or `vision`) decides whether the `image` input is
  used. The `clip` input is now optional and overrides `model` when connected; a
  saved model missing on this machine no longer fails validation.
- Prompt files accept a `no_text_sentence:` front-matter key, appended when the
  result has no quoted text (straight or typographic quotes); the shipped krea2 prompt uses it.

## 1.5.0

### Packaging

- The Comfy Registry listing uses the new KikoTools icon, and the README opens
  with the new banner. Both images live in `docs/brand/`, which stays out of
  the package.

### Model Downloader

- New optional `sha256` input. When it is set, a download is hashed while it
  streams and is discarded (the `.part` file is removed, nothing lands in the
  models folder) if it does not match. A file that is already there is hashed
  instead of being trusted; on a mismatch it is kept and the node says so,
  suggesting Force Redownload. The input is last, so saved workflows keep their
  widget values.

## 1.4.0

### Packaging

- The Comfy Registry package has its nodes again. An unanchored `tools/` rule in
  `.comfyignore` also matched `kikotools/tools/`, so the 1.2.0 to 1.3.1 packages
  shipped without the tool modules; installs from git were not affected. Every
  rule is now anchored to the root, and `tests/unit/test_package_contents.py`
  holds them to what ComfyUI needs.
- `docs/` and `examples/` are left out of the package as well; they are only
  read on GitHub. The download goes from about 8.5 MB to about 0.26 MB.

### Local Image Loader

- New `folder` output: the path of the folder the gallery shows, or the
  selected image's folder until you browse. Browsing to a folder is enough;
  no image needs to be selected. Use it to pick a training dataset visually and
  pass it to a node that reads a whole folder. The folder must be inside a
  saved path or ComfyUI's input/output, as for images.

### Model Downloader

- Civitai tokens and Hugging Face tokens are read on the ComfyUI server:
  `CIVITAI_API_KEY` (also `CIVITAI_API_TOKEN`, `CIVITAI_TOKEN`) and `HF_TOKEN`
  (also `HUGGING_FACE_HUB_TOKEN`, or the token `hf auth login` saved). Leave
  `api_token` empty so shared workflows carry no token; a typed token still
  wins. Each token goes only to its own site, and custom URLs only get a typed
  token.
- civitai.green and civitai.red links download like civitai.com links; the
  download goes through civitai.com.
- A Civitai download with a `filename` that already exists returns before any
  API call.

## 1.3.1

### Startup

- The console banner is one line, version plus tool count, instead of one
  `Loaded:` line per node.

### Custom Colors

- The `🫶 Custom Colors` entry opens its Full / Title / BG submenu again in
  Nodes 2.0. The Nodes 2.0 context menu converts litegraph items itself and
  only renders a submenu for entries flagged `has_submenu`, so the entry was an
  inert label there; the classic menu was unaffected.

### Model Resolution Picker

- New `Krea 2` family (Krea 2 Turbo, Raw and finetunes): 8x VAE, step 16,
  1.0 / 2.0 / 4.0 MP tiers, with the model card's 1024×1024 and 2048×2048 and
  Big Love KreaEdit3's 1024×1536.

## 1.3.0

### Model Resolution Picker

- New `Model Resolution Picker` node (🖼️ Resolution): pick a native size for a
  model family from a chip grid of aspect ratios and output an empty latent plus
  width/height. Fourteen shipped families (SD 1.5, SDXL, Illustrious XL, Anima,
  Flux.1, Z-Image, Qwen-Image, Flux.2 / Klein / MOSS, Qwen-Image 2.1,
  HunyuanImage 2.1 and four video keyframe rows), each rounded to its VAE step.
- Native `resolution` dropdown that mirrors the chip grid both ways; typed or
  wired sizes show `custom`.
- Shipped family table in `families.json` with a validator, and a user override
  file at `user/kikotools/model_resolutions.json` that can replace, add or remove
  families and set the default. Invalid files are ignored whole with a warning
  in the panel.
- The node height follows the panel content, and workflows saved before the
  dropdown existed still load.
- `GET /kikotools/model_resolution/families` serves the merged table; the shared
  dimension swap now works on nodes without a preset widget.

## 1.2.0

### Unified ComfyAssets UI

- Consistent blue controls and strong red destructive actions that follow
  ComfyUI's light/dark theme.
- Updated Local Image Loader, Save Image viewer, Seed History, Workflow Timer,
  dimension swaps, Node Dimensions, Display Text/Any and Embedding Autocomplete.
- Larger adjustable gallery thumbnails and saved-image previews that use the
  available space; responsive layouts, keyboard controls and lifecycle cleanup.
- Shared Custom Colors picker with hex entry, HSV sliders and presets.
- Restored autocomplete tag management, four-column CSV parsing, worker-based
  imports and persistent tag caching. Tag packs remain a separate download;
  see [tag-pack provenance and terms](docs/tag-packs/README.md).
- Follow Execution honors live enablement, avoids duplicate subscriptions and
  safely groups navigation menus.

### Compatibility and testing

- Classic and Nodes 2.0 coverage includes fresh startup in each renderer,
  switching both ways, themes, saved workflows and removal cleanup.
- Required CPU-only real-ComfyUI CI joins the existing Python, JavaScript,
  Chromium, touch, Firefox and WebKit suites. Runtime pins and failure artifacts
  make compatibility checks repeatable.
- Retained [screenshots](docs/screenshots/README.md) and documented
  [testing commands](TESTING.md).

### Deprecation and upgrade

Gemini Prompt Engineer is deprecated and hidden from normal new-node discovery.
Its registration, schema and execution remain available for saved workflows;
ongoing Google API/model compatibility maintenance has ended.

Restart ComfyUI and hard-refresh the browser after upgrading. Existing node
interfaces, workflow values and setting IDs are retained. No workflow conversion
is required. Follow Execution remains opt-in through its Enable setting.
