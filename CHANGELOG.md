# Changelog

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
