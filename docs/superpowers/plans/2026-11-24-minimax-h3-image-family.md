# MiniMax H3 Image Family Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `MiniMax H3 Image` family to the Model Resolution Picker with 1K, 2K and 4K sizes on the 32-pixel grid.

**Architecture:** Data-only change to `families.json`, which the picker's Python node and frontend both read. No code changes. Tests pin the shipped sizes and the node's rounding for this family; docs list the new family.

**Tech Stack:** Python 3.10+, pytest, ComfyUI custom node, JSON family table.

**Spec:** `docs/superpowers/specs/2026-11-24-minimax-h3-image-family-design.md`

## Global Constraints

- Label `MiniMax H3 Image`, group `image`, `vaeRatio` 16, `step` 32, `megapixels` [1.0, 4.0, 16.0], `default` [2048, 2048], `aliases` [].
- Every size is a multiple of 32 on both sides.
- Placed after `HunyuanImage 2.1` and before `Wan 2.2 (keyframes)` in `families`.
- No change to any other family, to Empty Latent Batch, Width/Height Selector, or `MiniMax H3 (keyframes)`.
- Commits: conventional `type(scope): subject` with a bullet body. No AI or Claude attribution of any kind in commits or PR text. Stage only the named files.
- Push with an explicit refspec (`git push origin <branch>:<branch>`); this repo has `push.default=matching`.

## Review Focus

- A custom size off the grid, such as MiniMax's hosted 1360 × 768, must round to 1376 × 768 under this family, not pass through. Pinned in Task 1.
- The widest 4K pick, 6272 × 2688, must pass through `create` unrounded and stay under the node's 8192 side limit. Pinned in Task 1.
- The 4K latent must be the picker's usual 4-channel 8x latent, `[1, 4, 384, 684]` for 5472 × 3072 with `downscale_ratio_spacial` 8, which ComfyUI widens to `[1, 24, 1, 192, 342]` when sampling. Pinned in Task 1.
- The family's labels must not collide with the keyframes row in the model dropdown. Covered by the existing unique-label test.
- Shared size labels such as `2048×2048 - 1:1 (4.0MP)` already exist in the `resolution` dropdown; picking one under H3 Image must give 2048 × 2048. Pinned in Task 1.

---

### Task 1: Ship the family

**Files:**
- Modify: `kikotools/tools/model_resolution_picker/families.json` (new entry after `HunyuanImage 2.1`)
- Test: `tests/unit/tools/model_resolution_picker/test_families.py`
- Test: `tests/unit/tools/model_resolution_picker/test_node.py`

**Interfaces:**
- Consumes: `resolve_family(label)`, `FAMILIES`, `family_labels()` from `families.py`; `ModelResolutionPickerNode().create(model, resolution, width, height, batch_size) -> (latent, width, height)`; `generate_size(ratio_w, ratio_h, megapixels, step)` from `logic.py`.
- Produces: family label `MiniMax H3 Image` for Task 2's docs.

- [ ] **Step 1: Write the failing tests**

In `test_families.py`, add to the `must` dict in `test_defaults_labels_and_must_includes`:

```python
"MiniMax H3 Image": [(2048, 2048), (1376, 768), (5472, 3072), (6272, 2688)],
```

and add:

```python
H3_IMAGE = {
    "1:1": [(1024, 1024), (2048, 2048), (4096, 4096)],
    "5:4": [(1152, 928), (2304, 1824), (4576, 3648)],
    "4:3": [(1184, 896), (2368, 1760), (4736, 3552)],
    "3:2": [(1248, 832), (2496, 1664), (5024, 3360)],
    "16:9": [(1376, 768), (2720, 1536), (5472, 3072)],
    "21:9": [(1568, 672), (3136, 1344), (6272, 2688)],
}


def test_minimax_h3_image_ships_the_reference_table():
    family = resolve_family("MiniMax H3 Image")
    assert (family.group, family.vae_ratio, family.step) == ("image", 16, 32)
    assert tuple(family.megapixels) == (1.0, 4.0, 16.0)
    assert tuple(family.default) == (2048, 2048)
    expected = dict(H3_IMAGE)
    for chip, sizes in H3_IMAGE.items():
        expected[MIRROR[chip]] = [(h, w) for w, h in sizes]
    assert {c: [tuple(s) for s in e] for c, e in family.sizes.items()} == expected


def test_minimax_h3_image_sits_after_hunyuan_image():
    labels = family_labels()
    assert labels.index("MiniMax H3 Image") == labels.index("HunyuanImage 2.1") + 1
```


In `test_node.py`, add:

