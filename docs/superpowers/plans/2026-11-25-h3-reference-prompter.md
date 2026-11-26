# H3 Reference Prompter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A KikoTools node that looks at up to three reference pictures (character, outfit, pose) with a local text-and-vision model and rewrites a short draft into a long, detailed MiniMax H3 Image prompt that keeps the draft's `<Picture N>` tags.

**Architecture:** New tool `kikotools/tools/h3_reference_prompter/`: pure helpers (`logic.py`), instruction text (`instructions.py`), model listing (`models.py`), a transformers backend (`hf_backend.py`) and the node (`node.py`). It reuses the Kiko Prompt Enhancer's model entries and its native and GGUF backends, and the safe unload from Kiko Purge VRAM. Two passes: describe each picture for its role, then write the prompt. Frontend shows the result with the `web/ui/` toolkit.

**Tech Stack:** Python 3.10+, ComfyUI V1 node API, transformers 5.19 (`AutoProcessor`, `AutoModelForImageTextToText`), optional llama-cpp-python, torch; JS ES modules with node:test and Playwright.

**Spec:** `docs/superpowers/specs/2026-11-25-h3-reference-prompter-design.md`

## Global Constraints

- Work in `/home/vito/code/personal/ComfyUI-KikoTools-h3prompt` on branch `feat/h3-reference-prompter` (it contains the PR #140 purge branch). Never touch `/home/vito/code/personal/ComfyUI-KikoTools` (the live ComfyUI loads it) or the ComfyUI install.
- Node id `KikoH3ReferencePrompter`, display name `H3 Reference Prompter`, category `🫶 ComfyAssets/🧠 Prompts`, base class `ComfyAssetsBaseNode`.
- Own code and own instruction text only. Copy nothing from ComfyUI-MiniMax-H3-Promptor or ComfyUI-QwenVL (both GPL-3.0), and add no credit line for them.
- `image_N` is always `<Picture N>` (N = 1, 2, 3); slots are never renumbered.
- Roles: `character`, `outfit`, `pose`, `other`; defaults `image_1` character, `image_2` outfit, `image_3` pose.
- The result must contain exactly the set of `<Picture N>` tags found in the draft. Retry once; then raise `ValueError` naming missing and extra tags.
- English output, full sentences, target 250 to 450 words, in this section order: the draft's reference sentences (tags exact), subject head to hands, outfit garment by garment, pose with each hand and foot, camera (height, side, distance, direction, framing), a lighting sentence (source, hardness, what it touches), background, the draft's style sentence, a short closing list of what must not appear (one problem per line).
- The pose description never describes the mannequin's own look (surface, colour, build, face).
- Draft instructions win over picture notes (for example "leave out the shoes", the style sentence, the pose name).
- Before loading a prompt model call `kikotools.tools.kiko_purge_vram.logic.unload_models_safely()`; on any failure call `repair_loaded_models()` before re-raising. Never call `comfy.model_management.unload_all_models()` directly from this tool.
- transformers loading: `trust_remote_code=False` always; bf16 on CUDA, float32 on CPU fallback.
- Recognised Hugging Face folders: directories under `models/LLM` (recursive) holding `config.json` whose `architectures` contains one of `Qwen3_5ForConditionalGeneration`, `Qwen3VLForConditionalGeneration`, `Gemma4ForConditionalGeneration`, `Gemma4UnifiedForConditionalGeneration`. Picker name `hf: <path relative to models/LLM>`.
- The Kiko Prompt Enhancer's behaviour and picker do not change.
- Tests need no GPU and no model weights. Python coverage floor 85%; every new JS file needs a reviewed entry in `tools/testing/frontend-coverage-baseline.json`.
- Commits: conventional `type(scope): subject` with a bullet body; stage only named files; no AI or Claude attribution of any kind (no Co-Authored-By, no Claude-Session trailer, no claude.ai links). Push with an explicit refspec.

## Review Focus

- A draft with no `<Picture N>` tags at all (plain text) must still work, and the result must contain no tags. Pinned in Task 1 and Task 5.
- A slot holding a batch of more than one image (an IMAGE tensor with batch > 1, not a list) must fail with an error naming the slot, not silently describe one frame. Pinned in Task 5.
- Model output wrapped in chatter ("Here is your prompt:", quotes, markdown fences, a `<think>` block) must come back as the bare prompt. Pinned in Task 1.
- A workflow saved with a model name missing on this machine must load (validation passes) and fail at run time with a message naming the model and the folders searched. Pinned in Task 5.
- One-per-pose: three poses with one character and one outfit must describe the character and outfit once and each pose once, and load the model once. Pinned in Task 5.

---

### Task 1: Pure helpers

**Files:**
- Create: `kikotools/tools/h3_reference_prompter/__init__.py` (empty for now), `kikotools/tools/h3_reference_prompter/logic.py`
- Test: `tests/unit/tools/h3_reference_prompter/__init__.py`, `tests/unit/tools/h3_reference_prompter/test_logic.py`

**Interfaces:**
- Produces, in `logic.py`:
  - `ROLES: Tuple[str, ...] = ("character", "outfit", "pose", "other")`, `DEFAULT_ROLES = ("character", "outfit", "pose")`, `SLOTS = 3`
  - `find_tags(text: str) -> Set[int]` — the N of every `<Picture N>`, tolerant of spaces inside the brackets (`< Picture 2 >`).
  - `tag_problems(draft: str, result: str) -> Tuple[List[int], List[int]]` — `(missing, extra)`, both sorted.
  - `pair_items(**columns: List[Any]) -> List[Dict[str, Any]]` — length-1 columns are repeated; columns longer than 1 must share one length, else `ValueError` naming each column's length; an empty column (ComfyUI sends `[]` or `[None]` for an unconnected optional input) becomes `None` per item.
  - `item_seed(seed: int, index: int) -> int` — `(seed + index) % 2**64`.
  - `image_key(image: torch.Tensor, role: str, model: str) -> str` — sha256 of the tensor's bytes (contiguous, CPU) plus shape, role and model.
  - `clean_result(text: str) -> str` — reuse `prompt_enhancer.logic.split_thinking` and `clean_output`, then also strip a leading line such as `Here is the prompt:` / `Prompt:` and surrounding quotes or code fences.

- [ ] **Step 1: Write the failing tests** — `test_find_tags` (`"<Picture 1> and < Picture 3 >"` → `{1, 3}`; no tags → `set()`), `test_tag_problems` (draft tags `{1,2,3}`, result `{1,3,4}` → `([2], [4])`; plain draft and plain result → `([], [])`), `test_pair_items_broadcasts_and_checks_lengths` (`prompt` × 3 with `image_1` × 1 → 3 items each with the one image; lengths 2 and 3 → `ValueError` mentioning `2` and `3`; `[]` → `None`), `test_item_seed` (`item_seed(2**64 - 1, 1) == 0`), `test_image_key_changes_with_content_role_model`, `test_clean_result_strips_chatter` (cases: `"<think>x</think>\nA woman..."`, `"Here is the prompt:\n\"A woman...\""`, a fenced block).
- [ ] **Step 2: Run** `$V/bin/python -m pytest tests/unit/tools/h3_reference_prompter -p no:cacheprovider -q` — FAIL on import. (`V=/tmp/claude-1000/-home-vito-code-personal-ComfyUI-KikoTools/f79925f2-d12d-4383-ad2e-85d80c922cf7/scratchpad/venv`.)
- [ ] **Step 3: Implement `logic.py`.**
- [ ] **Step 4: Run** the same command — PASS.
- [ ] **Step 5: Commit** `feat(h3_reference_prompter): tag, list and cleanup helpers` with a bullet body.

### Task 2: Instruction text

**Files:**
- Create: `kikotools/tools/h3_reference_prompter/instructions.py`
- Test: `tests/unit/tools/h3_reference_prompter/test_instructions.py`

**Interfaces:**
- Consumes: `ROLES` from Task 1.
- Produces:
  - `describe_system(role: str) -> str` — the pass-1 system text for one picture of that role (see the spec's Goal 1 lists, verbatim as requirements). Unknown role → `ValueError`.
  - `describe_user(role: str, draft: str) -> str` — the pass-1 user message: asks for factual notes on this picture only, as short sentences, and gives the draft for context.
  - `writer_system() -> str` — pass-2 system text carrying the Global Constraints' section order, word target, full-sentence rule, tag rule, draft-wins rule and mannequin rule.
  - `writer_user(draft: str, notes: List[Tuple[int, str, Optional[str]]]) -> str` — `notes` is `(slot, role, text or None)` in slot order; text `None` means "no picture; use the draft's words". Each note is labelled with its tag, e.g. `Notes for <Picture 2> (outfit): ...`; a connected slot whose tag is absent from the draft is labelled as context only, with "do not write its tag".
  - `retry_user(problems: Tuple[List[int], List[int]]) -> str` — a short correction naming the missing and extra tags.

- [ ] **Step 1: Write the failing tests** — `test_describe_system_covers_role_fields` (character mentions face, eyes, hair, skin, build and excludes clothing; outfit mentions each garment, colour, material, footwear; pose mentions each hand and each foot, weight, camera height/side/distance/direction, and says not to describe the mannequin's surface, colour, build or face); `test_describe_system_rejects_unknown_role`; `test_writer_system_lists_sections_in_order` (the nine section names appear in order; mentions `250` and `450`; says full sentences; says keep every `<Picture N>` tag exactly and add none); `test_writer_user_labels_notes_by_tag` (slot 2 outfit text → `<Picture 2>` label; `None` text → "no picture" wording; a slot not in the draft → "do not write its tag"); `test_retry_user_names_tags`.
- [ ] **Step 2: Run** the Task 1 command — FAIL.
- [ ] **Step 3: Write `instructions.py`.** Text written fresh, guided by https://platform.minimax.io/docs/guides/image-generation and https://openart.ai/blog/minimax-h3-image-prompt-guide/ : subject first, head to hands, key traits stated two ways, each hand's action, camera in four parts, lighting in its own sentence with what it touches, specific materials and surface detail, one-problem-per-line closing list, no style string at the start.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(h3_reference_prompter): describe and writer instructions`.

### Task 3: Model listing

**Files:**
- Create: `kikotools/tools/h3_reference_prompter/models.py`
- Test: `tests/unit/tools/h3_reference_prompter/test_models.py`

**Interfaces:**
- Consumes: `prompt_enhancer.models.ModelEntry`, `prompt_enhancer.models.list_models`, `NONE_FOUND`.
- Produces:
  - `HF_ARCHITECTURES` — the four names in Global Constraints.
  - `hf_entries(llm_root: Path) -> List[ModelEntry]` — `kind="hf"`, `path` = the folder, `vision=True`, `mmproj=None`, `clip_type=None`, name `hf: <relative path>`; skips folders whose `config.json` is missing, unreadable or lists another architecture; does not descend into a recognised folder.
  - `list_prompter_models() -> List[ModelEntry]` — `hf_entries` of `folder_paths.models_dir/LLM` plus the Enhancer's entries with `vision=True` (GGUF only when it has an `mmproj`), sorted by name, unique by name.
  - `prompter_model_names() -> List[str]` (or `[NONE_FOUND]`), `find_prompter_model(name: str) -> Optional[ModelEntry]`, `default_prompter_model(names: List[str]) -> str` — prefers a name containing `Qwen3.5-4B`, then any `hf:` entry, then the first.

- [ ] **Step 1: Write the failing tests** with a `tmp_path` tree: `LLM/Qwen-VL/Qwen3.5-4B-Unredacted-MAX/config.json` (`Qwen3_5ForConditionalGeneration`), `LLM/gemma-4-e4b/config.json` (`Gemma4ForConditionalGeneration`), `LLM/text-only/config.json` (`Qwen3ForCausalLM`), `LLM/broken/config.json` (invalid JSON), a nested folder inside the Qwen folder that also has a config. Assert names `hf: Qwen-VL/Qwen3.5-4B-Unredacted-MAX` and `hf: gemma-4-e4b` only. Patch `folder_paths` and the Enhancer's `list_models` to check merging, the vision filter, the GGUF-needs-mmproj rule, `default_prompter_model`, and that `prompt_enhancer.models.model_names()` is unchanged by this module.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement `models.py`.**
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(h3_reference_prompter): list text-and-vision models`.

### Task 4: Transformers backend

**Files:**
- Create: `kikotools/tools/h3_reference_prompter/hf_backend.py`
- Test: `tests/unit/tools/h3_reference_prompter/test_hf_backend.py`

**Interfaces:**
- Consumes: `ModelEntry` (kind `hf`).
- Produces:
  - `generate_hf(entry: ModelEntry, system: str, prompt: str, image: Optional[torch.Tensor], seed: int, temperature: float, max_length: int) -> str` — keeps one loaded model in a module slot (reloads only when the path changes); builds chat messages `[{"role": "system", ...}, {"role": "user", "content": [image part if any, text part]}]`; applies the processor's chat template with `add_generation_prompt=True` and `enable_thinking=False` (retry without the keyword if the template rejects it); converts the ComfyUI image (B=1, H, W, C, 0–1 float) to a PIL image; seeds torch; samples with the given temperature (`do_sample=temperature > 0`); returns only the new tokens decoded with special tokens skipped.
  - `free_hf() -> None` — drops the slot, `gc.collect()`, empties the CUDA cache.
  - Loading uses `AutoProcessor.from_pretrained(path, trust_remote_code=False)` and `AutoModelForImageTextToText.from_pretrained(path, trust_remote_code=False, dtype=torch.bfloat16 on CUDA else torch.float32)` moved to the device; missing transformers → `ValueError` saying to install it.

- [ ] **Step 1: Write the failing tests** with a fake `transformers` module in `sys.modules` (fake processor recording `apply_chat_template` kwargs and returning tensors; fake model whose `generate` returns prompt ids plus new ids): loads once for two calls with the same entry and reloads for another; `trust_remote_code=False` passed to both `from_pretrained`; `enable_thinking=False` passed, and a template that raises `TypeError` on it is retried without; the image is passed as a PIL image in the user content; only new tokens are decoded; `free_hf` clears the slot; missing transformers raises `ValueError`.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement `hf_backend.py`.**
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(h3_reference_prompter): transformers backend for model folders`.

### Task 5: The node

**Files:**
- Create: `kikotools/tools/h3_reference_prompter/node.py`; fill `__init__.py` (export `H3ReferencePrompterNode`)
- Modify: `kikotools/__init__.py` (import, `NODE_CLASS_MAPPINGS["KikoH3ReferencePrompter"]`, display name `H3 Reference Prompter`)
- Test: `tests/unit/tools/h3_reference_prompter/test_node.py`

**Interfaces:**
- Consumes: Tasks 1–4; `prompt_enhancer.native_backend.load_native`, `generate_native`; `prompt_enhancer.gguf_backend.generate_gguf`, `free_gguf`; `kiko_purge_vram.logic.unload_models_safely`, `repair_loaded_models`.
- Produces: `H3ReferencePrompterNode` with `INPUT_TYPES` — required `prompt` (STRING multiline), `model` (picker from `prompter_model_names()`, default `default_prompter_model`), `role_1`/`role_2`/`role_3` (`ROLES`, defaults `DEFAULT_ROLES`), `seed` (INT, `control_after_generate`); optional `image_1`–`image_3` (IMAGE), advanced `temperature` (FLOAT 0.7, 0.01–2.0), `describe_tokens` (INT 512, 64–4096), `write_tokens` (INT 1536, 256–8192), `keep_loaded` (BOOLEAN False). `INPUT_IS_LIST = True`, `RETURN_TYPES = ("STRING", "STRING")`, `RETURN_NAMES = ("prompt", "notes")`, `OUTPUT_IS_LIST = (True, True)`, `FUNCTION = "write"`, `VALIDATE_INPUTS(cls, model)` returns `True` for any string, and `write(...)` returns `{"ui": {"h3_prompts": [...], "h3_notes": [...]}, "result": (prompts, notes)}`.
- A single dispatcher `_generate(entry, clip, system, prompt, image, seed, temperature, max_length) -> str` routes `hf` → `generate_hf`, `gguf` → `generate_gguf(..., thinking=False, keep_loaded=True)`, `native` → `generate_native` with a clip from `load_native(entry)` loaded once per run.

The pass-1 cache is a module-level dict in `node.py` (lives for the ComfyUI session, cleared on restart). A GGUF load or generation error is re-raised as `ValueError` naming the model and suggesting a transformers folder under `models/LLM` instead (Gemma 4 vision through llama-cpp 0.3.36 is unverified); test `test_gguf_failure_names_model_and_suggests_folder`.

Run flow: pair items; resolve the model or raise (Review Focus line 4); reject any slot tensor with batch > 1 (`ValueError` naming `image_N`); call `unload_models_safely()` once; for each item: describe each connected slot through the cache (`image_key`), build `writer_user`, write with `item_seed`, `clean_result`, check `tag_problems`, retry once with `retry_user`, else raise; notes output lists each slot's role and notes. Wrap the whole run: on exception call `repair_loaded_models()` and re-raise. At the end free the backend (`free_hf`, `free_gguf`, drop the native clip) unless `keep_loaded`.

- [ ] **Step 1: Write the failing tests** with a fake `_generate` (patched) returning scripted text and recording calls, and patched `unload_models_safely` / `repair_loaded_models`:
  - `test_input_types_and_metadata` (names, defaults, list flags, category, display mapping registered in `kikotools/__init__.py`).
  - `test_one_item_two_passes` (3 images → 3 describe calls with the right `describe_system(role)`, 1 write call; result and notes returned; ui keys present).
  - `test_one_per_pose_caches_character_and_outfit` (prompts × 3, `image_3` × 3, `image_1`/`image_2` × 1 → describe calls 2 + 3 = 5, write calls 3, `unload_models_safely` once, seeds `s, s+1, s+2`).
  - `test_plain_draft_without_tags` (no tags in draft, result without tags passes).
  - `test_tag_retry_then_error` (first result missing `<Picture 2>` → one retry with `retry_user`; second still missing → `ValueError` naming `2`; `repair_loaded_models` called).
  - `test_batch_tensor_in_a_slot_is_rejected` (`image_3` shape `[2, H, W, 3]` → `ValueError` mentioning `image_3`).
  - `test_missing_model_validates_then_fails_clearly` (`VALIDATE_INPUTS("hf: gone")` is `True`; run raises naming `hf: gone` and `models/LLM`).
  - `test_unmentioned_slot_is_context_only` (image_3 connected, draft mentions only 1 and 2 → writer message says not to write `<Picture 3>`; result with `<Picture 3>` triggers the retry).
  - `test_backend_freed_unless_keep_loaded`.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement `node.py` and the registration.**
- [ ] **Step 4: Run** the tool's tests, then the full suite: `$V/bin/python -m pytest tests -p no:cacheprovider -q --cov=kikotools` (≥ 85%), `$V/bin/black --check .`, `$V/bin/flake8 kikotools/tools/h3_reference_prompter tests/unit/tools/h3_reference_prompter`.
- [ ] **Step 5: Commit** `feat(h3_reference_prompter): H3 Reference Prompter node`.

### Task 6: Frontend

**Files:**
- Create: `web/h3_reference_prompter.js` (extension), `web/ui/h3-reference-prompter.js` (pure helpers, no ComfyUI imports)
- Modify: `tools/testing/frontend-coverage-baseline.json` (reviewed floors for both files), `tests/browser/workflows.spec.mjs`
- Test: `tests/js/h3-reference-prompter.test.mjs`

**Interfaces:**
- Consumes: the node's `ui` payload `{h3_prompts: string[], h3_notes: string[]}` from Task 5.
- Produces: on `onExecuted`, a DOM panel under the node's widgets showing the item count, the prompt of the selected item (previous/next when more than one), a copy button, and a collapsible notes section; built with `web/ui/core.js` (`createScope`, `mountTheme`) and `controls.css` like the Local Image Loader. Pure helpers in `web/ui/h3-reference-prompter.js`: `summary(prompts) -> string` (e.g. `3 prompts`), `clampIndex(index, length) -> number`, `wordCount(text) -> number`.

- [ ] **Step 1: Write the failing tests** — node:test for the three helpers; a Playwright test in `workflows.spec.mjs` following the Prompt Enhancer test's pattern (around line 2130): add the node, deliver an executed message with two prompts, assert the count, step to the second prompt, click copy and check the clipboard text, toggle notes.
- [ ] **Step 2: Run** `env npm test --prefix tools/testing` and `env KIKO_TEST_PYTHON=$V/bin/python npm run --prefix tools/testing test:browser -- --project chromium -g "H3 Reference Prompter"` — FAIL.
- [ ] **Step 3: Implement both files; add coverage baseline entries at the measured coverage.**
- [ ] **Step 4: Run** the two commands, then `env KIKO_TEST_PYTHON=$V/bin/python npm run --prefix tools/testing test:coverage` — PASS ("Frontend coverage passed").
- [ ] **Step 5: Commit** `feat(h3_reference_prompter): show the written prompts on the node`.

### Task 7: Docs

**Files:**
- Modify: `README.md` (tool table line under 🧠 Prompts, a section like the Kiko Prompt Enhancer's), `CHANGELOG.md` (`## Unreleased` → `### H3 Reference Prompter`)
- Create: `examples/documentation/h3_reference_prompter.md`

- [ ] **Step 1: Write the docs.** Cover: what it does; inputs, roles and outputs; the `<Picture N>` slot rule; the two passes; one-per-pose lists; where to put models (`ComfyUI/models/LLM/Qwen-VL/Qwen3.5-4B-Unredacted-MAX/` from https://huggingface.co/prithivMLmods/Qwen3.5-4B-Unredacted-MAX, Gemma 4 E4B folders from https://huggingface.co/collections/huihui-ai/gemma-4-abliterated, GGUF with `mmproj` optional); that the model unloads after the run and ComfyUI's models are freed first; a short example draft and an example of the kind of prompt it writes (describe its shape; do not paste output from any other pack). No credit line for other packs.
- [ ] **Step 2: Check** `$V/bin/black --check .` and the tool's tests — PASS.
- [ ] **Step 3: Commit** `docs(h3_reference_prompter): document the H3 Reference Prompter`.
