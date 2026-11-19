# Kiko Prompt Enhancer: model picker, vision mode, GGUF backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give KikoPromptEnhancer three things: its own LLM picker (native ComfyUI encoders plus llama.cpp GGUF models), a text/vision mode, and an optional `clip` override. Fix the krea2 "no text" sentence and quote-safe trigger stripping.

**Architecture:**
- `models.py` lists and classifies local LLM files.
- `native_backend.py` holds today's CLIP tokenize/generate path, plus loading a picked encoder.
- `gguf_backend.py` runs llama.cpp when it is importable.
- `node.py` chooses a backend and keeps the shared clean → cap → no-text → trigger pipeline.

**Tech Stack:** Python 3.10+, ComfyUI (`comfy.sd`, `comfy.model_management`, `folder_paths`), optional `llama_cpp` (0.3.x), pytest.

**Spec:** `docs/superpowers/specs/2026-11-18-prompt-enhancer-design.md`. This plan implements the section "Addendum 2026-11-18: model picker, text/vision mode, GGUF backend".

## Global Constraints

- **No new hard dependencies.**
  - `llama_cpp` is imported lazily. If it is missing, GGUF entries are not listed, and one `logger.info` line says so.
  - `requirements.txt` stays unchanged.
- **Model combo values:**
  - `native: <path relative to its text_encoders root>`
  - `gguf: <path relative to its models/LLM or text_encoders root>`
  - Use forward slashes.
  - If nothing is found, the combo holds the single entry `(none found)`.
- **`mode` combo:** `["text", "vision"]`, default `"text"`.
- **The `clip` input is optional.** When connected it overrides `model`.
- **Errors (exact text):**
  - `"vision mode needs an image; connect one to the image input"`
  - `"<model name> cannot read images; pick a vision model (one with an mmproj file, or a Qwen-VL / Qwen3.5 encoder)"`
  - `"No model selected and no clip connected; pick a model or connect an encoder"`
  - `"llama-cpp-python is not installed; install it to use GGUF models"`
- **GGUF runs:**
  - Before loading, call `comfy.model_management.unload_all_models()` and `comfy.model_management.soft_empty_cache()`.
  - Pass `flash_attn=True` when CUDA is available, `n_gpu_layers=-1`, and `n_ctx=8192`.
  - `keep_loaded` (BOOLEAN, default False) keeps the `Llama` object between runs. Otherwise the node frees it after the run.
- **Native encoder type** comes from detecting the model, then a fixed map:

  | Detected model | `clip_type` |
  |---|---|
  | `QWEN35_*` | `moss_image` |
  | `QWEN3VL_4B` | `flux3` |
  | `QWEN3VL_8B` | `boogu` |
  | `QWEN3_4B` | `lumina2` |
  | `QWEN3_8B` | `flux2` |
  | `QWEN25_7B` | `qwen_image` |

  Any other detected model is not listed.
- **Vision-capable** means one of these:
  - a native `QWEN35_*`, `QWEN3VL_*` or `QWEN25_7B`;
  - a GGUF with a file whose name contains `mmproj` in the same folder.
- **`no_text_sentence:` front-matter key.**
  - The node appends this sentence only when the cleaned, capped output contains no `"…"` double-quoted span.
  - When it will be appended, cap at `max_words − len(sentence.split())`.
- **Trigger stripping** never changes characters except at the spots where a trigger was removed.
- **Pipeline order:** `split_thinking` → `clean_output` → `cap_words` → `append_no_text` → `prepend_triggers`.
- **Commit messages:** `<type>: <description>`, with no AI attribution lines or session links.
- **Test commands:**
  - Python: `/home/vito/comfy/ComfyUI/venv/bin/python -m pytest … --ignore=tests/test_embedding_autocomplete_fixed.py`
  - JS: `node --test tests/js/prompt-enhancer.test.mjs`

## Review Focus

1. A GGUF folder that holds several model quants plus one mmproj: every quant is vision-capable and the mmproj is never listed. Test: `test_mmproj_shared_by_all_quants` (Task 2).
2. A broken or truncated safetensors file in `text_encoders`: it is skipped with a warning and the listing still works. Test: `test_corrupt_safetensors_skipped` (Task 2).
3. `mode="text"` with an image wired: the image is never sent to either backend. Test: `test_text_mode_drops_image` (Task 5).
4. `clip` connected while `model` says `(none found)`: the run works through the clip. Test: `test_connected_clip_overrides_none_found` (Task 5).
5. A GGUF run that raises mid-generation with `keep_loaded=False`: the model is still freed. Test: `test_gguf_freed_after_error` (Task 4).

---

### Task 1: Quote-safe trigger stripping and the `no_text_sentence` key