```python
def test_h3_image_rounds_custom_sizes_to_32():
    _, w, h = ModelResolutionPickerNode().create("MiniMax H3 Image", "custom", 1360, 768, 1)
    assert (w, h) == (1376, 768)


def test_h3_image_listed_sizes_pass_through():
    node = ModelResolutionPickerNode()
    assert node.create("MiniMax H3 Image", "custom", 6272, 2688, 1)[1:] == (6272, 2688)
    assert node.create("MiniMax H3 Image", "2048×2048 - 1:1 (4.0MP)", 1024, 1024, 1)[1:] == (2048, 2048)


def test_h3_image_4k_latent_is_the_usual_empty_latent():
    latent, w, h = ModelResolutionPickerNode().create("MiniMax H3 Image", "custom", 5472, 3072, 2)
    assert tuple(latent["samples"].shape) == (2, 4, 384, 684)
    assert latent["downscale_ratio_spacial"] == 8
```

Use the exact `resolution` label format the dropdown emits; if `2048×2048 - 1:1 (4.0MP)` is not in `INPUT_TYPES()["required"]["resolution"][0]` after Step 3, take the 2048 × 2048 label from that list.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$V/bin/python -m pytest tests/unit/tools/model_resolution_picker -p no:cacheprovider -q`
Expected: FAIL on the new tests (`resolve_family("MiniMax H3 Image")` is `None`). `$V` is a scratch venv per the test-env notes (uv, Python 3.12, CPU torch, pytest, pytest-cov, pytest-mock, pytest-asyncio, numpy, pillow, aiohttp, black, flake8).

- [ ] **Step 3: Add the family to `families.json`**

Build `sizes` with `generate_size(x, y, mp, 32)` for every chip in `CHIPS` and `mp` in (1.0, 4.0, 16.0), each chip's list sorted by area; this reproduces the table above exactly (checked: 0 mismatches against MiniMax's formula). Write the result into the JSON by hand or with a one-off script that is not committed. Keep the file's existing indentation.

- `models`: `"MiniMax H3 Image"`
- `notes`: `"MiniMax reference size formula (examples/context_ir.py) at 1K, 2K and 4K areas, step 32. 2K and 4K match MiniMax's published output table; 1K is rounded onto the 32 grid."`

- [ ] **Step 4: Run the picker tests, then the full suite**

Run: `$V/bin/python -m pytest tests -p no:cacheprovider -q --cov=kikotools`
Expected: all pass, coverage at or above 85%.

Run: `env npm test --prefix tools/testing`
Expected: `# fail 0`.

- [ ] **Step 5: Commit**

```bash
git add kikotools/tools/model_resolution_picker/families.json tests/unit/tools/model_resolution_picker/test_families.py tests/unit/tools/model_resolution_picker/test_node.py
git commit -m "feat(model_resolution_picker): add a MiniMax H3 Image family

- Image family on the 32 px grid (16x VAE, 2x2 patch) with 1K, 2K and 4K
  tiers from MiniMax's reference size formula; 2K and 4K match the published
  output table, 1K is rounded onto the grid.
- Defaults to 2048x2048, the area the model is tuned for."
```

### Task 2: Document the family

**Files:**
- Modify: `examples/documentation/model_resolution_picker.md` (family table, after the `HunyuanImage 2.1` row)
- Modify: `README.md:230`
- Modify: `CHANGELOG.md` (new `## Unreleased` above `## 1.8.0`)

**Interfaces:**
- Consumes: the family from Task 1.

- [ ] **Step 1: Add the documentation table row**

```markdown
| MiniMax H3 Image | MiniMax H3 Image | 16x | 32 | 1.0, 4.0, 16.0 | 2048×2048 | image |
```

- [ ] **Step 2: Update the README family count**

Line 230: `14 shipped families` becomes `16 shipped families`, and add `MiniMax H3 Image` to the parenthetical list. Verify the count with `len(FAMILIES)` before writing it.

- [ ] **Step 3: Add the changelog entry**

```markdown
## Unreleased

### Model Resolution Picker

- New `MiniMax H3 Image` family: 16x VAE, step 32, 1K / 2K / 4K tiers from
  MiniMax's reference size formula, defaulting to 2048×2048. The 2K and 4K sizes
  match MiniMax's published table; 1K sizes are rounded onto the 32 grid.
  The `MiniMax H3 (keyframes)` row for the H3 video model is unchanged.
```

- [ ] **Step 4: Check formatting**

Run: `$V/bin/black --check .` and `$V/bin/python -m pytest tests/unit/tools/model_resolution_picker -p no:cacheprovider -q`
Expected: clean, all pass.

- [ ] **Step 5: Commit**

```bash
git add examples/documentation/model_resolution_picker.md README.md CHANGELOG.md
git commit -m "docs(model_resolution_picker): list the MiniMax H3 Image family

- Family table row, README family count and an Unreleased changelog entry."
```
