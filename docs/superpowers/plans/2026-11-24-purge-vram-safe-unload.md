# Kiko Purge VRAM Safe Unload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Kiko Purge VRAM's model unload immune to ComfyUI's loaded-model list shrinking mid-loop, repair that list after any failed step, and fail the job instead of carrying on.

**Architecture:** Two helpers in `logic.py` replace the `unload_all_models()` call and repair the list; `node.py` turns a failed step into a repaired list plus a raised `RuntimeError`. Docs follow.

**Tech Stack:** Python 3.10+, pytest with `unittest.mock`, ComfyUI `comfy.model_management`.

**Spec:** `docs/superpowers/specs/2026-11-24-purge-vram-safe-unload-design.md`

## Global Constraints

- Touch only `kikotools/tools/kiko_purge_vram/logic.py`, `node.py`, `tests/unit/tools/test_kiko_purge_vram.py`, `README.md`, `CHANGELOG.md`.
- Modes, threshold, switches, legacy names, IS_CHANGED, VALIDATE_INPUTS and the success/skip/unwired report text are unchanged.
- ComfyUI facts: `mm.current_loaded_models` is a plain `list` of `LoadedModel`; `LoadedModel.real_model` is `None` until loaded and again after `model_unload()`, otherwise a weakref; `LoadedModel.model` is a property returning the `ModelPatcher` or `None` once it is collected; `LoadedModel.model_unload()` takes no required arguments.
- Own implementation; no source copied from other packs.
- Commits: conventional `type(scope): subject` with a bullet body; stage only named files; no AI or Claude attribution of any kind. Push with an explicit refspec.

## Review Focus

- The finalizer case: an entry's `model_unload()` removes a different entry from `current_loaded_models`; the loop must finish without `IndexError` and leave the list empty. Pinned in Task 1.
- A half-unloaded entry (`real_model is None`) left by any failure must be gone before the node raises, or the next prompt's leak check kills ComfyUI's worker. Pinned in Task 1 and Task 2.
- A real error must still surface: the node raises, not returns, and the traceback is logged. Pinned in Task 2.
- A ComfyUI without a `current_loaded_models` list (or a test `MagicMock`) must fall back to `mm.unload_all_models()`, so the existing step-order tests keep passing. Pinned in Task 1.
- An entry removed from the live list by someone else during the loop must not be unloaded or removed twice. Pinned in Task 1.

---

### Task 1: Safe unload and repair helpers

**Files:**
- Modify: `kikotools/tools/kiko_purge_vram/logic.py`
- Test: `tests/unit/tools/test_kiko_purge_vram.py`

**Interfaces:**
- Produces, in `logic.py`:
  - `unload_models_safely() -> None` — if `getattr(mm, "current_loaded_models", None)` is not a `list`, call `mm.unload_all_models()` and return. Otherwise, for each entry in `list(loaded)`: skip it if it is no longer in `loaded` (compare by identity); if `entry.real_model is None` or `entry.model is None`, remove it without unloading; else call `entry.model_unload()` and then remove it by identity if still present.
  - `repair_loaded_models() -> int` — remove every entry of `mm.current_loaded_models` whose `real_model is None`; return how many were removed; return `0` when the list is missing or not a `list`.
  - `run_steps` calls `unload_models_safely()` for the `models` step instead of `mm.unload_all_models()`; order and the other steps unchanged.
- Consumes: nothing new.

- [ ] **Step 1: Write the failing tests**

Use a small fake in the test file:

```python
class FakeLoaded:
    def __init__(self, name, loaded=True, patcher=True, on_unload=None):
        self.name = name
        self.real_model = (lambda: object()) if loaded else None
        self.model = object() if patcher else None
        self.on_unload = on_unload
        self.unload_calls = 0

    def model_unload(self):
        self.unload_calls += 1
        self.real_model = None
        if self.on_unload:
            self.on_unload()
```

Give `fresh_mm` (or a new fixture) a real list: `logic_module.mm.current_loaded_models = [...]`. Tests:

