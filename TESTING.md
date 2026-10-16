# Testing and merge confidence

Use regression tests before fixing a bug. Confirm that the test fails on the
original implementation, then run the relevant suites after the fix.

## What runs

| Layer | Real components | Replaced boundaries |
| --- | --- | --- |
| Python | Tool logic, tensors, image files, API validation | ComfyUI services and external models where needed |
| JavaScript | Production extension hooks and callback behavior | Minimal host objects; controlled timers for focused regressions |
| Browser | All shipped extension imports and lifecycle registration; real plugin startup, HTTP routes, PNG thumbnails, selection persistence, and image loading | ComfyUI graph/widgets/settings/event interfaces and its saved-image serving endpoint |

Browser workflows cover swaps, local image browsing/selection, pagination,
sorting, hidden folders, directory autocomplete, saved paths,
denied paths and network recovery, display output, seed persistence/cleanup, and
workflow timing, autocomplete insertion, and saved-image previews. They run in Chromium, Firefox, WebKit, and touch Chromium.
The harness binds to localhost and writes configuration, selections, and fixture
images only inside a temporary directory. External browser requests fail tests;
custom-word downloads are disabled in the fixture. No credentials, model
weights, running ComfyUI, or GPU are required.

## Run locally

Use Python 3.10–3.13 and Node.js 24. Install the CPU PyTorch wheel on Linux if you
do not need CUDA, then install the development dependencies:

```sh
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-dev.txt
python -m pytest tests
python -m pytest tests --cov=kikotools --cov-report=term-missing
npm ci --prefix tools/testing --ignore-scripts
npx --prefix tools/testing playwright install --with-deps chromium firefox webkit
npm test --prefix tools/testing
npm run --prefix tools/testing test:coverage
npm run --prefix tools/testing test:browser -- --project firefox --project webkit
```

`make test` runs the full pytest suite and propagates failures. `make coverage`,
`make frontend-test`, `make browser-test`, and `make frontend-coverage` provide
shortcuts. The Python Make targets use the existing virtual-environment setup.
Install local commit and push hooks with `pre-commit install --hook-type
pre-commit --hook-type pre-push`. The push hooks run Python and JavaScript
regressions; CI additionally runs all browser workflows and coverage gates.
For a quick browser check, use `test:browser -- --project chromium`.
`KIKO_TEST_PYTHON` selects a Python executable with the development dependencies;
`KIKO_TEST_PORT` changes the default port 8766. Servers are never reused.
Unsupported Linux distributions may lack WebKit libraries; Ubuntu CI validates
all engines.

## Coverage and diagnosis

Python CI checks all twelve Python/OS combinations and enforces 85% combined
statement/branch coverage. Every production `web/*.js` file appears in frontend
coverage, including code without behavioral coverage. V8 unit coverage and
Chromium desktop/touch coverage are merged through c8. The committed per-file
floors are an honest starting point, not a claim that every feature is tested.

`npm run --prefix tools/testing coverage:update` reruns the suites and raises
floors with two percentage points of runtime allowance. It cannot lower existing
floors; new source files require 80% line coverage when added with this command.
Missing measurements, missing baselines, and per-file regressions fail CI.

CI artifacts include Python JUnit results, Python HTML/XML coverage, and
`frontend-test-reports` with frontend HTML coverage and browser failure traces
and screenshots. Open traces using Playwright's `show-trace` command. Local
frontend coverage is at `coverage/js/index.html`.

Real ComfyUI/LiteGraph compatibility, GPU execution, cloud inference, network
model downloads, and visual design still need targeted live checks when changed.
The browser host is a test double; these workflows do not run the real ComfyUI
frontend or certify every node's UI. Type checking and security jobs retain their
existing advisory behavior.

### Actual ComfyUI frontend smoke test

The Local Image Loader also has an opt-in suite using the actual ComfyUI frontend,
graph, DOM widgets, renderer switch and palette settings. Start a local ComfyUI
0.39.0 with frontend 1.55.14 and KikoTools installed, then run:

```sh
KIKO_COMFY_URL=http://127.0.0.1:8188/ node \
  tools/testing/node_modules/@playwright/test/cli.js test \
  --config tools/testing/comfyui.config.mjs
```

The suite requires those exact versions and records them in its artifacts. It
serves the current checkout's extensions to a separate browser context and loads
only KikoTools extensions. Media requests use the existing real Python routes
with disposable fixture data on port 8771. Other HTTP writes are intercepted,
so user settings, saved workflows and selections are not written to the live
server. It does not execute a workflow or download models.

Checks cover Classic/Nodes 2.0/live switching, theme changes, workflow save/reload
and removal for the loader. Save Image additionally checks real image output,
window close/reopen through the node control across renderer switches, theme
changes, exclusion of the launcher from serialized values and owner removal.
Its `/view` requests also use disposable fixture output rather than live files.
Seed History checks keyboard-operable rows through renderer switches, list growth
and scrolling on resize, palettes, saved history/node dimensions, serialization
and polling cleanup on removal.
Screenshots/traces appear in
`tools/testing/test-results/comfyui/`. This opt-in smoke suite is separate from
the required fixture CI job; fully provisioned, pinned ComfyUI CI and testing
alongside other node packs remain follow-up work in issue #81.

## Required merge checks

The manifest in `.github/branch-protection.json` requires all Python matrix jobs,
Python coverage, frontend syntax, frontend workflows/coverage, and the existing
`code-quality` job (including Black and fatal lint checks). Administrators follow
the same checks and branches must be current with main. No extra human approval
is required. Workflows run on every pull request without path filters.

After the checks pass, an administrator applies and verifies the manifest:

```sh
gh api --method PUT repos/ComfyAssets/ComfyUI-KikoTools/branches/main/protection \
  --input .github/branch-protection.json
gh api repos/ComfyAssets/ComfyUI-KikoTools/branches/main/protection/required_status_checks
```

Keep the manifest synchronized with job names when changing CI.
