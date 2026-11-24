# Kiko Purge VRAM: Pixaroma Behaviour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Kiko Purge VRAM free memory the way Free VRAM Pixaroma does: three modes in a fixed step order through ComfyUI's helpers, an unwired guard, a free-memory threshold, and garbage-collection and every-run switches.

**Architecture:** `logic.py` becomes small pure helpers plus one function that runs the steps through `comfy.model_management`; `node.py` keeps the class name and wires widgets, validation, caching and the report. No frontend.

**Tech Stack:** Python 3.10+, pytest with `unittest.mock`, ComfyUI V1 node API.

**Spec:** `docs/superpowers/specs/2026-11-24-purge-vram-pixaroma-behaviour-design.md`

## Global Constraints

- Node id `KikoPurgeVRAM`, display name `Kiko Purge VRAM`, category `🫶 ComfyAssets/🛠️ Utils`, `OUTPUT_NODE = True`, outputs `(any_type, "STRING")` named `("passthrough", "memory_report")` — unchanged.
- Modes `all`, `models`, `cache`; default `all`. Legacy map: `soft`→`all`, `aggressive`→`all`, `models_only`→`models`, `cache_only`→`cache`.
- Step order: `mm.unload_all_models()`, then `gc.collect()` when `collect_garbage`, then `mm.soft_empty_cache(True)`. `all` = models + cache; `models` = models only; `cache` = cache only. All cache emptying goes through `mm`; no direct `torch.cuda.*` calls.
- Widget order (saved by position): `mode`, `report_memory`, `memory_threshold_mb`, then the new `collect_garbage`, `every_run`.
- `memory_threshold_mb`: skip when free MB ≥ threshold; `0` always runs; INT default 0, min 0, max 262144, step 100.
- `all`/`models` read ComfyUI's free figure `mm.get_free_memory(dev)`; `cache` reads the driver's free figure `free_total - free_torch` from `mm.get_free_memory(dev, torch_free_too=True)`; total from `mm.get_total_memory(dev)`; `dev = mm.get_torch_device()`.
- Credit text, verbatim: `Behaviour based on Free VRAM Pixaroma from [ComfyUI-Pixaroma](https://github.com/pixaroma/ComfyUI-Pixaroma) by Pixaroma.` In `DESCRIPTION` without the link markup: `Behaviour based on Free VRAM Pixaroma from ComfyUI-Pixaroma by Pixaroma.`
- Own implementation only: do not copy source from ComfyUI-Pixaroma.
- Commits: conventional `type(scope): subject` with a bullet body; stage only named files; no AI or Claude attribution of any kind (no Co-Authored-By, no Claude-Session trailer, no claude.ai links). Push with an explicit refspec.

## Review Focus

- An old workflow saved with `mode` `soft` must validate and run as `all`, and the report must say it was mapped. Pinned in Task 2.
- An unknown mode string such as `turbo` must fail validation with a message naming the three modes, not run. Pinned in Task 2.
- A wired input that is falsy (`0`, `""`, `False`) is still wired; only `None` is "nothing wired in". Pinned in Task 2.
- When memory cannot be read (no `comfy`, or `mm` raises), a set threshold must not skip the purge; the node runs and the report says the figures were unavailable. Pinned in Task 1 and Task 2.
- When a step raises (for example `unload_all_models`), the node must still pass its input through and report the error instead of failing the prompt. Pinned in Task 2.

---

### Task 1: Rewrite the purge helpers

