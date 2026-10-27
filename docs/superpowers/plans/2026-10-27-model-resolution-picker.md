# Model Resolution Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new ComfyAssets node whose model dropdown drives a ratio-chip grid and size list, outputting width, height and an empty latent, with the toolkit Swap W×H.

**Architecture:** The family table lives in Python (`families.py`) and is served by a GET route; the Python node rounds to the family step and builds the latent with the existing `create_empty_latent_batch`. The frontend is a pure derivation module (`web/ui/resolution-picker.js`), a DOM view (`web/views/resolution-picker.js`) and an extension (`web/model_resolution_picker.js`) that projects the native `model`/`width`/`height` widgets into the panel and writes back through widget callbacks. No panel state is serialized.

**Tech Stack:** Python 3.10–3.13, torch (CPU), aiohttp routes on `PromptServer`; ES modules on the `web/ui` toolkit; pytest, `node --test`, Playwright fixture host (`tests/browser`), pinned real ComfyUI (`tests/comfyui`).

**Spec:** `docs/superpowers/specs/2026-10-27-model-resolution-picker-design.md`

## Global Constraints

- Node id `ModelResolutionPicker`, display name `Model Resolution Picker`, category `🫶 ComfyAssets/🖼️ Resolution`.
- Combo value is the family **label**; labels are stable ids; each family carries `aliases`; unknown label → step 8, logged warning, no re-rounding to another family's step.
- Chips, in grid order: `1:1`, `4:5`, `5:4`, `3:4`, `4:3`, `2:3`, `3:2`, `9:16`, `16:9`, `21:9`, `9:21`, then `Custom ratio`. Mirror pairs: 4:5↔5:4, 3:4↔4:3, 2:3↔3:2, 9:16↔16:9, 21:9↔9:21, 1:1↔1:1.
- Chip tolerance for derived (non-listed) sizes: **7%** relative to the chip ratio. Authored list membership always wins.
- 1 MP = 1,048,576 px. Custom-ratio sizes use core Resolution Selector math: `scale = sqrt(mp·1048576/(rw·rh))`, each side `round(side/step)·step`, never below 64.
- Default family `SDXL`, default size 1024×1024, `batch_size` default 1, min 1, max 64. `width`/`height` widgets: default 1024, min 64, max 8192, step 8.
- Route: `GET /kikotools/model_resolution/families`, registered at module import like `local_image_loader/node.py`, guarded by `try/except ImportError`.
- Only `createScope()`, `mountTheme()`, `createButton()` and `controls.css` tokens for UI; new CSS classes are prefixed `.ca-resolution-`.
- Panel DOM widget is added with `serialize: false`; it mounts after the native widgets; new nodes start at 340 × 600.
- Never vendor Pixaroma code or assets. No external HTTP.
- Python coverage ≥ 85% overall; every new `web/*.js` file gets a row in `tools/testing/frontend-coverage-baseline.json`.
- Width Height Selector and Empty Latent Batch tests must keep passing unchanged.
- Commits: conventional type with scope, imperative subject, bullet body. No AI attribution lines.

## Review Focus

1. Typed width/height below 64 or not on the family step (e.g. 70×1000 on HunyuanImage 2.1): Python emits ≥ 64 on the step, the header shows the same effective size. Pinned in Task 1 (`round_to_step`) and Task 3 (`test_execution_rounds_to_family_step`).
2. Families route unavailable (network error or 500): panel shows one status line, native widgets and Swap still work, no page error. Pinned in Task 7 (`route failure keeps native widgets usable`).
3. Workflow saved with a former label or an unknown label: former label resolves through `aliases`; unknown label keeps the saved size (step 8). Pinned in Task 2 (`test_resolve_family_by_alias`) and Task 3 (`test_unknown_label_keeps_size_and_warns`).
4. `width` and `height` converted to inputs: chips and list disabled, header says "dimensions are wired in", Swap disabled. Pinned in Task 7 (`wired-in dimensions disable the picker`).
5. Custom ratio text such as `0:5`, `16:`, `a:b`, `99999999:1`: rejected with the inline error, previous list kept. Pinned in Task 5 (`parseRatio rejects malformed input`) and Task 7 (`custom ratio field`).

---

## File structure

| Path | Responsibility |
|---|---|
| `kikotools/tools/model_resolution_picker/logic.py` | step rounding, size generation, ratio label |
| `kikotools/tools/model_resolution_picker/families.py` | `Family` record, `CHIPS`, `MIRROR`, `FAMILIES`, lookup, JSON payload |
| `kikotools/tools/model_resolution_picker/node.py` | node class, route handler, module-level registration |
| `kikotools/tools/model_resolution_picker/__init__.py` | exports `ModelResolutionPickerNode` |
| `kikotools/__init__.py` | registration (modify) |
| `web/ui/dimensions.js` | swap without a `preset` widget (modify) |
| `web/ui/resolution-picker.js` | pure derivation and ratio math |
| `web/views/resolution-picker.js` | DOM view built from toolkit primitives |
| `web/model_resolution_picker.js` | extension: fetch families, mount view + swap, bind widgets |
| `web/ui/controls.css` | `.ca-resolution-*` rules (modify) |
| `tests/unit/tools/model_resolution_picker/` | `test_logic.py`, `test_families.py`, `test_node.py` |
| `tests/js/resolution-picker.test.mjs`, `tests/js/dimensions.test.mjs` | JS unit tests |
| `tests/browser/workflows.spec.mjs` | fixture-host workflows (modify) |
| `tests/comfyui/host-setup.mjs`, `tests/comfyui/resolution-picker.spec.mjs` | real-host coverage |
| `tools/testing/frontend-coverage-baseline.json` | floors for the 3 new JS files (modify) |
| `README.md`, `docs/ui-migration.md`, `examples/documentation/model_resolution_picker.md`, `docs/screenshots/resolution-picker/` | docs |

All pytest runs use the scratch venv: `V=/tmp/claude-1000/-home-vito-code-personal-ComfyUI-KikoTools/f79925f2-d12d-4383-ad2e-85d80c922cf7/scratchpad/venv; $V/bin/python -m pytest … -p no:cacheprovider`. Frontend: `npm test --prefix tools/testing`, `npm run --prefix tools/testing test:browser -- --project chromium`.

---

### Task 1: Rounding and size generation (`logic.py`)

**Files:**
- Create: `kikotools/tools/model_resolution_picker/__init__.py` (empty docstring for now), `kikotools/tools/model_resolution_picker/logic.py`
- Test: `tests/unit/tools/model_resolution_picker/__init__.py` (empty), `tests/unit/tools/model_resolution_picker/test_logic.py`

**Interfaces:**
- Produces: `round_to_step(value: int, step: int, minimum: int = 64) -> int`; `generate_size(ratio_w: int, ratio_h: int, megapixels: float, step: int) -> tuple[int, int]`; `ratio_label(width: int, height: int) -> str` (reduced `W:H` with aliases `8:5→16:10`, `5:8→10:16`, `7:3→21:9`, `3:7→9:21`); `MEGAPIXEL = 1_048_576`.

- [ ] **Step 1: Write the failing tests**

