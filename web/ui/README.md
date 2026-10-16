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
