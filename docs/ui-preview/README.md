# ComfyAssets UI preview

Interactive design review for [KikoTools #81](https://github.com/ComfyAssets/ComfyUI-KikoTools/issues/81)
and [PromptManager #186](https://github.com/ComfyAssets/ComfyUI_PromptManager/issues/186).
This standalone mockup changes no shipped nodes, APIs, settings, or workflows.

## Open the preview

From the KikoTools repository:

```sh
python3 -m http.server 8769 --bind 127.0.0.1 --directory docs/ui-preview
```

Open <http://127.0.0.1:8769/>. Stop the server with Ctrl+C.
No build, ComfyUI installation, or external requests are needed. Paths, files,
gallery images and prompt rows are sample content; actions affect this page only.
Browse and refresh intentionally reuse the same samples. Nothing is persisted.

## What to try

- Switch Dark/Light to simulate ComfyUI's mode. Production will follow the host;
  this review toggle is not a new product theme setting.
- Change Preview node width and Thumbnail size. Also resize the browser.
- Select and clear images, filter file names, switch Grid/List and change sorting.
- Operate switches with the keyboard; add, disable, remove and reset prompt rows.
- Show the error example and Retry to compare the red treatment against blue.

Both product samples use exactly the same visual tokens and controls. Blue
`#0877bb` and red `#d52430` are review candidates chosen to keep white button text
readable; they are not claimed to be exact colors sampled from the references.
Give feedback on these colors, density, borders, control proportions and resize
behavior before production migration.

Captured review views: [dark](screenshots/dark.png), [light](screenshots/light.png),
and [narrow](screenshots/narrow.png). These show the current candidate design,
not production screenshots or automatic visual regression baselines.

## Automated review checks

With Node.js 24 and the existing frontend test dependencies installed:

```sh
npm ci --prefix tools/testing --ignore-scripts
npx --prefix tools/testing playwright install chromium firefox
node tools/testing/node_modules/@playwright/test/cli.js test \
  --config docs/ui-preview/playwright.config.mjs --project chromium --project firefox
```

Stop the manual preview server first; the suite starts its own disposable server
on port 8769. CI also runs WebKit and touch Chromium using the same configuration.
The tests cover basic interactions, resizing, keyboard operation, theme
consistency and text contrast on sampled surfaces. Screenshots are written under
`tools/testing/test-results/ui-preview/` locally. The suite does not certify screen
reader usability, all state/border contrast, or real ComfyUI compatibility.

See the [foundation proposal](../shared-ui-foundation.md) for the renderer adapter,
real-host tests and incremental migration plan. Pixaroma's control organization
inspired this direction; this preview's code, styles and sample illustrations are
original and include none of his implementation or assets.
