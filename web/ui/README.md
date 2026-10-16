# ComfyAssets controls: first production consumer

The Local Image Loader uses `core.js` and `controls.css` for the approved shared
blue controls and host-following light/dark themes. `../views/image-browser.js`
composes these primitives; `../kiko_local_image_loader.js` retains the controller,
API calls and existing selection persistence.

Grid thumbnails default to 224 px with square preview areas and preserve the
entire image. The Thumbnail size slider adjusts the grid from 128–384 px. A full
page scrolls within the gallery instead of compressing the rows to fit the node.
Thumbnail size is a per-node view setting for the current session.
New nodes start at 800 × 900 to leave room for the larger previews. Existing
workflows retain their saved node dimensions and can be resized normally.

`createScope()` owns listeners, delayed work and a fetch cancellation signal.
Dispose it on node removal. `mountTheme()` observes host palette changes and
removes its observers/listeners with that scope. The module has no ComfyUI imports;
the extension passes the host settings interface explicitly.

Both projects will use the same theme and controls. This is the first consumer,
not a published package yet. Keep routes, node definitions and business state out
of `ui/`; add abstractions only as demonstrated by the next consumer.

Architecture and control organization were inspired by
[Pixaroma](https://github.com/pixaroma/ComfyUI-Pixaroma). This implementation and
styling are original; none of his toolkit code or assets are vendored.

## Floating windows

`floating-window.js` owns pointer capture, keyboard movement/resizing, viewport
bounds and observer cleanup. `window.css` consumes the same control tokens as the
loader. Kiko Save Image is its first consumer; the controller has no node, API or
gallery dependencies.

Drag the title or bottom-right resize handle. Focus either handle and use arrow
keys (Shift for larger steps). Escape closes the focused window. The viewer stays
nonmodal so the canvas remains usable. Window position and size survive new
results and minimize/reopen within the session; they are not written into a
workflow or persisted across browser reloads.

The owning node controls removal. Another node may take over the shared viewer,
but deleting the previous owner must not remove it. Closing or deleting a viewer,
or replacing its results, cancels delayed bulk-open actions.

## Seed History

`../views/seed-history.js` composes the shared buttons and theme tokens. The
extension keeps seed generation, callbacks, history and workflow persistence.
History entries are native buttons: Tab to an entry and press Enter or Space to
reuse its seed. The selected entry has a visible outline and pressed state.

The list fills the available node space and scrolls as needed. It automatically
hides after 2.5 seconds of inactivity, except while hovered or keyboard-focused.
Use Show history / Hide history to control it explicitly. Feedback appears in
the node's status area instead of temporary overlays on the canvas.

The existing browser storage key and serialized `seedHistory` field are retained.
Up to ten unique valid seeds are kept, including zero; malformed entries are
ignored. Browser storage failures leave in-memory/workflow history usable.
New nodes start at 320 × 420; saved workflows retain their node dimensions.
Node removal disposes theme observers, event listeners, polling and setup/hide
timers through `createScope()`.

## Workflow Timer and color controls

Workflow Timer uses the shared shell and theme without overriding node title or
background colors. New nodes start at 340 × 180; saved dimensions and the
`elapsed_time_str` property are restored with the workflow. Serialization saves
a plain snapshot instead of a reference to live node properties.

`workflow-clock.js` coordinates one polling interval for all visible timer
nodes. New timers join the current execution; the interval stops when the last
node is removed. Completion, interruption and errors freeze the same elapsed
time across nodes. Color/glow changes apply immediately during execution.

The existing `kikotools.workflow_timer.color` and `.glow` settings are retained.
Configured colors are preserved; the default is shared blue. Glow also respects
the system's reduced-motion preference.

`createColorPicker()` provides native Hue/Saturation/Brightness sliders, validated
six-digit hex input and keyboard-operable presets inside a native modal dialog.
Changes apply immediately on input; hovering does not change the saved color.
Done or Escape closes the picker and returns focus to its trigger. Disconnecting
the settings control closes the dialog and disposes its listeners/theme scope.
The setting renderer reuses its control across value updates. Its dialog lives
in the document body so those re-renders preserve focus and native slider
interaction. Cleanup waits one microtask to distinguish synchronous reparenting
from actually closing/removing the settings control.

## Dimension swapping

Width Height Selector and Empty Latent Batch share `dimension-swap.js` and
`dimensions.js`. Both use the same native blue Swap W×H button with keyboard and
touch behavior. The selector no longer adds canvas drawing or mouse hit areas.
Repeated mounting reuses one control; node removal disposes its theme/listeners.

The supplied preset labels determine dimensions, including Unicode `×`, ASCII
`x` and formatted metadata. A matching reversed preset is retained; otherwise
the node switches to custom dimensions. Custom values swap directly. Malformed
preset dimensions leave the node unchanged. Each width/height callback receives
the host context exactly once, and existing preset callback results are retained.

The control does not change node dimensions, batch size, native input order or
backend interfaces. Workflow persistence remains with ComfyUI's native widgets;
the DOM control does not serialize its UI state.
