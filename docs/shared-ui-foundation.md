# ComfyAssets UI foundation

Status: proposed. This document defines the implementation sequence; it does not
claim that the current extensions meet these requirements.

Tracking: [KikoTools #81](https://github.com/ComfyAssets/ComfyUI-KikoTools/issues/81)
and [PromptManager #186](https://github.com/ComfyAssets/ComfyUI_PromptManager/issues/186).

## Problem and intended result

KikoTools extensions independently construct controls, styles, windows, and host
integration. The Local Image Loader combines these concerns in
`web/kiko_local_image_loader.js`. PromptManager has useful `--pm-*` theme tokens,
but its pages and dialogs have different behavior and lifecycle requirements.

Build an original ComfyAssets foundation so both projects can offer reusable
controls, consistent editor layouts, shared settings/help/window behavior, and
tested Classic/Nodes 2.0 compatibility. Both projects are one toolset and must
look identical. Preserve existing node interfaces, workflows, routes, and features.

Architecture inspiration: [Pixaroma's editor framework](https://github.com/pixaroma/ComfyUI-Pixaroma/blob/78745d0860649d796032265d50711601e70f748e/js/framework/index.mjs)
and [shared infrastructure](https://github.com/pixaroma/ComfyUI-Pixaroma/blob/78745d0860649d796032265d50711601e70f748e/js/shared/index.mjs).
Credit this inspiration in the shipped documentation. Write our own implementation
and visual design; do not copy or vendor Pixaroma code, assets, or styles.

## Boundaries

| Layer | Owns | Must remain independent of |
| --- | --- | --- |
| Controls | Buttons, fields, selections, accessible labels and state | Node names, HTTP routes, renderer internals |
| Layout | Title, toolbar, workspace, optional sidebar and status slots | Gallery fetching and workflow serialization |
| Services | Settings, help, floating windows, cleanup scopes | Product colors and node-specific data |
| ComfyUI adapter | DOM widget attachment, renderer changes, zoom/resize, graph edits | Product layouts and themes |
| Product controllers | API calls, selection, commands, existing persistence | Renderer-specific implementation details |
| Theme | Scoped tokens, typography, spacing, colors, focus and interaction states | Business behavior |

Use native DOM modules and semantic controls for the pilot. Introduce no frontend
framework just for this work. Controls receive values and callbacks; controllers
retain state. Mounting returns an idempotent disposer. Disposal cancels pending
requests and timers, disconnects observers, removes listeners, and closes owned
windows. Late asynchronous responses cannot update a removed or superseded view.

Keep ComfyUI imports behind the host adapter. Detect supported capabilities and
subscribe to host changes where available. Any fallback watcher belongs in the
adapter, has one explicit owner, and stops on disposal. Preserve existing host
hooks and their return values. Do not scatter renderer checks through controls.

## Independent installation and shared source

During the pilot, keep the original source in KikoTools under `web/ui/`, with
product controllers outside that directory. Avoid a premature published package
or a second implementation in PromptManager.

Before PromptManager adopts controls, extract the proven core into one versioned
ComfyAssets source package. Use it as a pinned build-time dependency. Commit the
generated browser distribution, license, version, source revision, and integrity
metadata in each consumer so ordinary git/Manager installations require neither
npm nor a second custom node pack. A documented update command must regenerate
the distribution; CI must reject hand-edited or stale output. Package hosting
and release automation are decisions for that extraction PR.

Each consumer uses relative imports and its own root namespace. Avoid global
custom-element registration and mutable page-wide singletons in the pilot.
Settings and storage keys include a product identifier. Styles remain below the
consumer root. Floating windows inherit that consumer's tokens even when attached
to the document body. Different bundled versions must coexist without selecting
whichever version happened to load first. Test this explicitly during extraction.

## Agreed styling and theme direction

Both projects share exactly the same identity: controls, typography, spacing,
colors and interaction states. Follow ComfyUI's light/dark mode with our own
styling. Use ComfyUI-style blue for the primary accent and a strong, readable red
for errors and destructive actions. Pixaroma's orange is not our accent.

The maintainer's screenshot references establish compact, uniform buttons,
pill switches, segmented selections, structured editable rows, and correct
resizing. Existing styles are migration context, not the target. Define shared
semantic tokens and present the [interactive pilot mockup](ui-preview/README.md)
for review before production migration. Keep behavioral APIs independent of theme.

Follow host light/dark changes while mounted. Standalone PromptManager pages
need an explicit theme/settings bridge because a separate
page does not inherit its CSS variables. Any light/dark or accent choices must
preserve readable text and focus indicators.

Review the pilot in light and dark themes, at narrow and wide node sizes, and
with keyboard focus visible before extending the style system to other nodes.
Record screenshots and concrete contrast measurements; do not treat screenshot
existence as proof of accessibility. No global resets or host-wide style overrides.

## Pilot: Local Image Loader

Keep browsing, autocomplete, saved paths, sorting, hidden-folder filtering,
pagination, refresh, image/video/audio selection, and existing API error handling.
Keep node names, inputs/outputs, widget serialization, and persisted settings
compatible. Characterize existing saved workflows before changing implementation.

First extract the shell, button, select, text field, checkbox, and status controls
actually used by this node. Add sliders and number fields when a second editor
needs them. Windows/help/settings services follow after the pilot; do not add
unused abstractions to satisfy a component checklist.

## Acceptance and test strategy

Use TDD for each behavioral slice: record a failing regression or new contract
test, implement the minimum change, then run affected suites and required gates.
Characterization tests should pass before refactoring. Never weaken existing
coverage thresholds. Extend source discovery and coverage to nested `web/ui/`
modules before introducing them; the current collector only includes `web/*.js`.

| Boundary | Required evidence |
| --- | --- |
| Controls/services | Unit tests for state, callbacks, disposal, settings isolation and repeat mount/unmount |
| Product workflows | Existing browser fixture tests plus request races, errors and preserved selection/settings |
| Real host | Actual ComfyUI frontend, graph, settings, widgets and workflow serialization; no substituted host objects |
| Visual/keyboard | Theme screenshots, keyboard operation, visible focus, accessible names and measured contrast |
| Distribution | Both packs separately and together, with matching and different UI package versions |

The real-host harness must pin ComfyUI and frontend versions and record them in
test artifacts. Select and document a baseline that actually supports both
renderers before claiming compatibility. Test initial Classic and Nodes 2.0,
switching both ways without reload, zoom/pan/resize, node delete/recreate,
save/reload of an existing workflow, and duplicate-node behavior.

Opening or closing a view, changing theme, and moving a floating window must not
create graph edits. Committed node value changes must use the host's normal edit
path and participate in undo/redo. Assert serialized values and history behavior;
do not use canvas redraw as evidence of correct graph persistence.

Run the pinned baseline as a PR check once reproducible. Keep the existing fast
fixtures and cross-browser checks. Run a separately pinned newer-host matrix on
a schedule to detect upstream changes without silently changing PR dependencies.
Missing renderer support must fail or be reported as unsupported, never silently
skip the renderer and report compatibility. Model inference and GPU execution
are outside this UI suite; startup and UI interaction should use disposable data.

## Delivery sequence

1. **Proposal:** agree on these boundaries, pilot behavior, and test evidence.
2. **Host harness:** add reproducible real-ComfyUI tests for the existing loader;
   report any existing failures separately before the refactor.
3. **Pilot:** make nested source coverage exhaustive; add tokens, minimal controls,
   shell, adapter and loader migration in reviewable TDD slices. Include visual
   evidence and preserve the existing suites.
4. **Shared behavior:** migrate the Kiko image viewer; extract settings/help/window
   services from demonstrated needs and test cleanup, persistence and keyboard use.
5. **Second consumer:** extract and version the core, add reproducibility checks,
   then migrate one PromptManager dialog and its theme bridge. Prove standalone
   and combined installation before wider adoption.
6. **Incremental adoption:** migrate remaining editors individually. Remove old
   code only after replacement behavior is covered; document package updates and
   compatibility support.

Each PR links its tracked issue, includes validation commands/results, and states
which real-host and visual checks were performed. Keep runtime changes out of the
proposal PR. No backend or workflow schema change is planned for the UI pilot.
