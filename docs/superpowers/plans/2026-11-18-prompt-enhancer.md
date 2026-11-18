# Kiko Prompt Enhancer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `KikoPromptEnhancer` node that rewrites a short prompt in the style of a chosen base model. It uses the loaded text encoder, an optional image, and system prompts that users can override.

**Architecture:** The new tool package `kikotools/tools/prompt_enhancer/` is split into four files:
- `library.py`: finds and parses the shipped and override system prompt files;
- `logic.py`: pure text helpers for output clean-up, trigger words and the word cap;
- `node.py`: tokenize, generate and decode through the CLIP object, the same way core `TextGenerateV2` does;
- `routes.py`: one POST route that copies a shipped prompt into the override folder.

A small web extension adds the node's context-menu entry.

**Tech Stack:** Python 3.10+, ComfyUI legacy node API (`INPUT_TYPES`), aiohttp routes on `server.PromptServer`, pytest, plain JS ComfyUI extension, and `node --test` for JS.

**Spec:** `docs/superpowers/specs/2026-11-18-prompt-enhancer-design.md`

## Global Constraints

- Node id `KikoPromptEnhancer`. Display name "Kiko Prompt Enhancer". Category `🫶 ComfyAssets/🧠 Prompts`. It subclasses `ComfyAssetsBaseNode`.
- Shipped prompts live in `kikotools/tools/prompt_enhancer/system_prompts/<stem>.md`. The override folder is `<folder_paths.get_user_directory()>/kikotools/system_prompts/`.
- The combo value is the file stem. Overrides match shipped files by stem. A new stem adds an entry.
- No negative-prompt output, no new dependencies (no PyYAML), no network calls, and no content policy text in any shipped prompt.
- `trigger_words` never goes into the generation. It is placed in front of the output, joined with `", "`.
- Pack updates never write into the override folder. Only the copy route writes there, and it never overwrites an existing file.
- Commit messages follow `<type>: <description>` with no AI attribution lines or session links.
- Run Python checks with `/home/vito/code/personal/ComfyUI-KikoTools/venv/bin/python -m pytest` from the worktree root. If that venv lacks a package, use the ComfyUI venv `/home/vito/comfy/ComfyUI/venv/bin/python`.

## Decisions this plan makes (spec left them to the builder)

- **Vision check:** after `clip.tokenize(..., image=image)`, scan the tokens for a dict with `"type": "image"`. Non-vision tokenizers swallow `image` through `**kwargs` without complaint, so the call alone proves nothing. No image embed means a `ValueError`: "<encoder class> did not take the image; load a vision encoder such as Qwen3-VL or Qwen3.5".
- **System prompt check (covers old ComfyUI and non-chat encoders):** decode the tokenized ids and confirm the first 40 characters of the system prompt appear. Older cores and non-chat tokenizers drop `system_prompt` silently. If it's missing, raise `ValueError`: "This encoder ignored the system prompt. Update ComfyUI (Sept 2026 or newer) or use a chat encoder such as Qwen3, Qwen3-VL or Qwen3.5". If `clip` has no `generate`, raise the same "update ComfyUI" error.
- **File format:** optional front matter between two `---` lines with `key: value` pairs (only `max_words: <int>` is read). The body is the system prompt. A line that is exactly `## With an image` splits the body: text after it is appended only when an image is attached. A bad or unknown header value is logged as a warning and ignored; the body is still used.
- **Word cap:** when the output exceeds `max_words`, trim it back to the last sentence end (`.`, `!` or `?`) within the cap. With no sentence end inside the cap, cut at the cap. Trigger words don't count toward the cap.
- **Sampling:** always sampled. Fixed values match core defaults: `top_k=64`, `top_p=0.95`, `min_p=0.05`, `repetition_penalty=1.05`, `presence_penalty=0.0`. Exposed: `temperature` (default 0.7), `max_length` (default 1024), `thinking` (default False), `seed`.
- **Default combo entry:** `krea2` if present, otherwise the first entry in sorted order.
- **Re-runs after editing a file:** `IS_CHANGED` returns a hash of the resolved prompt file's text. Editing an override takes effect on the next queue.