- `test_unload_models_safely_unloads_and_removes_all`: three loaded entries → each `unload_calls == 1`, list is `[]`, `mm.unload_all_models` not called.
- `test_unload_survives_list_shrinking_mid_loop`: entries `a, b, c`; `a.on_unload` removes `c` from the live list (the finalizer case) → no exception, list `[]`, `a` and `b` unloaded once, `c.unload_calls == 0`.
- `test_unload_skips_entries_already_unloaded_or_dead`: `FakeLoaded("x", loaded=False)` and `FakeLoaded("y", patcher=False)` → both removed, neither `model_unload` called.
- `test_unload_falls_back_without_a_list`: `mm.current_loaded_models` left as a `MagicMock` attribute → `mm.unload_all_models` called once.
- `test_repair_removes_half_unloaded_entries`: list `[loaded, FakeLoaded("h", loaded=False), loaded2]` → returns `1`, the two loaded entries remain in order.
- `test_repair_without_a_list_returns_zero`: `MagicMock` attribute → `0`.
- Keep the existing `run_steps` order tests passing unchanged (they rely on the fallback).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$V/bin/python -m pytest tests/unit/tools/test_kiko_purge_vram.py -p no:cacheprovider -q`
Expected: FAIL on import of `unload_models_safely` / `repair_loaded_models`. `$V` is the scratch venv (uv, Python 3.12, CPU torch, pytest, pytest-cov, black, flake8).

- [ ] **Step 3: Implement the helpers and switch `run_steps` to `unload_models_safely()`**

Identity checks (`any(e is entry for e in loaded)`) rather than `in`, because `LoadedModel.__eq__` compares patchers and two entries can be equal.

- [ ] **Step 4: Run the tests**

Run: `$V/bin/python -m pytest tests/unit/tools/test_kiko_purge_vram.py -p no:cacheprovider -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add kikotools/tools/kiko_purge_vram/logic.py tests/unit/tools/test_kiko_purge_vram.py
git commit -m "fix(kiko_purge_vram): unload loaded models one at a time

- Iterate a copy of ComfyUI's loaded-model list and remove each entry by
  identity, so the list shrinking mid-loop cannot raise IndexError.
- Add a repair helper that drops half-unloaded entries (real_model None)."
```

### Task 2: Fail the job after repairing, and document it

**Files:**
- Modify: `kikotools/tools/kiko_purge_vram/node.py` (the `except Exception` around `run_steps`)
- Modify: `README.md` (Kiko Purge VRAM section), `CHANGELOG.md` (`## Unreleased` → `### Kiko Purge VRAM`)
- Test: `tests/unit/tools/test_kiko_purge_vram.py`

**Interfaces:**
- Consumes: `repair_loaded_models() -> int` from Task 1.
- Produces: `purge_vram` raises `RuntimeError` when a step fails.

- [ ] **Step 1: Write the failing tests**

Replace the tests that expect `Could not free memory` in a returned report (with report on and off) with:

- `test_step_error_repairs_and_raises`: `mm.current_loaded_models = [FakeLoaded("a"), FakeLoaded("b")]`, `a.on_unload` raises `RuntimeError("boom")` after setting its `real_model` to `None` (the fake already does that first) → `purge_vram("all", True, anything=1)` raises `RuntimeError` whose message contains `"Kiko Purge VRAM could not free memory"`, `"boom"` and `"repaired"`; afterwards no entry in the list has `real_model is None`; `__cause__` is the original error.
- `test_step_error_logs_traceback`: same setup with `caplog` at ERROR → one record from the node's logger with `exc_info` set.
- `test_step_error_raises_with_report_off`: `report_memory=False` → still raises.
- Keep every other node test passing unchanged.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$V/bin/python -m pytest tests/unit/tools/test_kiko_purge_vram.py -p no:cacheprovider -q`
Expected: the three new tests FAIL (the node returns instead of raising).

- [ ] **Step 3: Implement**

In the `except Exception as exc` branch: `removed = repair_loaded_models()`, then `logger.exception("Kiko Purge VRAM: purge failed")`, then `raise RuntimeError(...) from exc`. Message, verbatim apart from the two values: `Kiko Purge VRAM could not free memory: <exc>. ComfyUI's loaded-model list was repaired (<removed> half-unloaded entries removed) so later jobs keep working.` Remove the now-unused error-line path from the report builder.

Docs, in the existing style:
- README: replace "a failing step is logged and shown in the report" wording with: a failing step stops the run with an error, after the node repairs ComfyUI's loaded-model list so later jobs keep working. Under the step order, say the `models` step unloads loaded models one at a time rather than calling ComfyUI's `unload_all_models()`, because that call can fail when one unload frees another model mid-loop and leave ComfyUI unable to start the next job. Note this is a deliberate difference from Free VRAM Pixaroma.
- CHANGELOG `### Kiko Purge VRAM` under `## Unreleased`: replace the "failing step is logged and shown" bullet with the same two points in one or two bullets.

- [ ] **Step 4: Run the full checks**

Run: `$V/bin/python -m pytest tests -p no:cacheprovider -q --cov=kikotools` (pass, coverage ≥ 85%), `$V/bin/black --check .`, `$V/bin/flake8 kikotools/tools/kiko_purge_vram tests/unit/tools/test_kiko_purge_vram.py` (only the two pre-existing E402).

- [ ] **Step 5: Commit**

```bash
git add kikotools/tools/kiko_purge_vram/node.py tests/unit/tools/test_kiko_purge_vram.py README.md CHANGELOG.md
git commit -m "fix(kiko_purge_vram): fail the job after repairing ComfyUI's model list

- A failing step removes half-unloaded entries, logs the traceback and raises,
  so the run stops at the purge node and later jobs keep working.
- README and CHANGELOG describe the one-at-a-time unload and the new failure."
```
