# Kiko Purge VRAM: safe unload and fail loudly

## Intent

A live H3 run with Kiko Purge VRAM placed twice per workflow (after conditioning,
and between the sampler and VAE Decode) broke ComfyUI. The purge's call to
`comfy.model_management.unload_all_models()` raised "list index out of range";
our node caught it and carried on; VAE Decode then failed with "'NoneType' object
is not callable"; and the same error killed ComfyUI's prompt worker at the start
of the next job, which hung with the GPU idle. Make the purge unable to leave
ComfyUI in that state, and stop hiding the failure.

## What happened (from the ComfyUI source and log)

- `free_memory` (called by `unload_all_models`) records list positions of
  `current_loaded_models`, unloads each, and pops the unloaded entries only at the
  end. `LoadedModel.model_unload()` sets the entry's `real_model` to `None`.
- Unloading one model can drop the last reference to another model's weights,
  which fires that entry's `weakref.finalize(..., cleanup_models)`. `cleanup_models`
  pops dead entries from the same list mid-loop, so a recorded position points
  past the end: "list index out of range". This trigger is the only path
  that shrinks the list inside that loop. The IndexError and the follow-on
  TypeError reproduce on CPU with the installed ComfyUI's real
  `LoadedModel`/`ModelPatcher` classes (an ON_DETACH callback dropping the last
  reference to other models). The drain-then-delegate unload leaves the list empty
  and `cleanup_models_gc()` clean.
- The entries already unloaded keep `real_model = None` and are never removed.
  `cleanup_models_gc` (run by every `load_models_gpu`, and by `execution.py` at the
  start of each prompt, outside any node's error handling) calls
  `cur.real_model()` on them: "'NoneType' object is not callable". That kills the
  worker thread on the next prompt.
- Failing our node's job alone would not help: the broken entries outlive the job.

## Goals

1. **Safe unload.** The `models` step first drains the list, then calls
   `unload_all_models()` once so other packs' hooks on it still run. It iterates over a copy of `mm.current_loaded_models` and, for each entry still
   in the live list: an entry whose `real_model is None` (already unloaded) or
   whose `model is None` (patcher collected) is removed without unloading;
   otherwise call `entry.model_unload()` and then remove that entry from the live
   list by identity if it is still there. Removal by identity makes the loop immune
   to the list shrinking under it. Once the drain is done the list is empty (or holds
   only entries added meanwhile), so `unload_all_models()` has nothing to trip on. If `mm` has no `current_loaded_models` list
   (a ComfyUI that renamed it), fall back to `mm.unload_all_models()`.
2. **Repair on failure.** If any step raises, first remove from
   `mm.current_loaded_models` every entry whose `real_model is None`, so the next
   `cleanup_models_gc` cannot crash.
3. **Fail the job.** After repairing, log the full traceback with
   `logger.exception` and raise `RuntimeError` from the original error, with a
   message saying the purge failed, that ComfyUI's model list was repaired, and the
   original error text. The run stops at the purge node instead of in VAE Decode.
   This replaces the current behaviour of reporting the error and passing the
   input through.

## Non-goals

- Fixing ComfyUI's `free_memory` or `is_dead`. They are upstream; an upstream
  issue is worth filing separately with this analysis.
- Changing modes, threshold, switches, legacy names or the report format.

## Constraints

- Touch only `kikotools/tools/kiko_purge_vram/` (logic, node), its tests, README
  and CHANGELOG.
- Own implementation; no source copied from other packs.
- Docs: drop the "a failing step is logged and shown, the input passes through"
  wording; say a failing step stops the run with an error after repairing
  ComfyUI's model list, and that the `models` step unloads entries one at a time
  instead of calling `unload_all_models()` (a deliberate difference from Free VRAM
  Pixaroma, with the reason).

## Approaches

1. **Safe unload + repair + fail (chosen).** Prevents the crash path, repairs if
   anything else goes wrong, and makes the failure visible.
2. Fail the job only. Visible, but the broken entries still kill the worker on the
   next prompt.
3. Repair only and carry on. Keeps runs going, but hides that a purge failed.

## Left to the builder

- Helper names and where the repair lives (logic.py, next to `run_steps`).
- Tests with fake `LoadedModel` objects in a real list: one whose `model_unload`
  removes another entry (the finalizer case) must leave the list empty with no
  error; one whose `model_unload` raises after an earlier entry was unloaded must
  leave no `real_model is None` entry behind and raise `RuntimeError` through the
  node; an already-unloaded entry and a dead-patcher entry are removed without
  `model_unload` being called; no `current_loaded_models` falls back to
  `unload_all_models`.
