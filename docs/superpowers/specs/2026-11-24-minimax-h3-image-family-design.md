# MiniMax H3 Image family for the Model Resolution Picker

## Intent

People running MiniMax H3 Image in ComfyUI should be able to pick a native
H3 Image size from the Model Resolution Picker, the same way they do for Flux,
Qwen-Image or Krea 2. H3 Image needs both sides on a 32-pixel grid and is tuned
for 2048 × 2048 of area, so ordinary SDXL or Flux sizes are often wrong for it.

Source notes: `~/minimax-h3-image-resolution-and-latents.md` (MiniMax's output
size guide, the reference size helper in `examples/context_ir.py`, and
ComfyUI's `MiniMaxH3ImageConditioning`).

## Goals

- A new image-group family, **MiniMax H3 Image**, in
  `kikotools/tools/model_resolution_picker/families.json`.
- Sizes for every picker chip at three tiers, 1K, 2K and 4K, all on the
  32-pixel grid.
- Default 2048 × 2048, the area the model is tuned for.

## Non-goals

- Empty Latent Batch and Width/Height Selector are unchanged (approach 3 below).
- The existing **MiniMax H3 (keyframes)** video row stays as it is. It serves the
  H3 video model, which is a separate model.
- No new latent shape. The picker keeps emitting its empty 4-channel latent;
  ComfyUI's sampler (`fix_empty_latent_channels`) widens an empty latent to
  H3's 24 channels and 16x downscale and adds the frame axis.
- No hosted-API sizing (exact sizes off the grid, 20 MP cap). This is a local
  ComfyUI picker.

## Anti-goals

- Any size with a side that is not a multiple of 32. ComfyUI's H3 Image
  conditioning steps its width and height inputs by 32.
- Changing sizes or labels of existing families, which would shift saved
  workflows.

## Approaches

1. Add H3 Image presets to the shared Width/Height Selector preset list, so
   Empty Latent Batch gets them too. Small, but the size-keyed list collides on
   1024 × 1024 and 2048 × 2048 and grows the shared dropdown by about 30 entries.
2. Give Empty Latent Batch a model dropdown fed by the picker's families. One
   source of truth, but a redesign of a node in saved workflows that duplicates
   the picker.
3. **Picker only (chosen).** The picker already outputs a batched empty latent
   at the chosen size, so it covers H3 Image by itself. Cheapest, and no change
   to nodes people already use.

## Decided

- Family: label `MiniMax H3 Image`, group `image`, `vaeRatio` 16, `step` 32,
  `megapixels` [1.0, 4.0, 16.0] (1024², 2048², 4096²), `default` [2048, 2048].
  Placed after HunyuanImage 2.1, the last image family.
- Sizes come from MiniMax's reference formula, per chip `x:y` and tier area A:
  `w = 32 × round(sqrt(A × x / y) / 32)`, `h = 32 × round(sqrt(A × y / x) / 32)`.
  At 2K and 4K this reproduces MiniMax's published output table exactly.
- Keep a 1K tier as a fast preview tier. MiniMax's hosted 1K sizes 1152 × 912,
  1184 × 880 and 1360 × 768 are off the grid; the formula gives 1152 × 928,
  1184 × 896 and 1376 × 768 instead.

| Chip | 1K | 2K | 4K |
|---|---|---|---|
| 1:1 | 1024 × 1024 | 2048 × 2048 | 4096 × 4096 |
| 5:4 | 1152 × 928 | 2304 × 1824 | 4576 × 3648 |
| 4:3 | 1184 × 896 | 2368 × 1760 | 4736 × 3552 |
| 3:2 | 1248 × 832 | 2496 × 1664 | 5024 × 3360 |
| 16:9 | 1376 × 768 | 2720 × 1536 | 5472 × 3072 |
| 21:9 | 1568 × 672 | 3136 × 1344 | 6272 × 2688 |

Portrait chips (4:5, 3:4, 2:3, 9:16, 9:21) are the same sizes swapped.

- Notes text for the family says where the sizes come from and that 1K is
  rounded onto the 32 grid.

## Left to the builder

- Tests, following the existing family tests: every H3 Image size is a multiple
  of 32, the table above is what ships, the default is 2048 × 2048, and a
  picked H3 size passes through `create` unrounded. Plus a check that the
  picker's latent for a 4K pick widens to `[1, 24, 1, 256, 256]` (4096²) and
  `[1, 24, 1, 192, 342]` (5472 × 3072) through ComfyUI's
  `fix_empty_latent_channels` logic, if that can be exercised without model
  weights; otherwise assert the 4-channel shape and `downscale_ratio_spacial` 8.
- README picker family list, the picker's documentation table, and a CHANGELOG
  `## Unreleased` entry.
- Whether the picker's frontend needs a test update for the new family count.
