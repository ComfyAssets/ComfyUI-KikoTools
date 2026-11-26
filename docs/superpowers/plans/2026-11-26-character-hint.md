# Character Hint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Character Hint (Female) and Character Hint (Male) nodes and a `character_hint` input on the H3 Reference Prompter.

**Architecture:** New tool `kikotools/tools/character_hint/`: `options.py` (tables, already written and committed), `logic.py` (pure hint builder), `node.py` (two nodes). The prompter reads the hint as plain text: `logic.py` gains three pure helpers, `instructions.py` a hint block, `node.py` the input and the age rule.

**Tech Stack:** Python 3.12, ComfyUI node API, pytest.

**Spec:** `docs/superpowers/specs/2026-11-26-character-hint-design.md`

## Global Constraints

- Category `🫶 ComfyAssets/🧠 Prompts`, base class `ComfyAssetsBaseNode`, relative imports only inside `kikotools` (a guard test bans absolute ones).
- Node ids `KikoCharacterHintFemale`, `KikoCharacterHintMale`; display names `Character Hint (Female)`, `Character Hint (Male)`.
- Do not change any table in `options.py`.
- Test env: `V=/tmp/claude-1000/-home-vito-code-personal-ComfyUI-KikoTools/f79925f2-d12d-4383-ad2e-85d80c922cf7/scratchpad/venv`. Run `$V/bin/python -m pytest <path> -p no:cacheprovider -q`; full suite adds `--cov=kikotools` (floor 85%); `$V/bin/black --check .`; `$V/bin/flake8 <changed dirs>`.
- Commits: conventional type with scope, imperative subject, bullet body. NEVER add any Claude or AI attribution, session link or Co-Authored-By line.
- `NUDE_MIN_AGE` and the picture age check must not change.

## Review Focus

- A hint whose age is under 18 or missing must not pass a nude draft that has no character picture.
- A nude draft with a character picture that fails the estimate stays refused even when the hint says "aged 30".
- A youth word in the hint refuses a nude draft.
- "Unclothed detail:" must not reach the writer for a clothed item.
- An empty or whitespace hint behaves exactly as no hint.

---

### Task 1: Character Hint tool

**Files:**
- Create: `kikotools/tools/character_hint/__init__.py`, `logic.py`, `node.py`
- Modify: `kikotools/__init__.py` (import, both mappings, both display names)
- Test: `tests/unit/tools/character_hint/__init__.py`, `test_options.py`, `test_logic.py`, `test_node.py`

