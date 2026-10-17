# Testing and merge confidence

Use regression tests before fixing a bug. Confirm that the test fails on the
original implementation, then run the relevant suites after the fix.

## What runs

| Layer | Real components | Replaced boundaries |
| --- | --- | --- |
| Python | Tool logic, tensors, image files, API validation | ComfyUI services and external models where needed |
| JavaScript | Production extension hooks and callback behavior | Minimal host objects; controlled timers for focused regressions |
| Browser fixtures | All shipped extension imports and lifecycle registration; real plugin startup, HTTP routes, PNG thumbnails, selection persistence, and image loading | ComfyUI graph/widgets/settings/event interfaces and its saved-image serving endpoint |
| Real ComfyUI | Pinned server/frontend, LiteGraph, native menus, DOM widgets, initial renderers, switching and workflow serialization | Disposable media routes; simulated execution/progress events; model/service boundaries |

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

The fixture suite covers plugin behavior without a real ComfyUI frontend. The
separate required real-host job covers the integration described below. GPU/model
execution, cloud inference and model downloads still need targeted checks when
changed; the compatibility suite does not queue workflows or download weights.
Type checking and security jobs retain their existing advisory behavior.

## Pinned real-ComfyUI compatibility

The required **real ComfyUI compatibility** CI job provisions a CPU-only host.
`tools/testing/comfyui-runtime.json` pins upstream commit
`e8665ca8e4089ab917567cdb491308e1397663d4` (server 0.39.0), frontend 1.55.14,
Python 3.12 and the CPU PyTorch/torchvision pair. The launcher rejects a different
revision or modified tracked upstream files. The suite verifies server/frontend
versions and attaches them to each test's report.

Two projects, `classic-start` and `nodes2-start`, select the renderer during
startup, before creating nodes. Both run the complete suite, including live
renderer switching, zoom/resize, palette changes, workflow save/reload and
cleanup. Test-local settings start from a blank workspace and skip first-run
onboarding. They do not change the server's saved preferences.

The migrated controls covered are Local Image Loader, Save Image, Seed History,
Workflow Timer and its color picker, both dimension swap nodes, Node Dimensions,
Display Text/Any, Embedding Autocomplete/settings/tag imports, Custom Colors and
Follow Execution. Native canvas menus are opened with actual right clicks.
Execution/progress events are simulated; generation is never queued.

### Managed local host

Use a separate clean checkout of the pinned ComfyUI commit and a Python 3.12
environment containing its `requirements.txt` and this repository's
`requirements-dev.txt`. Install the CPU torch/torchvision versions from the
runtime manifest first, using the official CPU wheel index. The CI workflow in
`.github/workflows/tests.yml` contains the full provisioning recipe.

```sh
KIKO_COMFY_ROOT=/path/to/pinned/ComfyUI \
KIKO_TEST_PYTHON=/path/to/cpu-venv/bin/python \
  npm run --prefix tools/testing test:comfyui
```

Playwright owns this host on `127.0.0.1:8189` and a fixture server on port 8771.
The launcher creates a temporary base/user/model directory, installs only a
symlink to the current KikoTools checkout, disables other custom nodes and
partner services, and uses an in-memory database. It removes owned state after
normal shutdown, startup failure or process termination. Existing installations
and model folders are not used. An occupied port fails instead of reusing an
unrelated server.

### Existing local host

An opt-in mode still supports an already running host with the same pinned
versions:

```sh
KIKO_COMFY_URL=http://127.0.0.1:8188/ \
  npm run --prefix tools/testing test:comfyui
```

Only loopback URLs are accepted. A separate browser context serves the current
checkout's extensions. Media requests use real plugin Python routes with
disposable fixture data. Other HTTP writes are intercepted, preserving server
settings, saved workflows and selections. This mode does not start or stop the
existing server.

### Reports and pin updates

CI retains `real-comfyui-reports` for 14 days, including server startup logs at
`tools/testing/test-results/comfyui-host.log`, browser traces, screenshots and
version attachments. Startup logs survive failure. Reviewed captures copied to
[docs/screenshots](docs/screenshots/README.md) are committed separately from
throwaway test artifacts.

To update the host, review and change the runtime manifest, provision the new
checkout/dependencies, and run both startup projects before merging. A version
assertion update alone is not compatibility validation. Cross-pack installation
and shared-source version compatibility remain tracked in #81.

## Required merge checks

The manifest in `.github/branch-protection.json` requires all Python matrix jobs,
Python coverage, frontend syntax, frontend workflows/coverage, real ComfyUI
compatibility, and the existing
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
