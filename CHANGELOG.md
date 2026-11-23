# Changelog

## Unreleased

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
