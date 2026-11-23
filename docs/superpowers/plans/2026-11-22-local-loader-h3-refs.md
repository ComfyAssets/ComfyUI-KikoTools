# Local Image Loader: H3 RefMod refs output

## Goal

Let the Local Image Loader pick several photos, in order, and feed them
straight into the `refs_bundle` input of **Create H3 RefMod**
(ComfyUI-MiniMaxH3Mod), already matched to one size.

## Background (verified in ComfyUI-MiniMaxH3Mod)

- `refs_bundle` takes `H3_REF_LIST`: a plain Python list of IMAGE tensors,
  `[1, H, W, 3]` float32 0-1 per photo (`common.load_image_file`).
- In Full Reference (`encode`) mode, Create H3 RefMod stacks every ref into one
  latent. The **first** ref sets the canvas and every other ref is scaled to
  cover it and center-cropped (`nodes.py` ~1854, `common.resize_ref`). Mixed
  sizes never error, they are silently cropped.
- The type name is only a string; KikoTools gains no dependency on the pack.

## Decisions (agreed with Vito)

- **Crop to first:** the first picked photo keeps its own size and becomes the
  canvas. Every other photo is scaled to cover the canvas (bicubic, antialiased) and
  center-cropped, which is the same rule H3 applies. H3's own resize then only
  scales uniformly and crops nothing more. No new widget.
- **Preview output:** the size-matched photos also come out as one IMAGE batch.

## Behaviour

Outputs, appended after the existing three so saved workflows keep their links:

| # | Name | Type | Content |
|---|---|---|---|
| 3 | `refs` | `H3_REF_LIST` | list of `[1, H, W, 3]` tensors, pick order, all canvas-sized |
| 4 | `refs_preview` | `IMAGE` | the same photos as one `[N, H, W, 3]` batch |

- Nothing picked: `refs` is an empty list (H3 then raises its own "connect at
  least one image" error) and `refs_preview` is the existing empty tensor.
- Photos load with EXIF orientation applied and are converted to RGB (alpha
  dropped), so what you see in the gallery is what gets encoded.
- Images only (png/jpg/jpeg/webp/bmp/gif). Videos and audio are not refs here.
- At most 256 refs (H3's bundle limit).
- A picked file that is gone or no longer allowed is skipped with a warning; the
  order of the remaining refs is kept.

## Gallery UI

- **Ctrl/Cmd-click** an image toggles it in the refs list. Each picked tile shows
  its position (1, 2, 3...) as a badge; removing one renumbers the rest.
- A plain click keeps today's behaviour (the single `image` output).
- A small bar shows `Refs: N` with a **Clear refs** button.
- Picks are saved per node via a new route and also kept in
  `node.properties.kiko_refs`, so they survive reloading the workflow; on load
  the node re-sends them to the server.

## Tasks

### Task 1: Size matching (logic.py, pure function + tests)

`match_refs_to_first(images: list[tensor]) -> list[tensor]`, plus
`load_ref_image(path) -> [1, H, W, 3]` (EXIF transpose, RGB). Tests: same
sizes untouched; wider and taller photos cover-cropped to the canvas; one
photo; empty list; rounding never yields a 0 or off-by-one dimension.

### Task 2: Backend route + node outputs (node.py + tests)

`POST /kiko_local_image_loader/set_node_refs` with `{node_id, paths: [...]}`:
rejects non-lists, more than 256 items, non-image or disallowed paths (same
checks as `set_node_selection`); an empty list clears. Stored as
`selections[node_id]["refs"] = {"paths": [...]}`. Add the two outputs and
build them in `load_media`. Tests cover the route's validation, the output
order and shapes, and skipping a missing or disallowed file.

### Task 3: Gallery multi-select (web/kiko_local_image_loader.js + JS tests)

Ctrl/Cmd-click toggling, order badges, the `Refs: N` bar with Clear,
`node.properties.kiko_refs` persistence and re-sync on load. Keep the
frontend coverage baseline green (update the baseline entry only if the
numbers legitimately move).

### Task 4: Docs

README Local Image Loader section (refs outputs, Ctrl-click, the
crop rule), CHANGELOG entry under Unreleased, output tooltips.

### Task 5: Verify live

Run `venv/bin/python -m pytest tests/unit` and the JS tests.
Then check in the running ComfyUI: pick 3 photos of different shapes, wire
`refs` to Create H3 RefMod and `refs_preview` to Preview Image, and confirm
the preview crops and the H3 log line `source (1, H, W, 3)` agree.

## Out of scope

Videos as refs, per-photo crop positions, a resolution widget, reading or
writing `.safetensors` RefMod bundles.
