# Model Resolution Picker — design

Date: 2026-10-27. Status: approved 2026-10-27.

## Intent

A new ComfyAssets node that picks an image size the way Pixaroma's
"Resolution" node does — a grid of aspect-ratio chips with a list of concrete
sizes under the active chip — but driven by a **model dropdown**. Pick the model
family first and every chip's size list becomes that family's preferred
resolutions. The node outputs `width`, `height` and an empty `LATENT`, and has
the toolkit's Swap W×H button, so one node replaces Width Height Selector plus
Empty Latent Batch in a workflow.

This is a **new node**. Width Height Selector and Empty Latent Batch stay as
they are.

Why now: every new model family (Flux.2, Klein, Z-Image, Qwen-Image 2.1,
MOSS-Image, Anima, HunyuanImage) has its own preferred sizes and its own VAE
step. The existing preset dropdown is one flat SDXL/FLUX list; keeping it
current for a dozen families makes a 60-entry combo nobody can scan. The chip
grid makes the choice two clicks, and the model dropdown keeps the wrong sizes
out of reach.

## Goals

- Two clicks from "I loaded Illustrious" to a correct size: model, then chip,
  then (optionally) a different entry in the list.
- Swap W×H flips the dimensions, moves the highlight to the mirrored chip
  (16:9 → 9:16) and to the matching entry in that chip's list.
- Custom Ratio: type any `W:H` and get sizes computed at the family's
  megapixel tiers, rounded to the family's step.
- Custom Resolution: type exact width/height; the node rounds to the family's
  step and shows the effective size before you queue.
- The empty latent is correct for every listed family, including 16x and 32x
  VAEs, by carrying the `downscale_ratio_spacial` mark that core
  `EmptyLatentImage` sets (the fix from commit 297f2b1).
- Looks and behaves the same in the Classic and Nodes 2.0 frontends, using the
  existing `web/ui` toolkit.

## Non-goals

- Replacing or changing Width Height Selector or Empty Latent Batch, their
  presets, JS, or tests.
- Video-length or frame-count handling. Video families are listed for their
  **frame size** only: the latent output is an image latent for generating
  first/last keyframes with an image model at the video model's native size.
- Per-checkpoint detection. The user picks the family; the node does not
  inspect the loaded model.
- Snap/step toggles on the node. The step is a property of the family.

## Anti-goals (would make this a failure even if it works)

- Vendoring or adapting Pixaroma's JS, CSS or assets. `docs/ui-migration.md`
  records that only the organization was an inspiration; that stays true.
- Storing UI state anywhere except ComfyUI's native widgets. The DOM panel is
  a projection of `model`, `width`, `height`; it must never need its own
  serialized state to reconstruct itself.
- A size table that is "generated from the formula" for a family that has an
  official list. Official lists are used verbatim.
- Breaking the real-host CI (pinned ComfyUI, both renderers).

## How it looks

Top to bottom inside the node:

1. Native `model` combo widget.
2. The DOM panel (`.ca-tools`):
   - A header line: effective size, ratio label and megapixels, e.g.
     `1216 × 832 · 3:2 · 1.0 MP`. "Effective" means after rounding to the
     family step, so what you see is what Python will emit.
   - The chip grid: `1:1`, `4:5`, `5:4`, `3:4`, `4:3`, `2:3`, `3:2`, `9:16`,
     `16:9`, `21:9`, `9:21`, and `Custom ratio`. Three columns. Chips with no
     sizes for the selected family are disabled, not hidden, so the grid never
     reflows. The active chip uses the toolkit's primary (blue) style.
   - Below the grid, the size list for the active chip, one entry highlighted.
     With `Custom ratio` active, the list is replaced by a `W:H` text field
     and the computed sizes for that ratio.
   - The toolkit Swap W×H button.
3. Native `width`, `height`, `batch_size` widgets. `width`/`height` double as
   the Custom Resolution fields and as the inputs you convert when wiring
   dimensions in from another node.

Placement: the panel mounts after the native widgets, which is the toolkit
convention used by the two sibling nodes and the behavior `addDOMWidget` gives
for free in both renderers. **My call**; the builder may move the panel
directly under `model` only if it proves stable in both renderers under the
real-host tests.

New nodes start at 340 × 600. Saved workflows keep their node size.

## Behavior

### State model

The only persisted state is the four native widgets: `model` (COMBO),
`width` (INT), `height` (INT), `batch_size` (INT). Everything the panel
shows is derived:

