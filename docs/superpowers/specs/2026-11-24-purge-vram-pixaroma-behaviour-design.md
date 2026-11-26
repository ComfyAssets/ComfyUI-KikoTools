# Kiko Purge VRAM: match Free VRAM Pixaroma's behaviour

## Intent

Kiko Purge VRAM should free memory as reliably as Free VRAM Pixaroma
(`ComfyUI-Pixaroma/nodes/node_free_vram.py`). A review found ours the weakest of
three VRAM nodes: the default `soft` mode keeps every model loaded, cache
emptying calls CUDA directly so other cards get nothing, and the node always
forces everything downstream to re-run. Behaviour only: no new frontend.

## Goals

- Three modes, as Pixaroma names them: `all` (unload models, then hand the
  cache back), `models` (unload models only), `cache` (hand the cache back only,
  models stay loaded). Default `all`.
- Steps run in Pixaroma's order: `comfy.model_management.unload_all_models()`,
  then `gc.collect()` when enabled, then `comfy.model_management.soft_empty_cache(True)`.
  All cache emptying goes through ComfyUI, so MPS, XPU, NPU and MLU devices work.
- Unwired guard: with nothing wired into `anything`, the node does nothing and
  reports that. `anything` becomes optional so an unwired node is valid.
- Threshold measures free memory: skip when at least `memory_threshold_mb` MB is
  already free; `0` always runs. `all` and `models` read ComfyUI's free figure
  (`mm.get_free_memory`, which counts PyTorch's spare reserved blocks); `cache`
  reads the driver's free figure, because emptying the cache does not move
  ComfyUI's figure.
- `collect_garbage` switch (default on) and `every_run` switch (default on).
  `every_run` on makes `IS_CHANGED` return NaN; off returns a stable value built
  from the settings, so ComfyUI may cache the node and nothing downstream is
  forced to re-run.
- Passthrough output and the `memory_report` text output stay.

## Saved workflows (decided: approach 1)

- Widget values are saved by position: mode, report_memory, memory_threshold_mb.
  Those three keep their slots; `collect_garbage` and `every_run` are appended
  after them.
- Old mode names still load and run: `VALIDATE_INPUTS` accepts them and the node
  maps `soft` and `aggressive` to `all`, `models_only` to `models`, `cache_only`
  to `cache`. Any other mode value is rejected with a message naming the valid
  modes.
- A non-zero saved threshold flips meaning (used-MB trigger becomes free-MB
  skip). The CHANGELOG says so. `0`, the default, is unchanged.

## Credit (decided)

The modes, step order, unwired guard, free-memory threshold and every-run switch
are Pixaroma's design. Credit it in three places, with the same wording:

> Behaviour based on Free VRAM Pixaroma from
> [ComfyUI-Pixaroma](https://github.com/pixaroma/ComfyUI-Pixaroma) by Pixaroma.

- The README section for Kiko Purge VRAM, under its heading.
- The CHANGELOG entry.
- The node's `DESCRIPTION`, as a closing sentence without the link markup.

Write our own implementation; do not copy Pixaroma's source. Both projects are
MIT licensed, and copied code would have to carry Pixaroma's copyright notice.

## Non-goals

- Pixaroma's drawn memory bar, gear menu or node properties.
- Clearing ComfyUI's node result cache (only ComfyUI's own "Free model and node
  cache" does that, after a run).

## Approaches

1. **New modes, old names accepted, threshold flipped in place (chosen).** Old
   workflows load and run; a non-zero threshold flips meaning, noted in the
   changelog.
2. Keep the four old names and change what they do. No load risk, but `soft`
   would unload models, names would not match Pixaroma, and two names would do
   the same thing.
3. New threshold widget, old one kept as legacy. No meaning flips, but two
   thresholds on the node for good.

Display: behaviour only (option 1 of the earlier question); a memory bar like
Pixaroma's was declined.

## Left to the builder

- Report text: keep the current layout (mode, freed, before, after, time),
  measured in the mode's view; say "Nothing wired in" and "skipped" cases
  plainly. Name the legacy mode when one was mapped.
- Threshold max: raise from 48000 so cards above 48 GB can use it (my call:
  262144).
- Tests: replace the four-mode tests with tests for the three modes' step order
  (mock `comfy.model_management`), legacy mapping and rejection, the unwired
  guard, both threshold views, and both `every_run` settings.
- README section and table line, CHANGELOG `## Unreleased` entry, each with the credit above.