## Review Focus

1. The model wraps its answer in a preamble ("Here is the enhanced prompt:") or in quotes. Strip both. Owner: Task 2 (`test_clean_output_strips_preamble_and_quotes`).
2. Trigger words typed with stray commas or spaces (`" mabes9sans, "`) produce one clean prefix with no double comma. Owner: Task 2 (`test_prepend_triggers_normalises_separators`).
3. An override file with a broken header (`max_words: lots`) still loads its body and logs a warning. Owner: Task 1 (`test_bad_header_value_is_ignored_with_warning`).
4. Editing an override and re-queuing with identical inputs runs again rather than returning ComfyUI's cached result. Owner: Task 3 (`test_is_changed_follows_file_content`).
5. An empty prompt with no image raises a clear error. An empty prompt with an image is allowed (describe the image). Owner: Task 3 (`test_empty_prompt_without_image_raises`, `test_empty_prompt_with_image_runs`).

---

### Task 1: Prompt library (discovery, overrides, parsing)

**Files:**
- Create: `kikotools/tools/prompt_enhancer/__init__.py` (empty for now; Task 3 exports the node)
- Create: `kikotools/tools/prompt_enhancer/library.py`
- Create: `kikotools/tools/prompt_enhancer/system_prompts/krea2.md` (placeholder with `max_words: 150`; Task 5 replaces it)
- Test: `tests/unit/tools/prompt_enhancer/__init__.py`, `tests/unit/tools/prompt_enhancer/test_library.py`

**Interfaces:**
- Produces:
  - `SHIPPED_DIR: Path`
  - `IMAGE_HEADING = "## With an image"`
  - `@dataclass(frozen=True) class SystemPrompt: stem: str; text: str; image_text: str; max_words: Optional[int]; path: Path; is_override: bool`
  - `override_dir() -> Optional[Path]`: the override folder path, None when there's no user dir. Follows `model_resolution_picker/override.py:override_path`.
  - `parse_prompt_file(stem: str, raw: str, path: Path, is_override: bool) -> SystemPrompt`
  - `available_prompts() -> Dict[str, SystemPrompt]`: shipped entries merged with overrides; the override wins on the same stem.
  - `prompt_names() -> List[str]`: sorted stems.
  - `default_prompt_name(names: List[str]) -> str`
  - `load_prompt(stem: str) -> SystemPrompt`: raises `ValueError("Unknown base model '<stem>'")` when the stem is missing.

- [ ] **Step 1: Write the failing tests** in `test_library.py`. Use an autouse fixture that points `folder_paths.get_user_directory` at `tmp_path`, the same way `tests/unit/tools/model_resolution_picker/test_override.py` does.
  - `test_shipped_prompts_listed`: `"krea2" in prompt_names()`.
  - `test_override_replaces_shipped_by_stem`: write `tmp/kikotools/system_prompts/krea2.md` containing `"mine"`. Then `load_prompt("krea2").text == "mine"` and `.is_override`.
  - `test_override_adds_new_entry`: `lustify-v9.md` appears in `prompt_names()`.
  - `test_missing_override_dir_is_fine`: no folder means shipped entries only, no exception.
  - `test_front_matter_parsed`: `"---\nmax_words: 80\n---\nBody"` gives `max_words == 80` and `text == "Body"`.
  - `test_image_section_split`: `"Body\n## With an image\nMotion only."` gives `text == "Body"` and `image_text == "Motion only."`.
  - `test_bad_header_value_is_ignored_with_warning` (caplog): `max_words: lots` gives `max_words is None`, the body is kept, and a warning names the file.
  - `test_unknown_stem_raises`: `load_prompt("nope")` raises `ValueError` matching "Unknown base model".
  - `test_default_prefers_krea2`: `default_prompt_name(["a", "krea2"]) == "krea2"` and `default_prompt_name(["b", "a"]) == "a"`.
  - `test_non_md_files_ignored`: `notes.txt` in the override folder is not listed.