**Interfaces:**
- Consumes: `options.py` tables and `UNSET`, `MIN_AGE`, `MAX_AGE`, `DEFAULT_AGE`.
- Produces:
  - `logic.FEMALE = "woman"`, `logic.MALE = "man"`.
  - `logic.build_hint(gender: str, age: int, values: Dict[str, str], extra: str = "") -> str`. `values` maps field name to the chosen label; `UNSET`, missing and unknown-to-this-gender fields are skipped; an unknown label raises `ValueError` naming the field. Text layout exactly as the spec's "The hint text" section. Part order: lead, Body (`body_type`, `breast_size`, `butt_size`), Face (`face_shape`, `eye_color`, `eye_shape`, `eye_detail`, `nose`, `lip_shape`, lip colour when no makeup, `facial_hair`, `dimples`), Makeup, Hair (`hair_color`, `hair_length`, `hair_style`, `bangs`), Skin (`skin_tone`, `tan`, `freckles`, `acne`, `beauty_mark`), Tattoos, Expression, Unclothed detail (`nipples`, `areola`), Extra.
  - `logic.fields(gender) -> Dict[str, Table-like]`: ordered field name to its label list for that gender (female uses `FEMALE_BODY`, `FEMALE_LIP_SHAPE`, `FEMALE_HAIR_STYLE`; male uses `MALE_BODY`, `MALE_LIP_SHAPE`, `MALE_HAIR_STYLE`; field lists per the spec's "Fields").
  - `CharacterHintFemaleNode`, `CharacterHintMaleNode`: required `age` (INT, default 25, min 18, max 90, `"display": "slider"`), then one combo per field (`[UNSET, *labels]`, default `UNSET`), optional `extra` (STRING multiline, default ""). `RETURN_TYPES = ("STRING",)`, `RETURN_NAMES = ("hint",)`, `FUNCTION = "build"`; `build(self, age, extra="", **values)` returns `(build_hint(...),)`.

- [ ] **Step 1: Write failing tests.**
  - `test_options.py`: every table non-empty; no label equals `UNSET`; no phrase empty; no `MAKEUP` look or lips ends with punctuation; the word "bum" appears nowhere; "Flat" is not in `BREAST_SIZE`.
  - `test_logic.py` with these exact assertions:
    - `build_hint("woman", 25, {})` == `"The character is an adult woman aged 25."`
    - `build_hint("man", 40, {"heritage": "Japanese"})` == `"The character is an adult Japanese man aged 40."`
    - `build_hint("woman", 30, {"body_type": "Curvy", "breast_size": "Large", "butt_size": "Large"})` ends with `"Body: a curvy body, large breasts, a large butt."`
    - makeup alone: contains `"Makeup: wearing soft glam makeup, smoothly blended taupe eyeshadow, softly defined eyeliner, fluttery lashes, warm blush, and satin nude lips."`
    - makeup "Soft glam" + lip colour "Berry": contains `"warm blush, and berry lips."` and not `"satin nude lips"`.
    - lip colour "Berry" without makeup: Face part contains `"berry lips"` and there is no `"Makeup:"`.
    - male with `breast_size`, `makeup`, `nipples` given: none of them appear; `facial_hair: "Goatee"` gives `"Face: a goatee."`
    - `nipples: "Pierced", areola: "Dark"` gives `"Unclothed detail: pierced nipples, dark areolas."`
    - `extra="  has a scar on the chin "` ends with `"Extra: has a scar on the chin."`; extra already ending in "." is not doubled; blank extra adds nothing.
    - unknown label raises `ValueError` matching the field name; unknown gender raises `ValueError`.
    - parts appear in the order listed above (one test with a value in every part).
  - `test_node.py`: `INPUT_TYPES` of each node has `age` first with min 18; every combo's first choice and default is `UNSET`; female has `breast_size`, male does not; male has `facial_hair`; `build` returns a 1-tuple equal to `build_hint` for the same values; both ids and display names are registered in `kikotools.NODE_CLASS_MAPPINGS` / `NODE_DISPLAY_NAME_MAPPINGS`.
- [ ] **Step 2: Run** the tool's tests — FAIL on import.
- [ ] **Step 3: Implement** `logic.py`, `node.py`, `__init__.py` (export both nodes), register in `kikotools/__init__.py`.
- [ ] **Step 4: Run** the tool's tests, the full suite with coverage, black and flake8 — all pass.
- [ ] **Step 5: Commit** `feat(character_hint): add Character Hint nodes` (include `options.py`, which is untracked).

### Task 2: Prompter takes a character hint

**Files:**
- Modify: `kikotools/tools/h3_reference_prompter/logic.py`, `instructions.py`, `node.py`
- Test: `tests/unit/tools/h3_reference_prompter/test_logic.py`, `test_instructions.py`, `test_node.py`

**Interfaces:**
- Consumes: hint text as built in Task 1 (lead sentence contains "aged N"; an optional sentence starts with "Unclothed detail:").
- Produces:
  - `logic.HINT_MIN_AGE = 18`.
  - `logic.parse_hint_age(hint: Optional[str]) -> Optional[int]`: first `\baged (\d{1,3})\b` (case-insensitive) or None.
  - `logic.strip_unclothed(hint: str) -> str`: removes the sentence that starts with "Unclothed detail:" up to and including its full stop, tidies spaces.
  - `logic.check_adult(characters, draft, hint="") -> Tuple[int, int]`: youth-word check on draft, then on hint (message "The character hint uses the word '…'"). With characters: unchanged estimate check, then when `parse_hint_age(hint)` is at least `HINT_MIN_AGE` return `(age, age)`, else the estimate. Without characters: hint age at least `HINT_MIN_AGE` returns `(age, age)`; otherwise refuse with "No character picture is connected and the character hint gives no adult age."
  - `instructions.hint_block(hint: str) -> str` and `writer_user(lead, notes, adult=None, hint="")`: a non-blank hint adds the block after the notes block and before the nude/adult block. The block says: these traits come from the user; where they disagree with the character notes the hint wins; work each trait into the subject sentences in your own words, never as a list; do not copy labels such as "Body:"; then the hint. `writer_user` passes `strip_unclothed(hint)` unless `is_nude(lead, connected)`.
  - `nude_block(age)` / `adult_block(age)`: when `low == high` write "aged N" instead of "aged N to N" and skip the "in her twenties" alternative. When a hint is present its stated gender decides: add to both blocks' callers nothing new; the existing "if the character notes say the person is a man" sentence becomes "if the character notes or the character hint say the person is a man".
  - Node: optional input `character_hint` `("STRING", {"forceInput": True, "tooltip": "Traits from a Character Hint node; they win over the character picture"})`, placed after the image inputs; `write(..., character_hint: Optional[List[str]] = None)`; paired per item through `pair_items` under the key `hint` (None or blank becomes ""); `_adult_range` passes the item's hint to `check_adult`; `_write_one` / `_write_batch` pass it to `writer_user`.

- [ ] **Step 1: Write failing tests**, including each Review Focus line:
  - `parse_hint_age`: "…woman aged 25." → 25; "Aged 30" → 30; "ages well" → None; None → None.
  - `strip_unclothed("A. Unclothed detail: x, y. Extra: z.")` == `"A. Extra: z."`; text without it is returned unchanged.
  - `check_adult([], "nude", "The character is an adult woman aged 25.")` == `(25, 25)`; aged 17 and no age both raise `ValueError`; a hint with "teen" raises; characters whose notes estimate "15 to 19 years" raise even with hint "aged 30"; characters estimating "30 to 45" with hint "aged 25" return `(25, 25)`, and with no hint `(30, 45)`.
  - `writer_user`: hint text appears after the notes; blank hint gives output identical to no hint; clothed item drops "Unclothed detail:" and keeps the rest; nude item (draft says nude, no outfit note) keeps it.
  - `nude_block((25, 25))` contains "aged 25" and neither "25 to 25" nor "twenties".
  - Node: `INPUT_TYPES()["optional"]["character_hint"]` is a forced STRING input; a nude draft with no images but hint "…aged 25." reaches the writer (stub the generator as the existing node tests do) and the writer message contains the hint; a list of two hints pairs with two prompts; hint list of a different length than prompts raises the existing length error.
- [ ] **Step 2: Run** — new tests FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** prompter tests, full suite with coverage, black, flake8 — pass.
- [ ] **Step 5: Commit** `feat(h3_reference_prompter): take a character hint`.

### Task 3: Docs

**Files:**
- Create: `examples/documentation/character_hint.md`
- Modify: `README.md` (short section next to the H3 Reference Prompter one, and the node list if there is one), `examples/documentation/h3_reference_prompter.md` (new "Character hint" section, and the nude-mode section's age rule), `CHANGELOG.md` (`## Unreleased` → `### Added`)

- [ ] **Step 1: Write** the docs from the spec: what the nodes do, the field list, how the hint and the picture combine (hint wins), the age rule in plain words, that the options were tested against MiniMax H3 Image, and that "Unclothed detail" is used only for nude drafts. Plain language, short sentences, no marketing.
- [ ] **Step 2: Run** any docs or README tests in the suite (`pytest tests -k "readme or docs or changelog"`), and black.
- [ ] **Step 3: Commit** `docs(character_hint): document the Character Hint nodes`.