**Files:**
- Modify: `kikotools/tools/prompt_enhancer/logic.py` (`strip_triggers`; add `append_no_text`)
- Modify: `kikotools/tools/prompt_enhancer/library.py` (`SystemPrompt.no_text_sentence`; parse the key)
- Modify: `kikotools/tools/prompt_enhancer/node.py` (cap budget, append step)
- Modify: `kikotools/tools/prompt_enhancer/system_prompts/krea2.md`
- Test: `tests/unit/tools/prompt_enhancer/test_logic.py`, `test_library.py`, `test_node.py`, `test_shipped_prompts.py`

**Interfaces:**
- Produces:
  - `SystemPrompt.no_text_sentence: Optional[str]`. This is a new last field with default `None`, so existing constructors keep working.
  - `append_no_text(text: str, sentence: Optional[str]) -> str`
  - `strip_triggers(prompt: str, trigger_words: str) -> str`. The signature is unchanged; only its behaviour changes.

- [ ] **Step 1: Write the failing tests.**
  - `test_strip_triggers_keeps_quoted_text`: `strip_triggers('mabes9sans, a sign "1,000  items,left"', "mabes9sans") == 'a sign "1,000  items,left"'`
  - `test_strip_triggers_untouched_without_match`: `strip_triggers("a,b  c", "zzz") == "a,b  c"`
  - `test_strip_triggers_mid_sentence`: `strip_triggers("a woman, mabes9sans, smiling", "mabes9sans") == "a woman, smiling"`
  - `test_append_no_text_when_no_quotes`: `append_no_text("A fox.", "No text.") == "A fox. No text."`
  - `test_append_no_text_skipped_with_quotes`: `append_no_text('A sign reading "OPEN".', "No text.") == 'A sign reading "OPEN".'`
  - `test_append_no_text_none_is_noop`
  - `test_no_text_sentence_parsed`: front matter `no_text_sentence: Absolutely no text.` gives `.no_text_sentence == "Absolutely no text."`
  - `test_node_appends_no_text_within_cap`: an override has `max_words: 10` and a 3-word sentence, and the scripted output is 12 words with no quotes. The result has 7 body words plus the sentence.
  - `test_node_skips_no_text_when_quoted`
  - `test_krea2_uses_no_text_key`: `load_prompt("krea2").no_text_sentence` starts with `"Absolutely no text"`, and the krea2 body no longer contains `"Absolutely no text"`.
  - Remove or replace the older krea2 example test that relied on the closing sentence in the body.
- [ ] **Step 2: Run the tests and confirm they fail.** `… -m pytest tests/unit/tools/prompt_enhancer -v`
- [ ] **Step 3: Implement.**
  - **`strip_triggers`:** remove each match of `(?<!\w)trigger(?!\w)` (case-insensitive). At each removal site only, collapse the surrounding `\s*,?\s*` into a single `", "`, or into nothing at the start or end of the string. Use one `re.sub` with a pattern that includes the adjacent separators.
  - **krea2.md:** remove rule 7's instruction to write the closing sentence. Keep "do not describe signage, labels or screens with writing when no text was asked for". Add the front-matter key with the existing sentence. Strip the sentence from the examples. Set rule 10 to "60 to 130 words".
- [ ] **Step 4: Run the tests again and confirm they pass.** Run the same command, then the full suite.
- [ ] **Step 5: Commit.** `fix: append the krea2 no-text sentence in code and keep quoted text when stripping triggers`

### Task 2: Model discovery

**Files:**
- Create: `kikotools/tools/prompt_enhancer/models.py`
- Test: `tests/unit/tools/prompt_enhancer/test_models.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class ModelEntry: name: str; kind: str; path: Path; vision: bool; mmproj: Optional[Path]; clip_type: Optional[str]`. `kind` is `"native"` or `"gguf"`.
  - `NONE_FOUND = "(none found)"`
  - `list_models() -> List[ModelEntry]`: sorted by name.
  - `model_names() -> List[str]`: returns `[NONE_FOUND]` when the list is empty.
  - `find_model(name: str) -> Optional[ModelEntry]`
  - `llama_available() -> bool`: does `importlib.util.find_spec("llama_cpp") is not None`, cached.
- Roots:
  - Native: `folder_paths.get_folder_paths("text_encoders")`.
  - GGUF: `os.path.join(folder_paths.models_dir, "LLM")` plus the `text_encoders` roots.
- Native detection:
  - Read the safetensors header (8-byte little-endian length, then JSON) and build `{key: SimpleNamespace(shape=tuple(v["shape"]))}`, skipping `__metadata__`.
  - Pass that to `comfy.sd.detect_te_model`.
  - Map the result with the table in Global Constraints. Unmapped results are excluded.
  - Cache per file by `(path, mtime, size)`.
- GGUF:
  - List every `*.gguf` whose name does not contain `mmproj` and whose name contains `qwen`, `llama` or `joycaption` (case-insensitive). That keeps umt5 and similar files out.
  - Use `mmproj` = the first `*mmproj*.gguf` in the same folder.