- [ ] **Step 2: Run them and confirm they fail.** Run `…/python -m pytest tests/unit/tools/prompt_enhancer/test_library.py -v`. Expected: an ImportError on `library`.
- [ ] **Step 3: Implement `library.py`** with the interfaces above. Read files as UTF-8 and strip the body. Files are read on every call; there is no cache, since they are small.
- [ ] **Step 4: Run the tests again.** Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat: add prompt enhancer system prompt library"`

### Task 2: Output helpers

**Files:**
- Create: `kikotools/tools/prompt_enhancer/logic.py`
- Test: `tests/unit/tools/prompt_enhancer/test_logic.py`

**Interfaces:**
- Produces:
  - `split_thinking(generated: str) -> str`: returns the answer text with the thinking removed. It mirrors the `</think>` partition in core `comfy_extras/nodes_textgen.py` (`TextGenerateV2.execute`), minus the prompt-token check: when there's no `</think>` and the text starts with `<think>`, return `""`.
  - `clean_output(text: str) -> str`:
    - strips whitespace;
    - removes one leading preamble line matching `^(here is|here's|enhanced prompt|prompt)\b[^\n]*:\s*\n` (case-insensitive);
    - removes one pair of wrapping `"…"`, `'…'` or ``` fences.
  - `cap_words(text: str, max_words: Optional[int]) -> str`: the rule from "Decisions".
  - `prepend_triggers(text: str, trigger_words: str) -> str`: splits on commas, strips each part, drops empty parts, then joins the triggers and the text with `", "`. Returns `text` unchanged when there are no triggers.
  - `tokens_include_image(tokens: Any) -> bool`: walks the dict or list of lists of tuples and returns True if any tuple's first element is a dict with `type == "image"`.

- [ ] **Step 1: Write the failing tests:**
  - `test_split_thinking_removes_block`: `"<think>x</think>\nAnswer"` gives `"Answer"`.
  - `test_split_thinking_cut_off`: `"<think>never closed"` gives `""`.
  - `test_clean_output_strips_preamble_and_quotes`: `'Here is the enhanced prompt:\n"A red fox."'` gives `"A red fox."`.
  - `test_clean_output_keeps_inner_quotes`: `'A sign reading "OPEN".'` is unchanged.
  - `test_cap_words_trims_at_sentence`: `cap_words("One two. Three four five.", 4) == "One two."`.
  - `test_cap_words_hard_cut_without_sentence_end`: `cap_words("a b c d e", 3) == "a b c"`.
  - `test_cap_words_none_is_noop`.
  - `test_prepend_triggers_normalises_separators`: `prepend_triggers("A fox.", " mabes9sans, ,vito ") == "mabes9sans, vito, A fox."`.
  - `test_prepend_triggers_empty_is_noop`.
  - `test_tokens_include_image_true_and_false`: `{"qwen35": [[({"type": "image"}, 1.0)]]}` gives True, `[[(1, 1.0)]]` gives False.
- [ ] **Step 2: Run them and confirm they fail.** Run `…/python -m pytest tests/unit/tools/prompt_enhancer/test_logic.py -v`.
- [ ] **Step 3: Implement `logic.py`.**
- [ ] **Step 4: Run the tests again.** Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat: add prompt enhancer output helpers"`

### Task 3: The node

**Files:**
- Create: `kikotools/tools/prompt_enhancer/node.py`
- Modify: `kikotools/tools/prompt_enhancer/__init__.py` (export `PromptEnhancerNode`)
- Modify: `kikotools/__init__.py` (import it, register `"KikoPromptEnhancer": PromptEnhancerNode`, display name `"Kiko Prompt Enhancer"`, next to `ModelResolutionPicker` at lines 29/58/97)
- Test: `tests/unit/tools/prompt_enhancer/test_node.py`

