# ComfyAssets controls: first production consumer

The Local Image Loader uses `core.js` and `controls.css` for the approved shared
blue controls and host-following light/dark themes. `../views/image-browser.js`
composes these primitives; `../kiko_local_image_loader.js` retains the controller,
API calls and existing selection persistence.

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