```python
from kikotools.tools.model_resolution_picker.logic import (
    MEGAPIXEL, generate_size, ratio_label, round_to_step)

def test_round_to_step_rounds_nearest_and_never_below_minimum():
    assert round_to_step(1000, 32) == 992
    assert round_to_step(1232, 16) == 1232
    assert round_to_step(70, 32) == 64
    assert round_to_step(10, 64) == 64
    assert round_to_step(1016, 64) == 1024

def test_generate_size_matches_core_resolution_selector():
    assert generate_size(1, 1, 1.0, 8) == (1024, 1024)
    assert generate_size(16, 9, 2.0, 16) == (1936, 1088)
    assert generate_size(3, 2, 4.0, 32) == (2496, 1664)
    assert generate_size(21, 9, 0.25, 64) == (768, 320)

def test_ratio_label_reduces_and_aliases():
    assert ratio_label(1024, 1024) == "1:1"
    assert ratio_label(1216, 832) == "19:13"
    assert ratio_label(1280, 800) == "16:10"
    assert ratio_label(1344, 576) == "21:9"
    assert MEGAPIXEL == 1024 * 1024
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$V/bin/python -m pytest tests/unit/tools/model_resolution_picker/test_logic.py -p no:cacheprovider -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement the three functions in `logic.py`**

`round_to_step`: nearest multiple, then `max(result, ceil(minimum/step)*step)`. `generate_size`: the Global Constraints formula, each side through `round_to_step`. `ratio_label`: `math.gcd`, then the alias dict.

- [ ] **Step 4: Run tests to verify they pass**

Run: same command. Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add kikotools/tools/model_resolution_picker/__init__.py kikotools/tools/model_resolution_picker/logic.py tests/unit/tools/model_resolution_picker/
git commit -m "feat(model_resolution_picker): add step rounding and size generation"
```

---

### Task 2: The family table (`families.py`)

**Files:**
- Create: `kikotools/tools/model_resolution_picker/families.py`
- Test: `tests/unit/tools/model_resolution_picker/test_families.py`

**Interfaces:**
- Consumes: `generate_size` from Task 1 (used once, by hand, to author the generated lists; not imported by `families.py`).
- Produces:
  - `CHIPS: tuple[str, ...]` in the Global Constraints order (11 chips, without `Custom ratio`).
  - `MIRROR: dict[str, str]`.
  - `class Family(NamedTuple)`: `label: str`, `aliases: tuple[str, ...]`, `models: str`, `group: str` (`"image"`|`"video"`), `vae_ratio: int`, `step: int`, `megapixels: tuple[float, ...]`, `default: tuple[int, int]`, `sizes: dict[str, tuple[tuple[int, int], ...]]`.
  - `FAMILIES: tuple[Family, ...]`, `DEFAULT_FAMILY = "SDXL"`.
  - `family_labels() -> list[str]`, `resolve_family(label: str) -> Family | None` (label or alias), `families_payload() -> dict` with keys `chips`, `mirror`, `default`, `families` (each: `label, aliases, models, group, vaeRatio, step, megapixels, default: [w, h], sizes: {chip: [[w, h], …]}`).

Authored data (copy verbatim; order of `FAMILIES` is this order):

| label | group | vae | step | MP tiers | default | official sizes to list verbatim; everything else generated with `generate_size` at each tier and chip |
|---|---|---|---|---|---|---|
| `SD 1.5` | image | 8 | 64 | 0.25, 0.5 | 512×512 | must include 512², 768², 512×768, 768×512 |
| `SDXL` (models: "SDXL, Pony and other SDXL finetunes") | image | 8 | 64 | 1.0 | 1024×1024 | 1:1 1024²; 4:5 832×1024; 5:4 1024×832; 3:4 896×1152; 4:3 1152×896; 2:3 832×1216; 3:2 1216×832; 9:16 768×1344; 16:9 1344×768; 21:9 1536×640; 9:21 640×1536. No generated entries. |
| `Illustrious XL` (aliases: none; models: "Illustrious XL v1.0 and later, NoobAI, WAI and other Illustrious finetunes") | image | 8 | 32 | 1.0, 1.5, 2.25 | 1024×1024 | all SDXL entries, plus 1:1 1536²; 4:5 1248×1536; 5:4 1536×1248; 3:4 1344×1792; 4:3 1792×1344; 2:3 1024×1536, 1248×1824; 3:2 1536×1024, 1824×1248; 9:16 1152×2048; 16:9 2048×1152. No generated entries. |
| `Anima` | image | 8 | 16 | 0.5, 1.0, 1.5 | 1024×1024 | generated; drop any entry with a side < 512 or > 1536 |
| `Flux.1` (models: "Flux.1 dev / schnell / Krea, Chroma, HiDream I1, SD3.5, Lumina 2") | image | 8 | 16 | 0.5, 1.0, 1.5, 2.0 | 1024×1024 | generated; must include 16:9 1920×1088 and 9:16 1088×1920 (replace the 2.0 MP generated entry) |
| `Z-Image` (models: "Z-Image Turbo and Z-Image Base") | image | 8 | 16 | 1.0, 1.6 | 1024×1024 | 1:1 1024², 1280²; 4:3 1152×896, 1152×864, 1440×1120, 1472×1104; 3:4 896×1152, 864×1152, 1120×1440, 1104×1472; 3:2 1248×832, 1536×1024; 2:3 832×1248, 1024×1536; 16:9 1280×720, 1600×896; 9:16 720×1280, 896×1600; 21:9 1344×576, 1680×720; 9:21 576×1344, 720×1680. 4:5 and 5:4 empty. |
| `Qwen-Image` (models: "Qwen-Image and Qwen-Image 2512") | image | 8 | 16 | 1.76 | 1328×1328 | 1:1 1328²; 16:9 1664×928; 9:16 928×1664; 4:3 1472×1104; 3:4 1104×1472; 3:2 1584×1056; 2:3 1056×1584. Other chips empty. |
| `Flux.2 / Klein / MOSS` (models: "Flux.2 dev, Flux.2 Klein, Flux.3 Klein, MOSS-Image, Ideogram 4") | image | 16 | 16 | 1.0, 2.0, 4.0 | 1024×1024 | generated; must include 3:2 1248×832, 2:3 832×1248, 1:1 2048², 16:9 1920×1088, 9:16 1088×1920 |
| `Qwen-Image 2.1` (models: "Qwen-Image 2.1 and 2.1 Turbo") | image | 16 | 32 | 1.0, 4.0 | 1024×1024 | 1:1 2048²; 4:3 2400×1792; 3:4 1792×2400; 3:2 2528×1696; 2:3 1696×2528; 16:9 2752×1536; 9:16 1536×2752; plus generated 1.0 MP entries for every chip |
| `HunyuanImage 2.1` | image | 32 | 32 | 4.0 | 2048×2048 | 1:1 2048²; 16:9 2560×1536; 9:16 1536×2560; 4:3 2304×1792; 3:4 1792×2304; 3:2 2496×1664; 2:3 1664×2496. Other chips empty. |
| `Wan 2.2 (keyframes)` | video | 16 | 16 | 0.4, 0.9 | 1280×720 | 16:9 832×480, 1280×720, 1280×704; 9:16 480×832, 720×1280, 704×1280; 1:1 640×640, 960×960; other chips generated |
| `LTX-2 (keyframes)` | video | 32 | 32 | 0.4, 0.9 | 768×512 | 3:2 768×512; 2:3 512×768; 16:9 960×544; 9:16 544×960; other chips generated |
| `HunyuanVideo 1.5 (keyframes)` | video | 16 | 16 | 0.4, 0.9 | 1280×720 | 16:9 848×480, 1280×720; 9:16 480×848, 720×1280; other chips generated |
| `MiniMax H3 (keyframes)` | video | 16 | 32 | 0.4, 1.0 | 864×480 | generated |