- Note for tests: they must not import real `comfy`. Monkeypatch a fake `comfy.sd` module whose `detect_te_model` returns an enum-like object with a `.name`, and a fake `folder_paths`.

- [ ] **Step 1: Write the failing tests** (using `tmp_path`, with `models_dir` and roots patched):
  - `test_native_listed_with_clip_type`: a tiny safetensors header detected as `QWEN35_9B` gives the entry `native: Moss/x.safetensors`, `clip_type == "moss_image"` and `vision`.
  - `test_native_text_only_qwen3_4b`: `vision is False` and `clip_type == "lumina2"`.
  - `test_unmapped_native_excluded`: a detected T5 file is not listed.
  - `test_corrupt_safetensors_skipped` (caplog): the warning names the file and the rest is still listed.
  - `test_gguf_vision_with_mmproj` and `test_mmproj_shared_by_all_quants`: two quants and one mmproj give two vision entries and no mmproj entry.
  - `test_umt5_gguf_excluded`.
  - `test_gguf_hidden_without_llama_cpp`: with `llama_available` patched to False, no `gguf:` entries are listed.
  - `test_none_found_placeholder`.
  - `test_find_model_round_trip`.
- [ ] **Step 2: Run the tests and confirm they fail.**
- [ ] **Step 3: Implement `models.py`.**
- [ ] **Step 4: Run the tests and confirm they pass,** then run the full suite.
- [ ] **Step 5: Commit.** `feat: list local LLMs for the prompt enhancer model picker`

### Task 3: Native backend (move the existing path, add loading)

**Files:**
- Create: `kikotools/tools/prompt_enhancer/native_backend.py`
- Modify: `kikotools/tools/prompt_enhancer/node.py` (call into it; move `_prompt_ids`, `UPDATE_COMFY`, `NO_GENERATE` and the generate call out of the node)
- Test: `tests/unit/tools/prompt_enhancer/test_native_backend.py`. Move the generation-specific assertions out of `test_node.py` where they now belong.

**Interfaces:**
- Consumes: `ModelEntry` (Task 2).
- Produces:
  - `generate_native(clip, system: str, prompt: str, image, seed: int, temperature: float, max_length: int, thinking: bool) -> str`. Returns the decoded raw text. It raises the existing vision, system-prompt, thinking and no-generate errors with the same messages.
  - `load_native(entry: ModelEntry)`: returns a CLIP object built with `comfy.sd.load_clip(ckpt_paths=[str(entry.path)], embedding_directory=folder_paths.get_folder_paths("embeddings"), clip_type=getattr(comfy.sd.CLIPType, entry.clip_type.upper()))`. It keeps a single-slot module cache keyed by path. ComfyUI manages its VRAM.

- [ ] **Step 1: Write the failing tests.**
  - The existing node generation tests move here, retargeted at `generate_native`.
  - New: `test_load_native_uses_clip_type_and_caches`. `load_clip` is monkeypatched. Calling twice with the same entry calls `load_clip` once with `clip_type=CLIPType.MOSS_IMAGE`.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.** The node keeps working through `generate_native` (Task 5 adds the picker).
- [ ] **Step 4: Run the full suite and confirm it passes.**
- [ ] **Step 5: Commit.** `refactor: move prompt enhancer generation into a native backend`

### Task 4: GGUF backend

**Files:**
- Create: `kikotools/tools/prompt_enhancer/gguf_backend.py`
- Test: `tests/unit/tools/prompt_enhancer/test_gguf_backend.py`

**Interfaces:**
- Consumes: `ModelEntry` (Task 2).
- Produces:
  - `generate_gguf(entry: ModelEntry, system: str, prompt: str, image, seed: int, temperature: float, max_length: int, thinking: bool, keep_loaded: bool) -> str`. Returns the raw assistant text.
  - `free_gguf() -> None`
- Behaviour:
  - It raises the exact llama-not-installed error when `import llama_cpp` fails.
  - Before loading, it unloads ComfyUI models (Global Constraints).
  - Load: `Llama(model_path=…, n_ctx=8192, n_gpu_layers=-1, flash_attn=torch.cuda.is_available(), seed=seed, verbose=False, chat_handler=handler)`.
  - `handler` is used only when an image is sent. Use the first of `Qwen3VLChatHandler`, `Qwen25VLChatHandler` or `MTMDChatHandler` present in `llama_cpp.llama_chat_format`, built with `clip_model_path=str(entry.mmproj)`.
  - Messages:
    - system: `system`
    - user: `prompt`, with `"\n/no_think"` appended unless `thinking`
    - with an image, the user content is a list holding an `image_url` part (a PNG data URI from the first frame of the IMAGE tensor) followed by a `text` part.
  - Sampling: `create_chat_completion(messages, temperature, top_k=64, top_p=0.95, min_p=0.05, repeat_penalty=1.05, max_tokens=max_length, seed=seed)`. Return `choices[0]["message"]["content"]`.
  - Cache: a single-slot module cache keyed by `(path, mmproj-if-used)`. With `keep_loaded=False`, free it in `finally`.
