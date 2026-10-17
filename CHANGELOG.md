# Changelog

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