**Interfaces:**
- Consumes: everything from Tasks 1 and 2.
- Produces: `class PromptEnhancerNode(ComfyAssetsBaseNode)` with:
  - `RETURN_TYPES = ("STRING", "STRING")`, `RETURN_NAMES = ("prompt", "system_prompt")`, `FUNCTION = "enhance"`.
  - Required inputs: `clip` (`"CLIP"`); `prompt` (multiline STRING); `base_model` (`prompt_names()`, default `default_prompt_name`); `seed` (INT 0..0xffffffffffffffff, `control_after_generate`).
  - Optional inputs: `trigger_words` (STRING, single line, default `""`); `image` (`"IMAGE"`); `temperature` (FLOAT 0.01..2.0, default 0.7, `"advanced": True`); `max_length` (INT 64..8192, default 1024, advanced); `thinking` (BOOLEAN, default False, advanced).
  - `enhance(self, clip, prompt, base_model, seed, trigger_words="", image=None, temperature=0.7, max_length=1024, thinking=False) -> Tuple[str, str]`
  - `@classmethod IS_CHANGED(cls, base_model, **kwargs) -> str`: sha256 of the resolved `SystemPrompt.text + image_text`.
- Flow:
  1. Compose the system prompt: `text` plus `"\n\n" + image_text` when an image is attached and `image_text` is set.
  2. Check that `clip` has `generate` (otherwise the "update ComfyUI" error).
  3. `tokens = clip.tokenize(prompt, image=image, thinking=thinking, system_prompt=system, min_length=1)`.
  4. Run the system prompt check, then the vision check when an image is attached.
  5. `clip.generate(tokens, do_sample=True, …, seed=seed)`, then `clip.decode`.
  6. `split_thinking`, then `clean_output`, then `cap_words`, then `prepend_triggers`.
  7. Return `(final, system)`.

  For the system prompt check, extract the decoded ids the same way core does (`t[0]` for int entries from the first value's lists).

- [ ] **Step 1: Write the failing tests.** Use a `FakeClip` with recording `tokenize`, `generate` and `decode`; `tokenize` returns `{"qwen35": [[(1, 1.0), ...]]}` and `decode` returns scripted strings.
  - `test_registered_in_package`: `"KikoPromptEnhancer"` is in `kikotools.NODE_CLASS_MAPPINGS` and the display name is right.
  - `test_input_types_lists_base_models_and_default`.
  - `test_enhance_passes_system_prompt_and_seed`: `tokenize` gets `system_prompt` = the shipped krea2 text; `generate` gets `seed=7` and `do_sample=True`.
  - `test_trigger_words_not_sent_to_encoder_and_prepended`: `tokenize`'s text doesn't contain `"mabes9sans"`, and the output starts with `"mabes9sans, "`.
  - `test_image_section_appended_only_with_image`: with an override file that has a `## With an image` section and a fake image tensor, the `system_prompt` passed includes the section; without the image it doesn't.
  - `test_image_with_non_vision_encoder_raises`: tokens without an image dict raise `ValueError` matching "did not take the image".
  - `test_ignored_system_prompt_raises`: `decode` of the tokens lacks the system text, so a `ValueError` matches "Update ComfyUI".
  - `test_missing_generate_raises`: a clip without `generate` raises `ValueError` matching "Update ComfyUI".
  - `test_empty_prompt_without_image_raises`: `ValueError` matching "prompt is empty".
  - `test_empty_prompt_with_image_runs`.
  - `test_output_is_cleaned_and_capped`: a scripted `"<think>x</think>Here is the prompt:\n\"One two. Three four.\""` with `max_words: 2` in an override gives `"One two."`.
  - `test_is_changed_follows_file_content`: the value differs after rewriting the override file.
- [ ] **Step 2: Run them and confirm they fail.** Run `…/python -m pytest tests/unit/tools/prompt_enhancer/test_node.py -v`.
- [ ] **Step 3: Implement `node.py`, the `__init__` export and the registration.**
- [ ] **Step 4: Run the full suite.** Run `…/python -m pytest -q`. Expected: all pass, including `tests/unit/test_package_contents.py`.
- [ ] **Step 5: Commit.** `git commit -m "feat: add Kiko Prompt Enhancer node"`

### Task 4: Copy to the user folder (route and context menu)

**Files:**
- Create: `kikotools/tools/prompt_enhancer/routes.py`
- Modify: `kikotools/tools/prompt_enhancer/node.py` (import `routes` so it registers, inside the same `try: import server … except ImportError` pattern as `model_resolution_picker/node.py:121-130`)
- Create: `web/prompt_enhancer.js`
- Test: `tests/unit/tools/prompt_enhancer/test_routes.py`, `tests/js/prompt_enhancer.test.mjs`

**Interfaces:**
- Consumes: `SHIPPED_DIR` and `override_dir()` from Task 1.
- Produces:
  - `copy_to_user(stem: str) -> Path`. Rules:
    - the stem must equal the stem of a file in `SHIPPED_DIR`, an allowlist check (never build a path from raw input);
    - create `override_dir()` if needed;
    - raise `FileExistsError` if the target exists;
    - copy the file;
    - return the target.
  - `async def copy_route(request) -> web.Response`, on `POST /kikotools/prompt_enhancer/copy` with JSON `{"base_model": stem}`:
    - 200 `{"path": str}` on success;
    - 400 `{"error": …}` for an unknown stem;
    - 409 `{"error": "already exists", "path": …}` when the file exists;
    - 500 when there's no user dir.
  - JS: `registerExtension({name: "kikotools.promptEnhancer"})`.
    - For nodes of type `KikoPromptEnhancer`, add the context-menu item "Copy system prompt to user folder".
    - It POSTs the current `base_model` widget value and shows the outcome through `app.extensionManager.toast.add` when available, otherwise `console.info`.
    - The menu-label and response-to-message mapping goes in an exported pure function `copyResultMessage(status, body) -> string` so `node --test` can cover it.

- [ ] **Step 1: Write the failing tests:**
  - Python:
    - `test_copy_creates_override`: the file content equals the shipped file.
    - `test_copy_refuses_existing`: raises `FileExistsError`, and the existing content is untouched.
    - `test_copy_rejects_unknown_and_traversal_stems`: `"../evil"` and `"nope"` raise `ValueError`.
    - `test_route_status_codes`: 200/400/409, called through `asyncio.run` with a stub request whose `json()` returns the body.
  - JS: `copyResultMessage(200, {path:"/u/x.md"})` mentions the path; 409 says it already exists; 400 shows the error.
- [ ] **Step 2: Run them and confirm they fail.** Run `…/python -m pytest tests/unit/tools/prompt_enhancer/test_routes.py -v` and `cd tools/testing && npm test`.
- [ ] **Step 3: Implement `routes.py`, the registration and `web/prompt_enhancer.js`.**
- [ ] **Step 4: Run the tests again.** Expected: both suites pass.
- [ ] **Step 5: Commit.** `git commit -m "feat: copy prompt enhancer system prompts to the user folder"`

### Task 5: The ten shipped system prompts

**Files:**
- Create in `kikotools/tools/prompt_enhancer/system_prompts/`: `sdxl-realism.md`, `illustrious.md`, `anima.md`, `flux2-klein.md`, `z-image.md`, `moss.md`, `krea2.md` (replaces the placeholder), `qwen-image.md`, `wan-t2v.md`, `wan-i2v.md`
- Test: `tests/unit/tools/prompt_enhancer/test_shipped_prompts.py`
- Modify: `tests/unit/test_package_contents.py`: add `"kikotools/tools/prompt_enhancer/system_prompts/krea2.md"` to `KEPT`.

**Sources** (read before writing):
- The research notes at `/home/vito/code/personal/comfy-tools/research/prompt-enhancer-model-styles.md` (per-model form, length, sources).
- The official enhancer prompts linked there:
  - Krea 2: `docs/expansion.txt`;
  - MOSS: `skills/moss-image-prompt-enhancer`;
  - Qwen-Image 2.1: rewriter;
  - Z-Image: `pe.py`;
  - Wan 2.2: `wan/utils/system_prompt.py`;
  - FLUX.2: `system_messages.py`.
- Our uncensored Krea 2 adaptation: `/home/vito/code/personal/comfy-tools/builders/templates/muse_krea2_pe_system.md`.
- The ComfyUI template enhancer prompts used in the installed templates (`build_personal_workflows.py` `template_pe`).

**Values each file must carry** (`max_words` in front matter):

| stem | max_words | must state |
|---|---|---|
| sdxl-realism | 60 | short plain-language lead, then comma-separated photo/lighting tags; no "masterpiece/best quality"; no `BREAK` |
| illustrious | 60 | tags only: `masterpiece, best quality, newest, absurdres, highres`, rating tag, count, character, series, `artist:` tags, general tags; parentheses escaped `\(` `\)` |
| anima | 120 | tag block with `masterpiece, best quality, score_7` + one of `safe/sensitive/nsfw/explicit`, `@artist`, then 2-4 sentences |
| flux2-klein | 120 | subject-first prose, 30-80 words typical; positive phrasing only |
| z-image | 250 | dense objective prose; no metaphors, no "8K/masterpiece"; quoted text exact |
| moss | 500 | English prose caption 200-500 words; booru tags allowed inline |
| krea2 | 150 | one paragraph; faithful; append a "no text" sentence unless text was asked for |
| qwen-image | 520 | one 400-500 word observer paragraph; opening sentence names medium/style/subject/background; positional walk of the frame; lighting sentence; closing sentence |
| wan-t2v | 200 | up to 4 cinematic tags first, then subject, action, background motion; no scene cuts |
| wan-i2v | 100 | body: describe motion and camera; `## With an image` section: do not restate what the image shows |

Every file must also include the shared rules:
- keep the user's subjects, counts, colours and medium;
- keep quoted text exact, inside double quotes;
- keep unusual tokens and names exactly as written;
- turn "avoid X" into a positive statement;
- output only the prompt, no preamble or commentary.

None may contain a content policy (clothing assumptions, NSFW substitution, refusal instructions).

- [ ] **Step 1: Write the failing tests** (parametrized over the ten stems):
  - `test_every_expected_prompt_ships`: the ten stems are all in the shipped dir.
  - `test_max_words_matches_table`.
  - `test_shared_rules_present`: each body contains `exactly as written` and `double quotes`, and mentions `preamble`.
  - `test_wan_i2v_has_image_section`.
  - `test_no_content_policy_phrases`: no body contains, case-insensitively, any of `clothing covers`, `cannot generate`, `refuse`, `inappropriate`, `sanitize`.
- [ ] **Step 2: Run them and confirm they fail.** Run `…/python -m pytest tests/unit/tools/prompt_enhancer/test_shipped_prompts.py -v`.
- [ ] **Step 3: Write the ten files** from the sources and table above, adapting the official prompt where one exists.
- [ ] **Step 4: Run the full suite.** Run `…/python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat: ship prompt enhancer system prompts for ten base models"`

### Task 6: Docs, changelog and a live check

**Files:**
- Modify: `README.md` (one node section: inputs, override folder, the right-click copy, the ComfyUI version floor)
- Modify: `CHANGELOG.md` (an Unreleased entry)

- [ ] **Step 1: Write the README section and the changelog entry.**
- [ ] **Step 2: Run the live check against the running ComfyUI.**
  1. `~/comfy/ComfyUI/custom_nodes/kikotools` is a symlink to `/home/vito/code/personal/ComfyUI-KikoTools`. Repoint it at this worktree for the test.
  2. Restart ComfyUI (tmux pane).
  3. Run the node once per stem with `qwen3.5_9b_w4a8_gptq.safetensors` through `CLIPLoader`, with prompt `"mabes9sans woman in a red raincoat on a rainy Tokyo street at night, neon sign that says OPEN"` and `trigger_words` `"mabes9sans"`.
  4. Run `wan-i2v` once more with an image, using `qwen3vl_4b_fp8_scaled.safetensors`.
  5. Run once with an image on `qwen_3_4b.safetensors` and expect the "did not take the image" error.
  6. Expected: every output starts with `mabes9sans, `, keeps `"OPEN"` in quotes (except illustrious/sdxl, which may tag it), stays within `max_words`, and has no preamble.
  7. Restore the symlink and restart.
- [ ] **Step 3: Record the ten outputs in the PR description** (the test plan section).
- [ ] **Step 4: Commit.** `git commit -m "docs: document Kiko Prompt Enhancer"`