- Tests inject a fake `llama_cpp` module through `monkeypatch.setitem(sys.modules, …)`.

- [ ] **Step 1: Write the failing tests:**
  - `test_missing_llama_cpp_raises`
  - `test_text_run_messages_and_params`: asserts the system message, the `/no_think` suffix, `max_tokens`, `seed`, `flash_attn` and `n_ctx=8192`.
  - `test_thinking_skips_no_think`
  - `test_image_run_uses_handler_and_data_uri`
  - `test_unloads_comfy_models_first`
  - `test_keep_loaded_reuses_model`
  - `test_gguf_freed_after_error`
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement `gguf_backend.py`.**
- [ ] **Step 4: Run them and confirm they pass,** then run the full suite.
- [ ] **Step 5: Commit.** `feat: run GGUF models through llama.cpp in the prompt enhancer`

### Task 5: Node wiring (picker, mode, clip override)

**Files:**
- Modify: `kikotools/tools/prompt_enhancer/node.py`
- Test: `tests/unit/tools/prompt_enhancer/test_node.py`

**Interfaces:**
- Consumes: `model_names`, `find_model` and `NONE_FOUND` (Task 2); `generate_native` and `load_native` (Task 3); `generate_gguf` (Task 4); `append_no_text` (Task 1).
- Inputs:
  - Required, in this order: `prompt`, `base_model`, `model` (`model_names()`, default: the first entry whose name contains `uncensored`, `abliterated` or `heretic`, else the first), `mode`, `seed`.
  - Optional: `clip`, `trigger_words`, `image`, `temperature`, `max_length`, `thinking`, `keep_loaded` (all advanced except `clip`, `trigger_words` and `image`).
- `enhance(self, prompt, base_model, model, mode, seed, clip=None, trigger_words="", image=None, temperature=0.7, max_length=1024, thinking=False, keep_loaded=False) -> Tuple[str, str]`
- Flow:
  1. Empty and trigger checks, as today.
  2. `image = image if mode == "vision" else None`.
  3. In vision mode with no image, raise the vision error.
  4. Compose the system prompt; the image section only when an image is sent.
  5. If `clip` is connected, use `generate_native(clip, …)`.
  6. Otherwise `entry = find_model(model)`. If it is missing or `NONE_FOUND`, raise the no-model error. In vision mode with `not entry.vision`, raise the cannot-read-images error. Then dispatch by `entry.kind`.
  7. Shared pipeline (Global Constraints order).
- `IS_CHANGED` hashes the prompt file bytes plus `model` and `mode`.

- [ ] **Step 1: Write the failing tests** (backends monkeypatched):
  - `test_text_mode_drops_image`
  - `test_vision_mode_requires_image`
  - `test_vision_mode_rejects_text_only_model`
  - `test_connected_clip_overrides_none_found`
  - `test_gguf_entry_dispatches_to_gguf`
  - `test_native_entry_loads_and_dispatches`
  - `test_no_model_no_clip_raises`
  - `test_default_model_prefers_uncensored`
  - `test_is_changed_follows_model_and_mode`
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the full suite and the JS test, and confirm they pass.**
- [ ] **Step 5: Commit.** `feat: add model picker, text/vision mode and optional clip to the prompt enhancer`

### Task 6: Docs

**Files:**
- Modify: `README.md` (Kiko Prompt Enhancer section), `CHANGELOG.md` (Unreleased)

- [ ] **Step 1: Update the docs.** Cover:
  - the model picker (`native:` and `gguf:` entries, how vision capability is decided, GGUF needs llama-cpp-python, `keep_loaded`);
  - mode text/vision and its errors;
  - the `clip` override;
  - the `no_text_sentence:` key in the file format.
- [ ] **Step 2: Run the full suite.**
- [ ] **Step 3: Commit.** `docs: document the prompt enhancer model picker and vision mode`

### After the tasks (controller, not a subagent task)

1. Rebuild `vito-moody-moss-v7` in comfy-tools with:
   - the `model` widget set to `native: Moss/qwen3.5_9b_uncensored_fp16.safetensors`;
   - `mode` set to `text`;
   - the enhancer's `clip` link removed, so the picker is used.
2. Run a live check with three models:
   - native Qwen3.5 9B uncensored: text, then vision with the reference image;
   - GGUF Huihui Qwen3.8 27B: vision;
   - GGUF Qwen3-4B abliterated: text, then vision, which should fail with the cannot-read-images error.
3. Re-run krea2 with the OPEN prompt.