Every list is sorted by pixel count ascending; mirrored chips hold mirrored entries.

- [ ] **Step 1: Write the failing tests**

```python
from kikotools.tools.model_resolution_picker.families import (
    CHIPS, DEFAULT_FAMILY, FAMILIES, MIRROR, families_payload, family_labels, resolve_family)

CHIP_RATIO = {c: int(c.split(":")[0]) / int(c.split(":")[1]) for c in CHIPS}

def test_chip_order_and_mirrors():
    assert CHIPS == ("1:1", "4:5", "5:4", "3:4", "4:3", "2:3", "3:2", "9:16", "16:9", "21:9", "9:21")
    assert all(MIRROR[MIRROR[c]] == c for c in CHIPS)

def test_every_size_is_on_step_and_within_seven_percent_of_its_chip():
    for family in FAMILIES:
        for chip, entries in family.sizes.items():
            for w, h in entries:
                assert w % family.step == 0 and h % family.step == 0, (family.label, w, h)
                assert abs(w / h - CHIP_RATIO[chip]) / CHIP_RATIO[chip] <= 0.07, (family.label, chip, w, h)

def test_every_entry_has_its_mirror_and_lists_are_sorted():
    for family in FAMILIES:
        for chip, entries in family.sizes.items():
            assert list(entries) == sorted(entries, key=lambda s: s[0] * s[1])
            for w, h in entries:
                assert (h, w) in family.sizes.get(MIRROR[chip], ()), (family.label, chip, w, h)

def test_defaults_labels_and_must_includes():
    labels = family_labels()
    assert labels[0] == "SD 1.5" and "SDXL" in labels and DEFAULT_FAMILY == "SDXL"
    assert len(set(labels)) == len(labels)
    for family in FAMILIES:
        assert any(family.default in entries for entries in family.sizes.values()), family.label
    must = {"SDXL": ("16:9", (1344, 768)), "Flux.1": ("16:9", (1920, 1088)),
            "Flux.2 / Klein / MOSS": ("3:2", (1248, 832)), "Z-Image": ("21:9", (1680, 720)),
            "Qwen-Image": ("16:9", (1664, 928)), "Qwen-Image 2.1": ("16:9", (2752, 1536)),
            "HunyuanImage 2.1": ("16:9", (2560, 1536)), "Illustrious XL": ("2:3", (1248, 1824)),
            "Wan 2.2 (keyframes)": ("16:9", (1280, 704)), "MiniMax H3 (keyframes)": ("16:9", (864, 480))}
    for label, (chip, size) in must.items():
        assert size in resolve_family(label).sizes[chip], label

def test_resolve_family_by_alias_and_unknown():
    assert resolve_family("SDXL").step == 64
    assert resolve_family("nope") is None

def test_payload_is_json_shaped():
    payload = families_payload()
    assert payload["default"] == "SDXL" and payload["chips"] == list(CHIPS)
    sdxl = next(f for f in payload["families"] if f["label"] == "SDXL")
    assert sdxl["sizes"]["3:2"] == [[1216, 832]] and sdxl["vaeRatio"] == 8 and sdxl["group"] == "image"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$V/bin/python -m pytest tests/unit/tools/model_resolution_picker/test_families.py -p no:cacheprovider -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Author `families.py`**

Produce generated entries with a one-off snippet calling `generate_size` for each chip and tier, apply the "must include" replacements and the Anima range filter, sort, then paste the literals. `families_payload()` converts tuples to lists.

- [ ] **Step 4: Run tests to verify they pass**

Run: same command. Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add kikotools/tools/model_resolution_picker/families.py tests/unit/tools/model_resolution_picker/test_families.py
git commit -m "feat(model_resolution_picker): add the model family resolution table"
```

---

### Task 3: Node, route and registration

**Files:**
- Create: `kikotools/tools/model_resolution_picker/node.py`
- Modify: `kikotools/tools/model_resolution_picker/__init__.py`, `kikotools/__init__.py` (import + both mapping dicts, next to `EmptyLatentBatch`)
- Test: `tests/unit/tools/model_resolution_picker/test_node.py`

**Interfaces:**
- Consumes: `resolve_family`, `family_labels`, `families_payload`, `DEFAULT_FAMILY` (Task 2); `round_to_step` (Task 1); `create_empty_latent_batch(width, height, batch_size)` from `kikotools/tools/empty_latent_batch/logic.py`.
- Produces: `class ModelResolutionPickerNode(ComfyAssetsBaseNode)` with `INPUT_TYPES` (`model` COMBO of `family_labels()` default `DEFAULT_FAMILY`, tooltip "Model family; the chips list its preferred sizes", `width`, `height`, `batch_size` per Global Constraints), `RETURN_TYPES = ("LATENT", "INT", "INT")`, `RETURN_NAMES = ("latent", "width", "height")`, `FUNCTION = "create"`, `create(self, model, width, height, batch_size) -> tuple[dict, int, int]`; `async def get_families(request) -> web.Response` (JSON of `families_payload()`); module-level registration of `GET /kikotools/model_resolution/families` in a `try: import server … except ImportError: pass` block.

- [ ] **Step 1: Write the failing tests**