- **Active chip**: the chip under which the family table lists
  `width × height` (authored membership always wins; that is how HunyuanImage's
  2560×1536, a 5:3 size, lives under 16:9). If no list contains it, the
  nearest chip whose ratio is within 7% of `width / height` (so 1216×832
  reads as 3:2 and 1536×640 as 21:9). If none, `Custom ratio` is active and
  the ratio field shows the reduced fraction, with aliases so 8:5 displays as
  16:10 and 7:3 as 21:9.
- **Custom-ratio mode flag**: the panel keeps one in-memory, non-serialized
  flag "custom ratio open" plus the pending text in the field. Clicking the
  `Custom ratio` chip sets the flag and prefills the field with the current
  reduced ratio; it does not change `width`/`height`. Committing a ratio and
  picking a tier size sets `width`/`height` and keeps the custom list open
  until another chip is clicked. On reload the flag is gone and the pure
  derivation above decides, which is the intended behavior. This is the only
  panel-owned state and it is never needed to reconstruct anything.
- **Highlighted list entry**: the entry equal to `width × height`, else none.
- **Header**: computed from `width`, `height` and the family step.

Consequence: reload, undo, copy/paste, and converting `width`/`height` to
inputs all work with zero code, because there is nothing to restore. When
`width` or `height` is converted to an input, the panel disables the chips
and list and shows "dimensions are wired in" in the header; the Swap button
stays enabled only when both are widgets.

### Interactions

