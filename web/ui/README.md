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

## Model Resolution Picker

The picker's chips, size list and header are derived from the native `model`,
`width` and `height` widgets on every change; no panel state is saved in the
workflow. The only extra state is an in-memory custom-ratio flag, lost on
reload. The family table comes from `GET /kikotools/model_resolution/families`,
and a chip whose family lists no sizes for it is disabled. Swap reuses
`dimension-swap.js` and `dimensions.js`, and node removal disposes the scope.

The native `resolution` combo is another projection of the same state. Its
options are rebuilt whenever the model or the active chip changes: `custom` plus
the active chip's sizes (all family sizes for Custom ratio or no chip). Picking
a label writes `width`/`height` through their callbacks and the matching chip
activates; a chip click, swap, typed size or model change sets the label to the
matching size, and a size outside the list, wired inputs or a failed families
load show `custom`. Each ratio chip also carries an `aria-hidden` outline of its
shape.

The panel reports its measured content height (padding, visible children and
gaps) as both the minimum and the maximum DOM-widget height, and after every
render the extension sets the node height to the host's `computeSize()` while
keeping the width. The measurement is retried for up to 60 frames when the
element is not attached yet (fresh mount, workflow load), skipped while the
family table is still loading, and ignored when the panel is hidden by the
host. A `ResizeObserver` on the panel's children schedules a refit on the next
frame when their boxes change later, for example when the stylesheet arrives
after the first render; measuring inside the observer delivery would make WebKit
report an undelivered-notifications loop error. The panel children must carry no
vertical margins (the stylesheet zeroes them).

## Node Dimensions and modal dialogs

The ComfyAssets-only Node Dimensions context menu uses `dialog.js` for a native
modal shell, shared theme tokens, focus restoration and scoped cleanup. Native
modality contains keyboard focus; Escape and Cancel close without applying.
`../views/node-dimensions.js` owns the form and node lifecycle binding.

Enter or Apply accepts positive whole pixel values and clamps them to the node's
computed content minimum. Invalid values keep the form open with an associated
error. Opening the same node again reuses its dialog; node removal closes it and
preserves the previous removal hook's context, arguments and return value.
ComfyUI continues to serialize the resulting node size.

The global `KikoToolsExtensions.createDialog(htmlContent, onOK, onCancel)` helper
remains available for trusted HTML templates. It returns the native dialog with
an immediate `close()` method. OK/Enter supplies the dialog and input/select
values; Cancel/Escape invokes cancellation once. Manual `close()` dismisses
without invoking cancellation. New views should build DOM through shared
factories rather than pass HTML to this compatibility helper.

## Display Text and Display Any

Both nodes use `../views/text-output.js` for labelled, selectable read-only text
areas and shared Copy buttons. Display Text detects paired positive/negative
prompts and offers a copy action for each. Display Any preserves the complete
formatted output in one scrollable monospace field instead of separate chunks.
The view fills the available node area; updating output preserves node size.
Copy success and failure appear in a polite status area. Replacement and removal
cancel delayed feedback and ignore pending clipboard results from the old view.

`../controllers/display-node.js` preserves native input/mode widgets and existing
lifecycle hook arguments, context and return values. Complete output, including
empty text, is saved in a `kikoDisplay: { version: 1, text }` workflow snapshot.
Legacy widget values remain readable: converted input prefixes, prompt header
pairs, native Display Any modes and all saved output chunks are recognized.
The new output DOM widget does not serialize presentation state into native
widget values. Node removal disposes the view, its listeners and theme observers.

## Embedding Autocomplete

`autocomplete-suggestions.js` supplies the shared themed listbox, type badges,
selected state and viewport placement. The controller retains resource fetching,
matching, sorting, triggers and insertion preferences. Focus stays in the native
textarea; arrow keys select suggestions, configured Enter/Tab keys insert, and
Escape dismisses. New input clears the previous selection. Completion names are
rendered as text, including directory names, without interpreting markup.

`text-widget-adapter.js` binds editable Nodes 2.0 replacement textareas through
their node ID and associated label. It leaves the original widget/input intact,
cleans up disconnected replacements, and preserves Classic behavior when switching
back. Read-only and disabled fields are excluded. Each widget owns its listeners,
blur work and temporary accessibility attributes; removing a different widget
does not dismiss the active list. Page cleanup cancels pending refresh work.

`../views/autocomplete-settings.js` uses the shared native dialog and switches.
Only Save updates the existing `kikotools.embedding_autocomplete.settings` key;
Cancel/Escape discards edits. All advanced saved preferences are retained.
Storage failures keep the dialog open and restore the previous live preferences.
The settings launcher owns dialog cleanup, tolerates synchronous reparenting and
returns keyboard focus when the modal closes. The shared modal shell contains
pointer events so nested dialogs do not dismiss ComfyUI's parent settings panel.

### Tag packs and autocomplete preferences

The settings view stages CSV/TXT file and URL imports until Save Settings.
`autocomplete/tags.js` parses quoted four-column Danbooru data and legacy
word/frequency lists, validates counts/categories, deduplicates tags and aliases,
and limits search results without sorting every matching tag on each keystroke.
`autocomplete/tag-worker.js` performs parsing outside the UI thread; its owner
terminates it on completion, error, or dialog removal. Records expand to the
existing suggestion shape only for returned results.

`autocomplete/tag-storage.js` persists the active source text in browser
IndexedDB. The controller restores matching cached sources before requesting a
URL, guards stale loads, and retains the active list when an import fails.
Advanced trigger, matching and insertion controls use the existing settings key.
For dataset provenance, format and installation, see
[Tag packs](../../docs/tag-packs/README.md).

Node removal uses one hook per node, shared by its active text widgets. Detaching
widgets in any order restores the original hook after the last widget leaves.
General queries accept Unicode and punctuation between whitespace/comma
boundaries. Literal bracketed names are tried before interpreting leading
parentheses/brackets as prompt weighting; insertion preserves surrounding
weight syntax. URL downloads enforce their byte limit while reading the body,
cancel oversized/aborted streams, and decode UTF-8 across chunk boundaries.

### Custom Colors

`../kiko_custom_colors.js` opens the same shared color picker as Workflow Timer
from the host's node and group context menus. Hex entry, HSV sliders and presets
apply immediately. Full/Title/Background options, selected-node behavior, title
auto-shading and existing setting IDs are retained. Closing or replacing the
picker removes its dialog and theme observers; removing its target node also
closes it without replacing other node removal behavior. Keyboard focus returns
to the available opener, with the canvas as a fallback.
