# Repository Guidelines

## Project Structure & Module Organization

`kikotools/tools/<tool>/logic.py` contains reusable logic; `node.py` defines the
ComfyUI node. Shared classes live in `kikotools/base/`. Register nodes in
`kikotools/__init__.py`; the root `__init__.py` exposes the plugin and API routes.
`web/` contains browser extensions. Tests live in `tests/unit/`, `tests/js/`, and
`tests/browser/`. Examples are in `examples/`.

## Development Commands

Install Python dependencies with `python -m pip install -r requirements-dev.txt`.
Run `python -m pytest tests` or `make test` for the complete Python suite.
Use `python -m pytest tests --cov=kikotools` for the 85% statement/branch gate.
Format with `black .`; use `flake8 .` for lint findings.

Frontend tooling needs Node.js 24 and `npm ci --prefix tools/testing
--ignore-scripts`. Run `npm test --prefix tools/testing` for JavaScript tests,
`npm run --prefix tools/testing test:coverage` for coverage and Chromium workflows,
and `npm run --prefix tools/testing test:browser` for all browser projects.
See `TESTING.md` for browser installation, environment overrides, and artifacts.

## Coding Style & Naming

Use four-space Python indentation and Black's 88-character formatting.
Use `snake_case` for Python functions/modules, `PascalCase` for classes, and
`UPPER_CASE` for constants. Keep node interfaces separate from logic. Preserve
existing ComfyUI lifecycle hooks when extending widgets and clean up timers,
listeners, and observers when nodes are removed.

## Testing Guidelines

Write regression tests first and verify failure before implementing fixes.
Name Python tests `test_*.py` and JavaScript tests `*.test.mjs`; put browser
workflows in `tests/browser/*.spec.mjs`. Test behavior and persistence, including
failure recovery. Keep fixtures disposable and external services mocked.
Never lower coverage floors to make a change pass.

## Commits & Pull Requests

Use Conventional Commits, such as `fix(local_image_loader): preserve error
status`. Link the tracked issue, describe observable behavior, and report the
commands and results used for validation. Include screenshots for visual changes.
Required checks must pass before merging. Keep credentials and runtime files out
of commits; restart ComfyUI after installing Python changes.
