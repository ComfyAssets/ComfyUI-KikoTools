# KikoTools UI migration

KikoTools' custom controls use the original ComfyAssets foundation in `web/ui/`.
They share blue primary actions, red destructive actions, keyboard controls and
ComfyUI-following dark/light colors. Layouts resize with the available space.
Pixaroma's toolkit inspired the organization; its code/assets are not vendored.

| Interface | Shared implementation | Retained examples |
| --- | --- | --- |
| Local Image Loader | `views/image-browser.js`, controls and scoped controller | [Loader](screenshots/live-image-loader/) |
| Save Image | Floating window, batch selection and responsive preview | [Viewer](screenshots/save-image-viewer/) |
| Seed History | `views/seed-history.js`, scoped watcher and disclosure | [History](screenshots/seed-history/) |
| Workflow Timer | Shared clock, controls and color picker | [Timer](screenshots/workflow-timer/) |
| Width Height / Empty Latent swaps | `ui/dimension-swap.js`, `ui/dimensions.js` | [Swaps](screenshots/dimension-swap/) |
| Node Dimensions | `views/node-dimensions.js`, native dialog shell | [Dimensions](screenshots/node-dimensions/) |
| Display Text / Any | Shared output view, controller and widget adapter | [Output](screenshots/display-output/) |
| Embedding Autocomplete | Shared suggestions/settings, worker parsing and cache | [Autocomplete](screenshots/embedding-autocomplete/) |
| Custom Colors | Shared color picker, native node/group menus | [Colors](screenshots/custom-colors/) |
| Follow Execution | Native host menus/settings, idempotent execution listeners | [Menus](screenshots/follow-execution/) |

`createScope()` owns listeners, observers and delayed work. Node removal preserves
previous lifecycle hooks while disposing owned resources. Host-specific text
widget handling lives in `ui/text-widget-adapter.js`; floating windows and native
dialogs manage their own focus and cleanup. See [module notes](../web/ui/README.md).

Pure Python nodes continue using ComfyUI's native widgets. Gemini Prompt
Engineer retains its legacy UI for saved workflows under the agreed deprecation;
its UI migration was cancelled.

The [test guide](../TESTING.md) distinguishes fixture coverage, real-host
compatibility and model/GPU behavior. Required real-host CI uses a reviewed
upstream commit, fresh Classic/Nodes 2.0 starts and disposable CPU-only state.

## Remaining shared-toolset work

Before PromptManager adopts the foundation, extract a versioned shared source
package with reproducible browser artifacts. Then test both node packs alone and
together, including different bundled foundation versions, isolated settings
and identical styling. These requirements remain open in issue #81; the KikoTools
migration does not establish cross-pack compatibility by itself.

The approved design-preview draft [#82](https://github.com/ComfyAssets/ComfyUI-KikoTools/pull/82)
records the original direction. This inventory describes the shipped interfaces
and supersedes that draft's implementation sequence.