- **Chip click**: sets `width`/`height` to that chip's default entry for the
  family (the entry closest to the family's default megapixels), unless the
  current size already belongs to that chip's list.
- **List click**: sets `width`/`height` to that entry.
- **Custom ratio field**: accepts `W:H` (integers, also `W/H` and `W x H`);
  on commit, the list shows one size per family megapixel tier, computed with
  ComfyUI core's Resolution Selector formula (`scale = sqrt(MP·1024² /
  (w·h))`, each side rounded to the family step). Invalid input keeps the
  previous list and shows an inline error in the panel's status line.
- **Swap W×H**: swaps `width`/`height` through the native widgets with
  callbacks (so converted inputs and other extensions see it), then the panel
  re-derives. Because every family list is authored with mirrored pairs, the
  swapped size lands on the mirrored chip with a highlighted entry.
- **Model change**: if the current size is in the new family's lists, keep it.
  Otherwise pick, in order: the same chip's default entry in the new family;
  the family default size. Log nothing; the header reflects the change.
- **Width/height edited directly**: panel re-derives; the header shows the
  rounded effective size if the typed value is not on the family step.

Every width/height change goes through the widgets' callbacks exactly once,
as `ui/dimensions.js` already guarantees for the sibling nodes.

### Python execution

Inputs: `model`, `width`, `height`, `batch_size`.
Outputs: `LATENT` (`latent`), `INT` (`width`), `INT` (`height`).

1. Resolve the family record. The combo value **is the label**, because a
   ComfyUI COMBO stores the displayed string in both renderers; labels are
   therefore short and treated as stable ids (`SDXL`, `Illustrious XL`,
   `Flux.1`, `Z-Image`, `Qwen-Image`, `Flux.2 / Klein / MOSS`,
   `Qwen-Image 2.1`, `HunyuanImage 2.1`, `Anima`, `SD 1.5`, and the four
   video rows suffixed ` (keyframes)`). The model list that a label covers
   goes in the combo tooltip and the README, not in the label. Each record
   carries an `aliases` list of former labels so a rename maps forward.
   An unknown value falls back to a generic 8-pixel step with a logged
   warning: it never re-rounds a saved size to another family's step.
2. Round `width`/`height` to the nearest multiple of the family step, never
   below 64; log at info level when a value changed.
3. Build the latent with the existing
   `empty_latent_batch.logic.create_empty_latent_batch` (4 channels, 8x,
   carries `downscale_ratio_spacial: 8`). ComfyUI's sampler resizes it to the
   family's real latent ratio because of that mark; for 16x and 32x families
   the step rounding in step 2 is what keeps that resize exact.
4. Return `(latent, width, height)` as rounded.

The family table lives in Python
(`kikotools/tools/model_resolution_picker/families.py`) and is the single
source of truth. The frontend fetches it once from a GET route
`/kikotools/model_resolution/families` registered on `PromptServer` (the
project already registers routes for Local Image Loader) and caches it per
page. If the fetch fails the panel shows one status line and the native
widgets remain fully usable. **My call**; the alternative is duplicating the
table in JS, which is exactly the drift this node exists to avoid.

### Family table schema

```
id:           stable string used as the combo value, e.g. "sdxl"
label:        combo text, e.g. "SDXL / Pony"
vae_ratio:    8 | 16 | 32   (informational; the latent is always built at 8)
step:         pixel multiple for rounding and custom sizes
megapixels:   list of tiers for Custom ratio, in 1024² units
default:      (w, h)
sizes:        { chip: [(w, h), ...] }   authored, mirrored pairs across chips
```

The `sizes` lists are **authored literals checked into Python**. For the
"generated" families they are produced once by a helper script using the
Resolution Selector formula and then hand-adjusted to include the official
examples named below (for instance 1920×1088 for Flux 16:9 does not fall out
of the formula; it is added by hand). The validator never regenerates them.
The live Custom-ratio list does use the formula, so it may offer a slightly
different size than the chip list for the same ratio; that is acceptable and
the header shows the exact size either way.

Python unit tests validate the table: every size is a multiple of `step`,
every size's ratio is within 7% of its chip, every landscape entry has its
portrait mirror under the mirrored chip, defaults are present in `sizes`,
labels and aliases are unique, and every "must include" size named in the
family table below is present.

## The families (v1)

Sources are listed per row. "Official list" means the sizes are copied; for
families whose guidance is "any size, multiples of N, within a megapixel
range", the sizes are generated with the Resolution Selector formula at the
stated tiers and step, then spot-checked against the official examples
named. 1 MP = 1,048,576 px.

| id | Label | VAE | Step | Tiers (MP) | Default | Sizes |
|---|---|---|---|---|---|---|
| `sd15` | SD 1.5 | 8 | 64 | 0.25, 0.5 | 512×512 | generated; 512-class, plus 768×768 |
| `sdxl` | SDXL / Pony | 8 | 64 | 1.0 | 1024×1024 | official 1 MP buckets: 1024², 1152×896, 1216×832, 1344×768, 1536×640 and mirrors; 4:5/5:4 as 832×1024 / 1024×832 |
| `illustrious` | Illustrious XL (v1+) | 8 | 32 | 1.0, 1.5, 2.25 | 1024×1024 | SDXL buckets plus the 1536 class from the v1.0 model card and paper: 1536², 1024×1536, 1248×1824, 1344×1792, 1152×2048 and mirrors |
| `anima` | Anima | 8 | 16 | 0.5, 1.0, 1.5 | 1024×1024 | generated within the documented 512–1536 range; Wan 2.1 latent format in ComfyUI |
| `flux1` | Flux.1 dev / schnell / Krea, Chroma, HiDream I1, SD3.5, Lumina 2 | 8 | 16 | 0.5, 1.0, 1.5, 2.0 | 1024×1024 | generated; must include 1920×1088 / 1088×1920 (BFL's 16:9 example) |
| `zimage` | Z-Image Turbo / Base | 8 | 16 | 1.0, 1.6 | 1024×1024 | official 1024 and 1280 sets (11 sizes each) confirmed by Tongyi on the model's HF discussion #28 |
| `qwen_image` | Qwen-Image / 2512 | 8 | 16 | 1.76 | 1328×1328 | official training-stage list: 1328², 1664×928, 1472×1104, 1584×1056 and mirrors |
| `flux2` | Flux.2 dev / Klein, Flux.3 Klein, MOSS-Image, Ideogram 4 | 16 | 16 | 1.0, 2.0, 4.0 | 1024×1024 | generated; must include 1248×832 (Flux.2 template default) and 2048² (4 MP max) |
| `qwen_image_21` | Qwen-Image 2.1 / Turbo | 16 | 32 | 1.0, 4.0 | 1024×1024 | official 2K presets 2048², 2400×1792, 2528×1696, 2752×1536 and mirrors, plus generated 1 MP set (ComfyUI template default) |
| `hunyuan_image_21` | HunyuanImage 2.1 | 32 | 32 | 4.0 | 2048×2048 | official: 2048², 2560×1536, 2304×1792 and mirrors; 3:2/2:3 generated at 4 MP. No 1 MP tier: the card says 1K output artifacts |

Families named in one row share a VAE and step; the combo label lists them so
users find their model. Adding a family later is one Python record plus its
test row.

### Video families (frame sizes for first/last-frame generation)

These rows exist so a keyframe can be generated at the exact size the video
model will be run at. The combo groups them under a "Video (keyframes)"
suffix in the label. The latent output is still an 8x image latent, which is
what the keyframe image model needs; it is never fed to the video model.

| id | Label | Step | Tiers (MP) | Default | Sizes |
|---|---|---|---|---|---|
| `wan22` | Wan 2.2 (keyframes) | 16 | 0.4, 0.9 | 1280×720 | official 480p/720p classes: 832×480, 1280×720, 1280×704 (5B TI2V template), 640×640, 960×960 and mirrors |
| `ltx2` | LTX-2 (keyframes) | 32 | 0.4, 0.9 | 768×512 | template sizes 768×512, 960×544 (ComfyUI templates), plus generated at 0.9 MP with the 32 step the LTX templates use |
| `hunyuan_video_15` | HunyuanVideo 1.5 (keyframes) | 16 | 0.4, 0.9 | 1280×720 | generated; 480p and 720p classes |
| `minimax_h3` | MiniMax H3 (keyframes) | 32 | 0.4, 1.0 | 864×480 | generated at 0.4 MP, step 32, which is what every official H3 template sets on Resolution Selector; 1.0 MP tier covers H3-Base's 768p ceiling |

Video family sizes are validated by the same table tests. They carry no
frame-count data by design.

Deliberately out of v1: Ming Image, SenseNova U1.5 and other pixel-space
models (ratio 1, needs its own latent path), HunyuanImage 3.0 (no native
ComfyUI support), Flux.3 Image (API only).

## Decisions

- Default family on first add: **SDXL** at 1024×1024 (decided 2026-10-27).

Decided 2026-10-27: video families are in, as keyframe sizes (see above).
Builder-check calls made by the author, 2026-10-27: authored chip membership
wins over ratio tolerance (7%); combo value is the label with an alias list;
custom-ratio mode is an in-memory flag; size lists are authored literals;
manual 16x/32x generation check before merge.

## Verification before merge

The real-host CI never queues a generation, so the latent path is only
unit-tested. Core `EmptyLatentImage` is the same 4-channel, 8x, marked latent
this node emits, and the official Anima template already runs that path
(channel repeat 4 → 16). The two cases to confirm by hand on the user's GPU
box before merge, each with one queued image: a 16x family (Flux.2 or
Qwen-Image 2.1) and the 32x family (HunyuanImage 2.1) at a non-square size,
checking the saved image's dimensions equal the node's outputs. Record the
result in the PR.

## Constraints

- Node id `ModelResolutionPicker`, display name "Model Resolution Picker",
  category `🫶 ComfyAssets/🖼️ Resolution`. Registered in
  `kikotools/__init__.py` like the others.
- Frontend: `web/model_resolution_picker.js` extension plus a view under
  `web/views/` built only from `web/ui/core.js` primitives and
  `controls.css` tokens; styling added to `controls.css` under a new
  `.ca-resolution-*` family. `createScope()` owns listeners, the fetch
  signal and theme observers; node removal disposes it and preserves the
  previous `onRemoved` hook's context and return value, as every migrated
  node does.
- Swap reuses `ui/dimension-swap.js` for the button and `ui/dimensions.js`
  for the swap; the latter gains support for nodes that have `width`/`height`
  but no `preset` widget (today it returns early).
- Tests, per `TESTING.md` tiers: Python unit tests for the table validator,
  rounding and execution (including the latent mark and the unknown-id
  fallback); JS unit tests for derivation, ratio parsing, custom-ratio
  generation and model-change selection; browser-fixture workflows for chip
  → widgets, list → widgets, swap → mirrored chip, model change, custom
  ratio, wired-in dimensions, theme switch, idempotent mount and disposal;
  real-host coverage of both renderers and workflow round-trip. Python
  coverage stays above the 85% gate; new JS files get floors in
  `tools/testing/frontend-coverage-baseline.json`.
- README gets a tools-table row and a section with a screenshot under
  `docs/screenshots/`; `docs/ui-migration.md` gets a row.
- Version bump to 1.3.0 (new node), in the release PR, not this one.
- No external requests. The only HTTP call is the local families route.

## Left to the builder

- Exact chip grid markup (`createSegments` vs buttons with
  `aria-pressed`), keyboard order, and how disabled chips announce
  themselves.
- The generated-size algorithm's tie-breaking and the spot-check test list.
- Whether the families route also serves ETag/caching headers.
- Node default size fine-tuning and the status line's wording.
- File split inside `kikotools/tools/model_resolution_picker/` (`node.py`,
  `logic.py`, `families.py`, `routes.py`).

## Addendum (2026-10-27, after first hands-on test): JSON table, user override, resolution dropdown

Decided with the owner after testing the first build. Three changes, same branch.

### 1. The family table is a shipped JSON file

`kikotools/tools/model_resolution_picker/families.json` replaces the Python
literals. Its shape is exactly the payload the route already serves:

```json
{ "version": 1, "chips": [...], "mirror": {...}, "default": "SDXL",
  "families": [ { "label": "SDXL", "aliases": [], "models": "...", "group": "image",
                  "vaeRatio": 8, "step": 64, "megapixels": [1.0], "default": [1024, 1024],
                  "sizes": { "1:1": [[1024, 1024]], "4:5": [[832, 1024]], ... } } ] }