**Files:**
- Modify: `kikotools/tools/kiko_purge_vram/logic.py` (replace its contents)
- Test: `tests/unit/tools/test_kiko_purge_vram.py` (replace the `TestMemoryStats` and `TestMemoryPurge` classes and the report tests; keep the module's `comfy` mocking header)

**Interfaces:**
- Produces, all in `logic.py`:
  - `MODES: Tuple[str, ...] = ("all", "models", "cache")`
  - `LEGACY_MODES: Dict[str, str]` — the legacy map above
  - `resolve_mode(mode: str) -> Tuple[str, Optional[str]]` — `(new_mode, legacy_name_or_None)`; raises `ValueError` naming the three modes for anything else
  - `plan_steps(mode: str, collect_garbage: bool) -> Dict[str, bool]` — keys `"models"`, `"gc"`, `"cache"`; `mode` is already resolved
  - `memory_view(mode: str) -> str` — `"driver"` for `cache`, else `"comfy"`
  - `read_memory_mb(view: str) -> Optional[Tuple[float, float]]` — `(free_mb, total_mb)`, or `None` when `comfy` is missing or any `mm` call raises
  - `should_skip(threshold_mb: int, free_mb: Optional[float]) -> bool` — `True` only when `threshold_mb > 0`, `free_mb is not None` and `free_mb >= threshold_mb`
  - `run_steps(steps: Dict[str, bool]) -> None` — runs the true steps in the fixed order; with `comfy` missing, only `gc` runs

- [ ] **Step 1: Write the failing tests**

Patch `logic_module.mm` with a fresh `MagicMock` per test (attach a parent mock to check call order with `mock_calls`). Tests:

```python
def test_resolve_mode_new_and_legacy():
    assert resolve_mode("all") == ("all", None)
    assert resolve_mode("soft") == ("all", "soft")
    assert resolve_mode("aggressive") == ("all", "aggressive")
    assert resolve_mode("models_only") == ("models", "models_only")
    assert resolve_mode("cache_only") == ("cache", "cache_only")

def test_resolve_mode_rejects_unknown():
    with pytest.raises(ValueError, match="all, models, cache"):
        resolve_mode("turbo")

def test_plan_steps():
    assert plan_steps("all", True) == {"models": True, "gc": True, "cache": True}
    assert plan_steps("models", True) == {"models": True, "gc": True, "cache": False}
    assert plan_steps("cache", False) == {"models": False, "gc": False, "cache": True}

def test_memory_view():
    assert [memory_view(m) for m in MODES] == ["comfy", "comfy", "driver"]
```

- `test_run_steps_order_all`: with a parent mock holding `mm` and a patched `gc.collect`, `run_steps(plan_steps("all", True))` records `unload_all_models()`, then `collect()`, then `soft_empty_cache(True)`, in that order.
- `test_run_steps_models_skips_cache` and `test_run_steps_cache_skips_unload`: the other step is never called.
- `test_run_steps_without_comfy_only_collects`: with `logic_module.COMFY_AVAILABLE = False` (restore after), only `gc.collect` is called.
- `test_read_memory_comfy_view`: `mm.get_free_memory.return_value = 6 * 1024**3`, `mm.get_total_memory.return_value = 24 * 1024**3` → `(6144.0, 24576.0)`.
- `test_read_memory_driver_view`: `mm.get_free_memory.return_value = (8 * 1024**3, 2 * 1024**3)` when called with `torch_free_too=True` → free `6144.0`.
- `test_read_memory_returns_none_when_mm_raises`: `mm.get_torch_device.side_effect = RuntimeError` → `None`.
- `test_should_skip`: `(0, 9000.0)` False; `(4000, 9000.0)` True; `(4000, 4000.0)` True; `(4000, 3999.0)` False; `(4000, None)` False.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$V/bin/python -m pytest tests/unit/tools/test_kiko_purge_vram.py -p no:cacheprovider -q`
Expected: FAIL on import (`resolve_mode` and the other names do not exist). `$V` is the scratch venv (uv, Python 3.12, CPU torch, pytest, pytest-cov, pytest-mock, pytest-asyncio, numpy, pillow, aiohttp, black, flake8).

- [ ] **Step 3: Implement the helpers in `logic.py`**

Keep the module-level `try: import comfy.model_management as mm` with `COMFY_AVAILABLE`. Drop the `torch` import and the old `get_memory_stats`, `purge_memory`, `format_memory_report` and `should_purge`; only `node.py` and this test file use them. MB is `bytes / (1024 * 1024)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$V/bin/python -m pytest tests/unit/tools/test_kiko_purge_vram.py -p no:cacheprovider -q`
Expected: the new logic tests PASS. The old node tests in the same file may fail until Task 2; note which in the report.

- [ ] **Step 5: Commit**

```bash
git add kikotools/tools/kiko_purge_vram/logic.py tests/unit/tools/test_kiko_purge_vram.py
git commit -m "refactor(kiko_purge_vram): purge helpers in Pixaroma's step order

- all / models / cache modes with the legacy names mapped.
- Unload, collect, then empty the cache, all through comfy.model_management.
- Free-memory reads in ComfyUI's and the driver's view, and a free threshold."
```

### Task 2: Rewire the node

**Files:**
- Modify: `kikotools/tools/kiko_purge_vram/node.py`
- Test: `tests/unit/tools/test_kiko_purge_vram.py` (replace the node test class)

**Interfaces:**
- Consumes: everything Task 1 produces in `logic.py`.
- Produces: `KikoPurgeVRAM.INPUT_TYPES()`, `KikoPurgeVRAM.VALIDATE_INPUTS(cls, mode) -> Union[bool, str]`, `KikoPurgeVRAM.IS_CHANGED(cls, **kwargs) -> Union[float, str]`, `KikoPurgeVRAM().purge_vram(mode, report_memory, anything=None, memory_threshold_mb=0, collect_garbage=True, every_run=True) -> Tuple[Any, str]`.

- [ ] **Step 1: Write the failing tests**

Patch `logic_module.mm` (and `gc.collect`) per test. Tests:

- `test_input_types`: `list(required) == ["mode", "report_memory"]`; `required["mode"][0] == ["all", "models", "cache"]` with default `"all"`; `list(optional) == ["anything", "memory_threshold_mb", "collect_garbage", "every_run"]`; threshold `(default, min, max, step) == (0, 0, 262144, 100)`; both switches default `True`.
- `test_validate_inputs`: `VALIDATE_INPUTS("all") is True`; `VALIDATE_INPUTS("soft") is True`; `VALIDATE_INPUTS("turbo")` is a `str` containing `all, models, cache`.
- `test_is_changed`: `IS_CHANGED(every_run=True, mode="all")` is NaN; `IS_CHANGED(every_run=False, mode="all", memory_threshold_mb=0, collect_garbage=True)` equals itself on a second call and differs when `mode="cache"`; missing `every_run` is treated as `True`.
- `test_unwired_does_nothing`: `purge_vram("all", True)` returns `(None, report)` with `"Nothing wired in"` in the report and no `mm` call at all.
- `test_falsy_input_counts_as_wired`: `purge_vram("all", True, anything=0)` calls `unload_all_models` and returns `0` as passthrough.
- `test_all_mode_runs_and_reports`: `get_free_memory` returns 2 GiB then 10 GiB, total 24 GiB; report contains `"Mode: all"`, `"Memory Freed: 8192.0 MB"`, `"Before: 2048.0 MB free of 24576.0 MB"`, `"After: 10240.0 MB free of 24576.0 MB"`.
- `test_legacy_mode_is_mapped_and_named`: `purge_vram("soft", True, anything="x")` unloads models and the report contains `"Mode: all (from legacy 'soft')"`.
- `test_threshold_skips_when_enough_free`: free 9000 MB, threshold 4000 → no `unload_all_models`, report starts `"Memory purge skipped:"` and mentions `9000.0 MB free` and `4000 MB`.
- `test_threshold_runs_when_memory_unreadable`: `mm.get_torch_device.side_effect = RuntimeError`, threshold 4000 → `unload_all_models` is called and the report says `"Memory figures unavailable"`.
- `test_cache_mode_uses_driver_view`: `get_free_memory` with `torch_free_too=True` returns `(8 GiB, 2 GiB)` → threshold 7000 does not skip (driver free is 6144 MB).
- `test_step_error_is_reported_not_raised`: `mm.unload_all_models.side_effect = RuntimeError("boom")` → returns the input unchanged, report contains `"Could not free memory: boom"`.
- `test_report_off_returns_empty_string`: `report_memory=False` → second element `""`, steps still run.
- `test_description_credits_pixaroma`: `"Behaviour based on Free VRAM Pixaroma from ComfyUI-Pixaroma by Pixaroma." in KikoPurgeVRAM.DESCRIPTION`.
- Keep the existing category, `OUTPUT_NODE` and return-type assertions.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$V/bin/python -m pytest tests/unit/tools/test_kiko_purge_vram.py -p no:cacheprovider -q`
Expected: the new node tests FAIL (old inputs and signature).

- [ ] **Step 3: Implement the node in `node.py`**

- `VALIDATE_INPUTS` names only `mode`, so ComfyUI skips its dropdown check for `mode` and accepts legacy names; return the `ValueError` message from `resolve_mode` as the error string.
- `IS_CHANGED(cls, **kwargs)`: NaN when `kwargs.get("every_run", True)`; otherwise a string built from `mode`, `memory_threshold_mb` and `collect_garbage`.
- `purge_vram`: guard `anything is None` first; resolve the mode; read memory in the mode's view; skip on `should_skip`; run `run_steps` inside `try/except Exception` and report `Could not free memory: <message>`; read memory again; build the report. Report lines, in order: optional threshold line, `Mode: <mode>` (plus ` (from legacy '<name>')`), `Memory Freed: <after - before, floored at 0> MB`, `Before: <free> MB free of <total> MB`, `After: …`, `Time: <ms>ms`, all to one decimal. When memory is unreadable, replace the three figure lines with `Memory figures unavailable`. Return `(anything, report if report_memory else "")`.
- `DESCRIPTION`: one sentence on what the node does and its three modes, then the credit sentence from Global Constraints.
- Tooltips: mode (what each of the three does), threshold (skip when this many MB are already free, 0 always runs), `collect_garbage`, `every_run` (off lets ComfyUI cache the node so nodes after it do not re-run).

- [ ] **Step 4: Run the tests, then the full suite**

Run: `$V/bin/python -m pytest tests -p no:cacheprovider -q --cov=kikotools`
Expected: all pass, coverage ≥ 85%. Then `$V/bin/black --check .` and `$V/bin/flake8 kikotools/tools/kiko_purge_vram tests/unit/tools/test_kiko_purge_vram.py`: clean.

- [ ] **Step 5: Commit**

```bash
git add kikotools/tools/kiko_purge_vram/node.py tests/unit/tools/test_kiko_purge_vram.py
git commit -m "feat(kiko_purge_vram): free VRAM the way Free VRAM Pixaroma does

- all / models / cache modes; old mode names still validate and run.
- Nothing wired in does nothing; threshold skips when enough is free.
- collect_garbage and every_run switches; step errors are reported.
- Credit Pixaroma's design in the node description."
```

### Task 3: Document the change

**Files:**
- Modify: `README.md` (Kiko Purge VRAM table line and section)
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: the node from Task 2.

- [ ] **Step 1: Rewrite the README section**

Under `### 🧹 Kiko Purge VRAM`, put the credit line from Global Constraints (with the link), then: the three modes, the step order, nothing-wired behaviour, the free-memory threshold, the two switches, the passthrough and report outputs, and a note that old mode names still work. Replace the example output with one produced by the new report format. Update the table line's description to "Free GPU memory between workflow stages: unload models, return the cache, or both".

- [ ] **Step 2: Add the changelog entry**

If `CHANGELOG.md` has a `## Unreleased` heading, add a `### Kiko Purge VRAM` section to it; otherwise insert `## Unreleased` above the newest version heading first. Content: the new modes and order; old names mapped (`soft` and `aggressive` → `all`, `models_only` → `models`, `cache_only` → `cache`); **a non-zero `memory_threshold_mb` in a saved workflow now means "skip when at least this many MB are free" instead of "purge when this many MB are used"**; the two switches; the credit line with the link.

- [ ] **Step 3: Check**

Run: `$V/bin/black --check .` and `$V/bin/python -m pytest tests/unit/tools/test_kiko_purge_vram.py -p no:cacheprovider -q`
Expected: clean, all pass.

- [ ] **Step 4: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs(kiko_purge_vram): document the Pixaroma-style modes

- README section and table line, with credit to Free VRAM Pixaroma.
- Unreleased changelog entry, including the threshold's new meaning."
```