```python
import asyncio, json, logging
from kikotools.tools.model_resolution_picker.node import ModelResolutionPickerNode, get_families

def test_inputs_and_outputs():
    inputs = ModelResolutionPickerNode.INPUT_TYPES()["required"]
    assert inputs["model"][1]["default"] == "SDXL" and "HunyuanImage 2.1" in inputs["model"][0]
    width = inputs["width"][1]
    assert (width["default"], width["min"], width["max"], width["step"]) == (1024, 64, 8192, 8)
    assert ModelResolutionPickerNode.RETURN_TYPES == ("LATENT", "INT", "INT")
    assert ModelResolutionPickerNode.CATEGORY == "🫶 ComfyAssets/🖼️ Resolution"

def test_execution_rounds_to_family_step_and_marks_latent():
    latent, w, h = ModelResolutionPickerNode().create("HunyuanImage 2.1", 70, 1000, 2)
    assert (w, h) == (64, 992)
    assert latent["samples"].shape == (2, 4, 124, 8) and latent["downscale_ratio_spacial"] == 8

def test_exact_sizes_pass_through():
    _, w, h = ModelResolutionPickerNode().create("Flux.2 / Klein / MOSS", 1248, 832, 1)
    assert (w, h) == (1248, 832)

def test_unknown_label_keeps_size_and_warns(caplog):
    with caplog.at_level(logging.WARNING):
        _, w, h = ModelResolutionPickerNode().create("Renamed Family", 1000, 1000, 1)
    assert (w, h) == (1000, 1000) and "Renamed Family" in caplog.text

def test_families_route_returns_payload():
    response = asyncio.run(get_families(None))
    assert response.status == 200 and json.loads(response.text)["default"] == "SDXL"

def test_registered_in_kikotools():
    from kikotools import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    assert NODE_CLASS_MAPPINGS["ModelResolutionPicker"] is ModelResolutionPickerNode
    assert NODE_DISPLAY_NAME_MAPPINGS["ModelResolutionPicker"] == "Model Resolution Picker"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$V/bin/python -m pytest tests/unit/tools/model_resolution_picker/test_node.py -p no:cacheprovider -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement `node.py`, export it, register it**

`create`: resolve → `step = family.step if family else 8`, warning via `logger.warning` when `None`; round both sides; `log_info` when a value changed; build the latent; return. `get_families` returns `web.json_response(families_payload())`.

- [ ] **Step 4: Run the new tests, then the whole Python suite with coverage**

Run: `$V/bin/python -m pytest tests/unit/tools/model_resolution_picker -p no:cacheprovider -q` → `6 passed`
Run: `$V/bin/python -m pytest tests -p no:cacheprovider -q --cov=kikotools | tail -3` → all passed, coverage ≥ 85%
Run: `$V/bin/black --check kikotools tests && $V/bin/flake8 kikotools/tools/model_resolution_picker` → clean

- [ ] **Step 5: Commit**

```bash
git add kikotools/tools/model_resolution_picker kikotools/__init__.py tests/unit/tools/model_resolution_picker/test_node.py
git commit -m "feat(model_resolution_picker): add node, families route and registration"
```

---

### Task 4: Swap without a preset widget (`web/ui/dimensions.js`)

**Files:**
- Modify: `web/ui/dimensions.js:904-932` (`swapDimensions`)
- Test: `tests/js/dimensions.test.mjs`

**Interfaces:**
- Produces: `swapDimensions(node, app)` now swaps when the node has `width` and `height` widgets but no `preset` widget, taking the existing custom path (direct swap, callbacks once each, dirty canvas). Behavior with a `preset` widget is unchanged.

- [ ] **Step 1: Write the failing test**

```js
test('nodes without a preset widget swap width and height directly', () => {
    const calls = [];
    const node = { widgets: [
        { name: 'width', value: 1344, callback(value) { calls.push(['width', value]); } },
        { name: 'height', value: 768, callback(value) { calls.push(['height', value]); } },
    ], graph: { setDirtyCanvas() { calls.push(['dirty']); } } };
    swapDimensions(node, app);
    assert.deepEqual(node.widgets.map(widget => widget.value), [768, 1344]);
    assert.deepEqual(calls, [['width', 768], ['height', 1344], ['dirty']]);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test --prefix tools/testing -- ../../tests/js/dimensions.test.mjs` (or `node --test tests/js/dimensions.test.mjs`)
Expected: FAIL, values unchanged

- [ ] **Step 3: Change the guard**

`if (!width || !height || swapping.has(node)) return; const custom = !preset || preset.value === 'custom';` and leave every `preset.*` access behind `!custom`.

- [ ] **Step 4: Run the JS unit tests**

Run: `npm test --prefix tools/testing` Expected: all pass, including the existing dimensions tests

- [ ] **Step 5: Commit**

```bash
git add web/ui/dimensions.js tests/js/dimensions.test.mjs
git commit -m "feat(ui): let swapDimensions work on nodes without a preset widget"
```

---

### Task 5: Derivation module (`web/ui/resolution-picker.js`)

**Files:**
- Create: `web/ui/resolution-picker.js`
- Test: `tests/js/resolution-picker.test.mjs`

**Interfaces:**
- Consumes: the families payload shape from Task 2.
- Produces (all pure, no DOM):
  - `parseRatio(text) -> [w, h] | null` — accepts `W:H`, `W/H`, `WxH`, `W×H`, surrounding whitespace; integers 1–10000; else `null`.
  - `reducedRatio(width, height) -> string` — same rule and aliases as Python `ratio_label`.
  - `findFamily(payload, label) -> family | null` — label or alias.
  - `deriveSelection(payload, label, width, height) -> { family, chip, entryIndex, custom, ratioText }` — `chip` is the chip whose list holds `[width, height]`; else nearest chip within 7%; else `null` with `custom: true` and `ratioText` from `reducedRatio`. `entryIndex` is the index in `family.sizes[chip]` or `-1`.
  - `sizesForRatio(family, [rw, rh]) -> [[w, h], …]` — one per tier, Global Constraints formula, deduped, ascending.
  - `defaultEntry(family, chip) -> [w, h] | null` — entry of `family.sizes[chip]` with pixel count closest to `family.default`'s.
  - `effectiveSize(family, width, height) -> [w, h]` — rounded to `family.step` (8 when `family` is null), ≥ 64.
  - `megapixels(width, height) -> string` — one decimal, e.g. `"1.0"`.
  - `sizeOnModelChange(payload, newLabel, width, height, chip) -> [w, h]` — keep if listed in the new family; else `defaultEntry(newFamily, chip)` when non-null; else `newFamily.default`.

- [ ] **Step 1: Write the failing tests** (use a fixture payload with `SDXL` (step 64, default 1024², sizes 1:1 1024², 3:2 1216×832, 2:3 832×1216, 16:9 1344×768, 9:16 768×1344) and `HunyuanImage 2.1` (step 32, default 2048², 1:1 2048², 16:9 2560×1536, 9:16 1536×2560), plus `aliases: ['SDXL 1.0']` on SDXL)

```js
test('parseRatio accepts the documented forms and rejects malformed input', () => {
    for (const text of ['16:9', ' 16 / 9 ', '16x9', '16×9']) assert.deepEqual(parseRatio(text), [16, 9]);
    for (const text of ['0:5', '16:', 'a:b', '99999999:1', '', null]) assert.equal(parseRatio(text), null);
});
test('deriveSelection prefers authored membership, then the 7% band, then custom', () => {
    assert.deepEqual(deriveSelection(payload, 'HunyuanImage 2.1', 2560, 1536), { family: payload.families[1], chip: '16:9', entryIndex: 0, custom: false, ratioText: '5:3' });
    assert.equal(deriveSelection(payload, 'SDXL', 1200, 800).chip, '3:2');           // 1.5 exactly, not listed
    assert.equal(deriveSelection(payload, 'SDXL', 1200, 800).entryIndex, -1);
    const custom = deriveSelection(payload, 'SDXL', 1600, 800);          // 2:1 is >7% from every chip
    assert.deepEqual([custom.chip, custom.custom, custom.ratioText], [null, true, '2:1']);
    assert.equal(deriveSelection(payload, 'SDXL 1.0', 1024, 1024).chip, '1:1');      // alias
    assert.equal(deriveSelection(payload, 'nope', 1024, 1024).family, null);
});
test('sizesForRatio follows the core formula per tier and effectiveSize rounds to the step', () => {
    assert.deepEqual(sizesForRatio({ step: 16, megapixels: [1, 2] }, [16, 9]), [[1360, 768], [1936, 1088]]);
    assert.deepEqual(effectiveSize(payload.families[1], 70, 1000), [64, 992]);
    assert.deepEqual(effectiveSize(null, 1001, 1001), [1000, 1000]);
    assert.equal(megapixels(1216, 832), '1.0');
});
test('model change keeps listed sizes, else the same chip default, else the family default', () => {
    assert.deepEqual(sizeOnModelChange(payload, 'HunyuanImage 2.1', 2560, 1536, '16:9'), [2560, 1536]);
    assert.deepEqual(sizeOnModelChange(payload, 'HunyuanImage 2.1', 1344, 768, '16:9'), [2560, 1536]);
    assert.deepEqual(sizeOnModelChange(payload, 'HunyuanImage 2.1', 1216, 832, '3:2'), [2048, 2048]);
    assert.deepEqual(defaultEntry(payload.families[0], '21:9'), null);
});
```

- [ ] **Step 2: Run to verify failure** — `node --test tests/js/resolution-picker.test.mjs` → FAIL (module missing)

- [ ] **Step 3: Implement the module** — plain functions; `sizesForRatio` uses `Math.round(side / step) * step` with the 64 floor; nearest-chip selection picks the smallest relative error.

- [ ] **Step 4: Run** — `npm test --prefix tools/testing` → all pass

- [ ] **Step 5: Commit**

```bash
git add web/ui/resolution-picker.js tests/js/resolution-picker.test.mjs
git commit -m "feat(ui): add resolution picker derivation module"
```

---

### Task 6: View, extension and first browser workflows

**Files:**
- Create: `web/views/resolution-picker.js`, `web/model_resolution_picker.js`
- Modify: `web/ui/controls.css` (append `.ca-resolution-*` rules), `tests/browser/workflows.spec.mjs`

**Interfaces:**
- Consumes: Task 5 functions; `createScope`, `mountTheme`, `createButton` from `web/ui/core.js`; `mountDimensionSwap` from `web/ui/dimension-swap.js`; `swapDimensions` (Task 4); `api.fetchApi` from `../../scripts/api.js`.
- Produces:
  - `createResolutionPickerView(scope, actions) -> { element, render(state), setStatus(text, isError) }` in `web/views/resolution-picker.js`. `actions = { selectChip(chip), openCustom(), commitRatio(text), selectSize(w, h) }`. `state = { disabled: boolean, header: string, chips: [{ id, label, active, disabled }], customOpen: boolean, ratioText: string, entries: [{ w, h, active }], error: string | null }`. Markup: `element.className = 'ca-tools ca-resolution-picker'`; header `<p class="ca-resolution-header">`; chips in `<div class="ca-resolution-chips" role="group" aria-label="Aspect ratio">` as `<button type="button" aria-pressed>` with text `1:1` … and a last chip `Custom ratio`; sizes in `<div class="ca-resolution-sizes" role="group" aria-label="Resolution">` as `<button type="button" aria-pressed>` with text `1216 × 832`; custom mode shows `<input aria-label="Custom ratio" placeholder="16:9">` (commit on Enter and on `change`) above the generated sizes; status `<p class="ca-resolution-status" role="status">`.
  - Extension `comfyassets.ModelResolutionPicker` in `web/model_resolution_picker.js`: `beforeRegisterNodeDef` for `nodeData.name === 'ModelResolutionPicker'`; in `onNodeCreated`: `this.setSize([340, 600])`, create scope, mount view with `this.addDOMWidget('resolution_picker', 'div', view.element, { serialize: false, hideOnZoom: false, getMinHeight: () => 320 })`, `mountTheme`, `this.swapDimensions = () => { swapDimensions(this, app); render(); }`, `this.createSwapButton = () => mountDimensionSwap(this, app)` then call it, wrap the `model`/`width`/`height` widget callbacks to call the original then `render()`, `onRemoved` disposes the scope and preserves the previous hook's return. Families are loaded once per page via a module-level `loadFamilies(api)` promise using `api.fetchApi('/kikotools/model_resolution/families')`; while loading the view renders `disabled: true` with header `Loading sizes…`; on failure header `Sizes unavailable; type width and height` via `setStatus(…, true)` and chips stay disabled. Custom-ratio open flag and pending text live on the node instance (`this.resolutionCustom = { open, text }`), never serialized. Wired-in check: `node.inputs?.some(input => input.widget?.name === name && input.link != null)` for `width` or `height` → `disabled: true`, header `Dimensions are wired in`, and the swap button `disabled`.
  - Writing a size: set `width.value`/`height.value`, call each widget's `callback(value, app.canvas, node, [0, 0], null)` once, `node.graph?.setDirtyCanvas?.(true, true)`.

- [ ] **Step 1: Write the failing browser tests** (append to `tests/browser/workflows.spec.mjs`; the fixture host creates text inputs for the initial keys and serves the real route because `node.py` registered it on the stubbed `PromptServer`)

```js
test('resolution picker renders chips from the families route and writes sizes to native widgets', async ({ page, request }) => {
    await openHost(page);
    const payload = await (await request.get('/kikotools/model_resolution/families')).json();
    expect(payload.default).toBe('SDXL');
    await createNode(page, 'ModelResolutionPicker', { model: 'SDXL', width: 1024, height: 1024, batch_size: 1 });
    const panel = page.locator('.ca-resolution-picker');
    await expect(panel.getByRole('button', { name: '1:1', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(panel.locator('.ca-resolution-header')).toHaveText('1024 × 1024 · 1:1 · 1.0 MP');
    await panel.getByRole('button', { name: '3:2', exact: true }).click();
    const node = page.locator('[data-node="ModelResolutionPicker"]');
    await expect(node.getByLabel('width', { exact: true })).toHaveValue('1216');
    await expect(node.getByLabel('height', { exact: true })).toHaveValue('832');
    await expect(panel.getByRole('button', { name: '1216 × 832', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(panel.getByRole('button', { name: '21:9', exact: true })).toBeEnabled();
    for (const theme of ['light', 'dark']) {
        await page.evaluate(theme => document.body.style.setProperty('--bg-color', theme === 'light' ? '#fff' : '#202020'), theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
    }
    expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
});

test('resolution picker mounting is idempotent and removal disposes its scope', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'ModelResolutionPicker', { model: 'SDXL', width: 1024, height: 1024, batch_size: 1 });
    await page.evaluate(id => { const node = kikoHost.nodes.get(String(id)); node.createSwapButton(); node.createSwapButton(); }, id);
    await expect(page.locator('.ca-resolution-picker')).toHaveCount(1);
    await expect(page.locator('.ca-dimension-swap')).toHaveCount(1);
    const aborted = await page.evaluate(id => { const node = kikoHost.nodes.get(String(id)); kikoHost.removeNode(id); return node.resolutionScope.signal.aborted; }, id);
    expect(aborted).toBe(true);
    await expect(page.locator('.ca-resolution-picker')).toHaveCount(0);
});
```

- [ ] **Step 2: Run to verify failure** — `npm run --prefix tools/testing test:browser -- --project chromium -g "resolution picker"` → FAIL (no panel)

- [ ] **Step 3: Implement the view, the CSS and the extension**

CSS: chips grid `grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px`; active chip and active size use `--ca-accent` background with `#fff` text (same as `.ca-primary`); size list is a single column of full-width buttons; header uses `--ca-muted`; everything inherits the `.ca-tools` tokens so light/dark follow `data-ca-theme`. Expose the scope as `node.resolutionScope` for the disposal test.

- [ ] **Step 4: Run the browser suite and the JS unit suite** — `npm run --prefix tools/testing test:browser -- --project chromium` and `npm test --prefix tools/testing` → all pass, no page errors

- [ ] **Step 5: Commit**

```bash
git add web/views/resolution-picker.js web/model_resolution_picker.js web/ui/controls.css tests/browser/workflows.spec.mjs
git commit -m "feat(model_resolution_picker): add the chip grid panel and extension"
```

---

### Task 7: Swap, model change, custom ratio, wired-in, route failure; coverage floors

**Files:**
- Modify: `web/model_resolution_picker.js`, `web/views/resolution-picker.js` (only as the tests demand), `tests/browser/workflows.spec.mjs`, `tools/testing/frontend-coverage-baseline.json`

**Interfaces:**
- Consumes: Task 6 extension and view; `sizeOnModelChange`, `sizesForRatio`, `parseRatio` (Task 5).

- [ ] **Step 1: Write the failing browser tests**

```js
test('resolution picker swap lands on the mirrored chip and entry', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'ModelResolutionPicker', { model: 'SDXL', width: 1344, height: 768, batch_size: 1 });
    const panel = page.locator('.ca-resolution-picker');
    await page.locator('.ca-dimension-swap').getByRole('button', { name: 'Swap width and height', exact: true }).click();
    await expect(panel.getByRole('button', { name: '9:16', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(panel.getByRole('button', { name: '768 × 1344', exact: true })).toHaveAttribute('aria-pressed', 'true');
});

test('resolution picker model change keeps listed sizes or falls back to the chip default', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'ModelResolutionPicker', { model: 'SDXL', width: 1344, height: 768, batch_size: 1 });
    const node = page.locator('[data-node="ModelResolutionPicker"]');
    await node.getByLabel('model', { exact: true }).fill('HunyuanImage 2.1');
    await node.getByLabel('model', { exact: true }).dispatchEvent('change');
    await expect(node.getByLabel('width', { exact: true })).toHaveValue('2560');
    await expect(node.getByLabel('height', { exact: true })).toHaveValue('1536');
    await expect(page.locator('.ca-resolution-header')).toHaveText('2560 × 1536 · 16:9 · 3.8 MP');
});

test('resolution picker custom ratio field computes tiers and rejects bad input', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'ModelResolutionPicker', { model: 'Flux.1', width: 1024, height: 1024, batch_size: 1 });
    const panel = page.locator('.ca-resolution-picker');
    await panel.getByRole('button', { name: 'Custom ratio', exact: true }).click();
    const field = panel.getByLabel('Custom ratio', { exact: true });
    await expect(field).toHaveValue('1:1');
    await field.fill('16:10'); await field.press('Enter');
    await expect(panel.getByRole('button', { name: '1296 × 816', exact: true })).toBeVisible();   // 1.0 MP, step 16
    await panel.getByRole('button', { name: '1296 × 816', exact: true }).click();
    await expect(page.locator('[data-node="ModelResolutionPicker"]').getByLabel('width', { exact: true })).toHaveValue('1296');
    await field.fill('a:b'); await field.press('Enter');
    await expect(panel.locator('.ca-resolution-status')).toHaveText(/Enter a ratio like 16:9/);
    await expect(panel.getByRole('button', { name: '1296 × 816', exact: true })).toBeVisible();
});

test('wired-in dimensions disable the picker and swap', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'ModelResolutionPicker', { model: 'SDXL', width: 1024, height: 1024, batch_size: 1 });
    await page.evaluate(id => { const node = kikoHost.nodes.get(String(id)); node.inputs.push({ name: 'width', widget: { name: 'width' }, link: 7 }); node.widgets.find(w => w.name === 'width').callback('1024', kikoHost.app.canvas, node, [0, 0], null); }, id);
    const panel = page.locator('.ca-resolution-picker');
    await expect(panel.locator('.ca-resolution-header')).toHaveText('Dimensions are wired in');
    await expect(panel.getByRole('button', { name: '3:2', exact: true })).toBeDisabled();
    await expect(page.locator('.ca-dimension-swap').getByRole('button')).toBeDisabled();
});

test('route failure keeps native widgets usable', async ({ page }) => {
    await page.route('**/kikotools/model_resolution/families', route => route.fulfill({ status: 500, body: 'nope' }));
    await openHost(page);
    await createNode(page, 'ModelResolutionPicker', { model: 'SDXL', width: 1024, height: 1024, batch_size: 1 });
    const panel = page.locator('.ca-resolution-picker');
    await expect(panel.locator('.ca-resolution-status')).toHaveText('Sizes unavailable; type width and height');
    await expect(panel.getByRole('button', { name: '1:1', exact: true })).toBeDisabled();
    await page.locator('.ca-dimension-swap').getByRole('button').click();
    await expect(page.locator('[data-node="ModelResolutionPicker"]').getByLabel('width', { exact: true })).toHaveValue('1024');
});
```

The 500 response must not be counted as a page error: the fixture's `afterEach` collects responses ≥ 500, so this test registers its route before `openHost` and removes the 500 URL from `page.errors` at the end (`page.errors = page.errors.filter(e => !e.includes('families'))`).

- [ ] **Step 2: Run to verify failure** — `npm run --prefix tools/testing test:browser -- --project chromium -g "resolution picker|wired-in|route failure"` → the new tests FAIL

- [ ] **Step 3: Implement the remaining behavior** — model-change handler uses `sizeOnModelChange`; custom field uses `parseRatio` + `sizesForRatio`, error copy `Enter a ratio like 16:9`; the fixture model widget is a text input, so the extension must listen to the widget callback, not to a `<select>`.

- [ ] **Step 4: Add coverage floors and run everything frontend**

Add rows for `model_resolution_picker.js`, `ui/resolution-picker.js`, `views/resolution-picker.js` to `tools/testing/frontend-coverage-baseline.json`, then:
Run: `npm test --prefix tools/testing && npm run --prefix tools/testing test:browser -- --project chromium && npm run --prefix tools/testing test:coverage`
Expected: all pass; set each new row to the measured values rounded down to the nearest whole percent (never below 80 for lines/statements).

- [ ] **Step 5: Commit**

```bash
git add web/model_resolution_picker.js web/views/resolution-picker.js tests/browser/workflows.spec.mjs tools/testing/frontend-coverage-baseline.json
git commit -m "feat(model_resolution_picker): model change, custom ratio, wired-in and failure handling"
```

---

### Task 8: Real-host coverage (both renderers, workflow round-trip)

**Files:**
- Create: `tests/comfyui/host-setup.mjs`, `tests/comfyui/resolution-picker.spec.mjs`
- Modify: `tests/comfyui/image-browser.spec.mjs:1-60` (import the shared `beforeEach` instead of its inline copy)

**Interfaces:**
- Produces: `installHost(test, expect)` in `host-setup.mjs` that registers exactly the existing `beforeEach` (versions check, fixture reset, route proxying, settings override, extension filter, `app.graph.clear()`), with `/kikotools/model_resolution/` added to the list of prefixes proxied to the fixture server so the route is deterministic.

- [ ] **Step 1: Extract the shared setup and confirm the existing spec still passes**

Run: `KIKO_COMFY_ROOT=… npm run --prefix tools/testing test:comfyui` (or against `KIKO_COMFY_URL`; see `TESTING.md`). Expected: unchanged results for `image-browser.spec.mjs`.

- [ ] **Step 2: Write the failing real-host test** (mirrors the sibling swap test at `image-browser.spec.mjs:61-150`)

```js
test('resolution picker survives renderers, swap, themes and workflow reload', async ({ page }, testInfo) => {
    await page.evaluate(async () => { const { app } = await import('/scripts/app.js'); const node = LiteGraph.createNode('ModelResolutionPicker'); app.graph.add(node); app.canvas.centerOnNode(node); });
    const panel = page.locator('.ca-resolution-picker');
    await expect(panel.getByRole('button', { name: '1:1', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await panel.getByRole('button', { name: '16:9', exact: true }).click();
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => { const { app } = await import('/scripts/app.js'); await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer); }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await expect(panel).toHaveCount(1);
        await page.locator('.ca-dimension-swap').getByRole('button', { name: 'Swap width and height', exact: true }).click();
    }
    await expect(panel.getByRole('button', { name: '9:16', exact: true })).toHaveAttribute('aria-pressed', 'true');   // three swaps from 16:9
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => { const { app } = await import('/scripts/app.js'); await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme); }, theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
        await page.screenshot({ path: testInfo.outputPath(`ModelResolutionPicker-${theme}.png`) });
    }
    const restored = await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const workflow = app.graph.serialize();
        const saved = workflow.nodes.find(node => node.type === 'ModelResolutionPicker');
        if (saved.widgets_values.slice(4).some(value => value !== '' && value != null)) throw new Error('Picker UI leaked into workflow values');
        await app.loadGraphData(workflow);
        const node = app.graph._nodes.find(node => node.type === 'ModelResolutionPicker');
        return { saved: saved.widgets_values.slice(0, 4), restored: node.widgets.filter(w => ['model', 'width', 'height', 'batch_size'].includes(w.name)).map(w => w.value), size: Array.from(node.size), savedSize: Array.from(saved.size) };
    });
    expect(restored.restored).toEqual(restored.saved);
    expect(restored.size).toEqual(restored.savedSize);
    await expect(panel.getByRole('button', { name: '9:16', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await page.evaluate(async () => { const { app } = await import('/scripts/app.js'); const node = app.graph._nodes.find(node => node.type === 'ModelResolutionPicker'); window.removedPicker = node; app.graph.remove(node); });
    await expect(panel).toHaveCount(0);
    expect(await page.evaluate(() => removedPicker.resolutionScope.signal.aborted)).toBe(true);
});
```

- [ ] **Step 3: Run it against the pinned host for both projects** — `npm run --prefix tools/testing test:comfyui` → `classic-start` and `nodes2-start` pass. Fix extension behavior if a renderer differs; do not special-case the test.

- [ ] **Step 4: Copy the two screenshots** from the test output to `docs/screenshots/resolution-picker/ModelResolutionPicker-{light,dark}.png` (used by Task 9).

- [ ] **Step 5: Commit**

```bash
git add tests/comfyui/host-setup.mjs tests/comfyui/resolution-picker.spec.mjs tests/comfyui/image-browser.spec.mjs docs/screenshots/resolution-picker
git commit -m "test(model_resolution_picker): cover both renderers and workflow round-trip on the pinned host"
```

---

### Task 9: Documentation

**Files:**
- Modify: `README.md` (tools table after the `Empty Latent Batch` row at line 44; a `#### 🎯 Model Resolution Picker` section after `#### 📦 Empty Latent Batch`; the status table near line 801), `docs/ui-migration.md` (table row `Model Resolution Picker | views/resolution-picker.js, ui/resolution-picker.js, shared swap | [Picker](screenshots/resolution-picker/)`), `web/ui/README.md` (a short "Model Resolution Picker" section stating: derived state only, in-memory custom-ratio flag, families route, disabled chips for empty lists)
- Create: `examples/documentation/model_resolution_picker.md` (inputs, outputs, the family table with labels and steps, the keyframe note for video families, the manual GPU check procedure from the spec's "Verification before merge")

- [ ] **Step 1: Write the docs** — copy the family labels and steps from `families.py`; README section bullets: model dropdown; chips and list; Swap; custom ratio and custom resolution rounding; outputs; "video rows are keyframe sizes, the latent is an image latent".

- [ ] **Step 2: Verify links** — `grep -n "resolution-picker\|model_resolution_picker" README.md docs/ui-migration.md web/ui/README.md` shows every referenced path exists (`ls` each).

- [ ] **Step 3: Commit**

```bash
git add README.md docs/ui-migration.md web/ui/README.md examples/documentation/model_resolution_picker.md
git commit -m "docs(model_resolution_picker): document the node, families and keyframe use"
```

---

### Task 10: Full verification and manual GPU check

**Files:** none new.

- [ ] **Step 1: Run every suite**

```
$V/bin/python -m pytest tests -p no:cacheprovider -q --cov=kikotools | tail -3
$V/bin/black --check . && $V/bin/flake8 kikotools
npm test --prefix tools/testing && npm run --prefix tools/testing test:coverage
npm run --prefix tools/testing test:browser
npm run --prefix tools/testing test:comfyui
```
Expected: all green; Python coverage ≥ 85%; frontend floors met; Width Height Selector and Empty Latent Batch tests untouched and passing.

- [ ] **Step 2: Manual generation check on the user's ComfyUI** (spec: "Verification before merge"): one queued image each for `Flux.2 / Klein / MOSS` at 1248×832 and `HunyuanImage 2.1` at 2560×1536 through this node → KSampler → VAE Decode → Save; confirm the saved PNGs are exactly those sizes. Record both results in the PR description. This step needs the user's GPU box; if it cannot run, say so in the PR and mark it as a pre-merge TODO.

- [ ] **Step 3: Hand off** — use `superpowers:finishing-a-development-branch` (push with the explicit refspec, PR against `main`).

---

## Addendum tasks (spec addendum 2026-10-27: JSON table, user override, resolution dropdown)

Global Constraints additions: the shipped file is `kikotools/tools/model_resolution_picker/families.json`; the override is `<user_dir>/kikotools/model_resolutions.json`; dropdown label format `{w}×{h} - {ratio} ({mp:.1f}MP)` with `custom` first; `resolution` COMBO sits between `model` and `width`; `VALIDATE_INPUTS(cls, model, resolution)` returns True; an invalid override is ignored whole, logged, and surfaced as `warnings` in the payload; workflows serialize five native widgets.

### Task 11: Shipped JSON table with a runtime validator

**Files:**
- Create: `kikotools/tools/model_resolution_picker/families.json`, `kikotools/tools/model_resolution_picker/table.py`
- Modify: `kikotools/tools/model_resolution_picker/families.py` (becomes a thin loader), `pyproject.toml` (package-data for `*.json` under `kikotools`)
- Test: `tests/unit/tools/model_resolution_picker/test_table.py`; `test_families.py` keeps passing unchanged

**Interfaces:**
- Produces in `table.py`: `load_table(path: Path) -> dict` (JSON load; raises `ValueError` with the path on bad JSON); `validate_table(data: dict) -> list[str]` (returns human-readable problems, empty when valid; checks: top-level keys and `version == 1`, chips equal `CHIPS`, mirror consistent, unique labels/aliases across families, every chip key present per family, sizes on step, 7% tolerance, exact mirrors, ascending order, one chip per size, default present in sizes, `group` in {image, video}, `vaeRatio` in {8, 16, 32}, `step` > 0, non-empty `megapixels`); `build_families(data: dict) -> tuple[Family, ...]`.
- `families.py` keeps exporting `CHIPS`, `MIRROR`, `Family`, `FAMILIES`, `DEFAULT_FAMILY`, `family_labels`, `resolve_family`, `families_payload`, now built from `families.json` at import; a validation failure raises `RuntimeError` listing the problems.

- [ ] **Step 1: Write the failing tests** — `test_validate_table_accepts_the_shipped_file` (loads the shipped path, `validate_table` returns `[]`), `test_validate_table_reports_each_invariant` (parametrized: a copy of the shipped data mutated to break one rule each — off-step size, >7% size, missing mirror, unsorted list, duplicate size under two chips, duplicate label, missing chip key, default not listed, bad vaeRatio — must produce exactly one message naming the family and chip), `test_load_table_bad_json_names_the_path`, `test_families_module_is_built_from_json` (`FAMILIES` labels equal the JSON labels in order).
- [ ] **Step 2: Run to verify failure** — `$V/bin/python -m pytest tests/unit/tools/model_resolution_picker/test_table.py -p no:cacheprovider -q` → ImportError.
- [ ] **Step 3: Generate `families.json` from the current `FAMILIES`** with a one-off snippet (`families_payload()` plus `"version": 1`), indent 2, then rewrite `families.py` to load/validate/build; delete the literals; keep the source comments as a `"notes"` string per family (the validator ignores unknown keys).
- [ ] **Step 4: Run** the new tests, `test_families.py`, the full suite with coverage, black and flake8.
- [ ] **Step 5: Commit** — `refactor(model_resolution_picker): move the family table to families.json with a validator`.

### Task 12: User override file

**Files:**
- Create: `kikotools/tools/model_resolution_picker/override.py`
- Modify: `families.py` (resolution and payload consult the merged table), `node.py` (route payload includes `warnings`)
- Test: `tests/unit/tools/model_resolution_picker/test_override.py`, `test_node.py`

**Interfaces:**
- Produces: `override_path() -> Path | None` (uses `folder_paths.get_user_directory()`; `None` when `folder_paths` or the function is unavailable); `merge_override(shipped: dict, override: dict) -> dict` (rules from the spec: replace by label, append new, `remove`, `default`); `current_table() -> tuple[dict, list[str]]` (shipped merged with a valid override, cached by override mtime; returns `(merged_data, warnings)`; an unreadable/invalid override yields the shipped data plus one `"Override ignored: <reason>"` warning and a `logger.warning`).
- `families.py`: `resolve_family(label)` and `families_payload()` use `current_table()`; `families_payload()["warnings"]` is the warnings list; `FAMILIES` remains the shipped tuple for tests.

- [ ] **Step 1: Write the failing tests** — with `tmp_path` as a fake user directory (patch `folder_paths` in `sys.modules` with `get_user_directory`): override replaces SDXL's `sizes` and `resolve_family("SDXL")` reflects it; a new family `My Model` appears last in `families_payload()["families"]` and resolves; `"remove": ["SD 1.5"]` hides it; invalid JSON → shipped data, `warnings == ["Override ignored: <path>: <json error>"]` and a warning log; an override whose merged result breaks an invariant (e.g. off-step size) → ignored whole with the validator message in the warning; editing the file (newer mtime) is picked up on the next call; no `folder_paths` → no override, no warnings; `get_families` route JSON includes `warnings`.
- [ ] **Step 2: Run to verify failure.**
- [ ] **Step 3: Implement** `override.py` and wire `families.py`/`node.py`. `current_table()` caches on `(path, mtime_ns)`.
- [ ] **Step 4: Run** the picker tests, full suite with coverage, black, flake8.
- [ ] **Step 5: Commit** — `feat(model_resolution_picker): merge a user override file into the family table`.

### Task 13: Native `resolution` dropdown synced with the panel

**Files:**
- Modify: `node.py` (input, `VALIDATE_INPUTS`, execution precedence), `logic.py` (`size_label(w, h, ratio_label) -> str`, `parse_size_label(text) -> tuple[int, int] | None`), `web/ui/resolution-picker.js` (`sizeLabel`, `parseSizeLabel`, `dropdownOptions(payload, label, chip) -> string[]`), `web/model_resolution_picker.js` (rebuild options and sync value; dropdown callback writes size), `web/views/resolution-picker.js` (status shows the first payload warning), `tests/js/resolution-picker.test.mjs`, `tests/browser/workflows.spec.mjs`, `tests/comfyui/resolution-picker.spec.mjs` (five native widgets: `slice(5)`, include `resolution` in the round-trip), `tools/testing/frontend-coverage-baseline.json` if floors move
- Test: `test_node.py`, `test_logic.py`

**Interfaces:**
- Python: `INPUT_TYPES` adds `resolution` COMBO (`["custom"] + sorted distinct labels across shipped families`, default `custom`, tooltip "Sizes for the selected model and ratio; custom uses width/height") between `model` and `width`; `create(self, model, resolution, width, height, batch_size)`: when `resolution != "custom"` and `parse_size_label` succeeds, those dims replace `width`/`height` before rounding; `VALIDATE_INPUTS(cls, model, resolution) -> bool`.
- JS: `dropdownOptions` returns `['custom', ...labels]` for the active chip's sizes, or all family sizes when `chip` is null/custom; the extension sets `resolution.options.values` (array) on every render where model or active chip changed, sets `resolution.value` to the current size's label or `custom`, and wraps the `resolution` widget callback: a label value writes the parsed size through `width`/`height` callbacks (re-entrancy guarded), `custom` leaves sizes alone.
- Fixture host note: the fixture renders `resolution` as a text input; tests set its value and dispatch `change`.

- [ ] **Step 1: Write the failing tests** — Python: `test_resolution_label_overrides_width_height` (`create("SDXL", "1216×832 - 3:2 (1.0MP)", 1024, 1024, 1)` → `(1216, 832)`), `test_custom_uses_width_height`, `test_validate_inputs_accepts_unlisted_resolution`, `size_label(1216, 832, "3:2") == "1216×832 - 3:2 (1.0MP)"`, `parse_size_label("1216×832 - 3:2 (1.0MP)") == (1216, 832)` and `None` for `custom`/garbage. JS unit: `dropdownOptions(payload, 'SDXL', '3:2')` → `['custom', '1216×832 - 3:2 (1.0MP)']`; `dropdownOptions(payload, 'SDXL', null)` lists all five SDXL sizes with ratio labels; `parseSizeLabel` round-trips `sizeLabel`. Browser: creating the node with `resolution: 'custom'` and clicking `3:2` sets the `resolution` input to `1216×832 - 3:2 (1.0MP)`; setting `resolution` to `1344×768 - 16:9 (1.0MP)` and dispatching `change` writes width/height 1344/768 and activates `16:9`; a swap sets `resolution` to the mirrored label; a typed width of 1000 sets it to `custom`; with the families route fulfilled by a payload carrying `warnings: ['Override ignored: test']` the status line shows that text. Real host: the existing spec asserts `widgets_values.slice(5)` is empty and that `resolution` survives reload.
- [ ] **Step 2: Run to verify failure** (Python, JS unit, chromium focused).
- [ ] **Step 3: Implement** Python then JS. The option list is set as a plain array on `widget.options.values`; the sibling `dimensions.js` already reads array or function options.
- [ ] **Step 4: Run** Python suite with coverage, black/flake8, JS unit, chromium+touch browser suite (`env KIKO_TEST_PYTHON=…`), coverage gate, real host on both projects.
- [ ] **Step 5: Commit** — `feat(model_resolution_picker): add a resolution dropdown synced with the chip grid`.

### Task 14: Docs and final verification for the addendum

- [ ] Update `README.md` section bullets (dropdown; override file path and rules), `examples/documentation/model_resolution_picker.md` (JSON schema, override example with `remove` and a new family, warning behavior, dropdown precedence), `web/ui/README.md` (dropdown sync rule). Verify links.
- [ ] Run every suite as in Task 10 Step 1 (Python, black/flake8, JS unit, coverage gate, chromium+touch, real host). WebKit is a known local environment limitation.
- [ ] Commit — `docs(model_resolution_picker): document the JSON table, override file and resolution dropdown`.