```

`families.py` loads it at import, validates it with a runtime validator that
enforces the same invariants the tests enforce today (step multiples, 7% chip
tolerance, exact mirrors, ascending order, one chip per size, unique labels
and aliases, default present, every chip key present), and builds the same
`Family` records. A shipped file that fails validation is a startup error.
The file is package data (`[tool.setuptools.package-data]`), and the git
checkout is what ComfyUI loads, so the file simply lives next to the module.

### 2. A user override file

`<ComfyUI user directory>/kikotools/model_resolutions.json` (via
`folder_paths.get_user_directory()`; when that is unavailable there is no
override). Same schema as the shipped file; top-level `chips`/`mirror` are
ignored if present. Merge rules, by `label`:

- same label as a shipped family → the override record **replaces** it whole;
- new label → appended after the shipped families, in file order;
- optional `"remove": ["label", ...]` hides shipped families;
- `default` in the override, if present, becomes the combo default.

The merged table is validated with the same validator. An unreadable or
invalid override is **ignored entirely** (never partially applied), logged at
warning level, and reported to the panel: the payload gains
`"warnings": ["Override ignored: <reason>"]` and the panel shows the first
warning in its status line. The override is re-read when its mtime changes,
so edits are picked up on a page reload (or ComfyUI's "Refresh node definitions"), which also refreshes the `model` dropdown, without a restart. The frontend caches the families payload per page.
The shipped file is never modified by the node.

### 3. A native `resolution` dropdown

A COMBO widget named `resolution` sits between `model` and `width`. It lists
the sizes that fit the **active ratio chip** for the selected model, plus
`custom` first; with `Custom ratio` active or no chip matched it lists every
size for the model. Labels use the old node's format:
`1216×832 - 3:2 (1.0MP)` (ratio label = the chip the size is listed under,
else the reduced ratio; megapixels to one decimal, 1 MP = 1024²).

Sync rules (the panel remains a projection of the native widgets):

- Picking from the dropdown writes `width`/`height` through their callbacks,
  exactly like a size-list click.
- Any size change (chip list, swap, typed width/height, model change) sets
  `resolution` to the matching label, or `custom` when the size is not in the
  active list. The dropdown's option list is rebuilt whenever the model or the
  active chip changes.
- Python: when `resolution` is not `custom` and parses as `W×H`, those
  dimensions win over `width`/`height` (same precedence as the old preset
  dropdown); then the family-step rounding applies as before. The combo's
  Python option list is `custom` plus every distinct size label across all
  shipped families, and `VALIDATE_INPUTS` accepts `resolution` as it does
  `model`, so override-added sizes and old labels still execute.
- Workflows now serialize five native widgets; nothing else changes.

Non-goals unchanged. The chip grid, Custom ratio and Swap stay as built.

### 4. Ratio shape on each chip

Each ratio chip shows a small outlined box shaped like its ratio before the
label (wide for 16:9, tall for 9:16, square for 1:1). It is drawn with the
toolkit's own markup and tokens: a `<span class="ca-resolution-shape">`
sized from the ratio (longest side 18 px, shortest side at least 6 px,
rounded to whole pixels), `border: 1px solid currentColor`, with the active
chip's white text colour showing through. Purely decorative: `aria-hidden`,
no effect on the accessible name, hidden on `Custom ratio`. No Pixaroma
code or assets.
