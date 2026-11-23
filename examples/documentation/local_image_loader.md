# Local Image Loader

## Overview

The Local Image Loader is a gallery inside the node. You browse a local folder, click an image, and the node outputs it. It can also output the folder you browsed to, and an ordered set of photos for Create H3 RefMod in ComfyUI-MiniMaxH3Mod.

The gallery lists videos and audio files too, but the node outputs images only.

## Node outputs

| Output | Type | Description |
|--------|------|-------------|
| `image` | IMAGE | The selected image. |
| `info` | STRING | JSON with the image's file name, width, height, color mode and format, plus the prompt, workflow or A1111 `parameters` saved in the file when there are any. |
| `folder` | STRING | The folder the gallery shows, or the selected image's folder. |
| `refs` | H3_REF_LIST | The picked refs in pick order, all at the first pick's size, for the `refs_bundle` input of Create H3 RefMod. |
| `refs_preview` | IMAGE | The same refs as one image batch, to check what Create H3 RefMod will encode. It shares memory with `refs`. |

The node has no inputs. Its hidden `unique_id` ties the gallery's choices to this node.

## Usage

1. Add **Local Image Loader** from 🫶 ComfyAssets → 💾 Images.
2. Type or paste a folder path and press Enter or **Browse**. The path field suggests folders as you type.
3. Click an image to select it for the `image` and `info` outputs.
4. To pass a whole folder on, browse to it and queue. The `folder` output has its path even when no image is selected, for nodes such as a dataset captioner.

### Refs for MiniMax H3

1. Ctrl-click (Cmd-click on a Mac) photos in the order you want. Each picked photo shows its number, and the `Refs: N` bar counts them. Ctrl-click a picked photo again to remove it; the others renumber.
2. Picks can come from different folders. **Clear refs** removes them all.
3. Connect `refs` to `refs_bundle` on Create H3 RefMod, and `refs_preview` to a Preview Image node if you want to see the result.

The first pick sets the size. The node scales each other pick to cover that size and crops the center, the same rule Create H3 RefMod uses. Pick a photo with the shape you want first.

Refs are images only, up to 256. The workflow saves the picks, and a file that is missing or outside the allowed folders when you queue is skipped with a warning in the console.

### Gallery controls

- **Saved paths**: **☆ Save path** adds the current folder to the list, and **×** removes the selected one.
- **↑** opens the parent folder, and **↻** reloads the current one.
- **Sort** by name, date or size, and **Order** ascending or descending.
- **Filter this page** hides files whose names don't match.
- **Grid** or **List** layout, and a **Thumbnail size** slider from 128 to 384 px.
- Page controls at the bottom split large folders.
- Double-click a file to open it full size in a new browser tab.

## Supported files

| Kind | Extensions | Output |
|------|------------|--------|
| Images | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.webp` | `image`, `refs` |
| Videos | `.mp4`, `.webm`, `.mov`, `.mkv`, `.avi` | listed only |
| Audio | `.mp3`, `.wav`, `.ogg`, `.flac` | listed only |

## Examples

Load an image and show its metadata:

```
Local Image Loader [image] → your image node
                   [info]  → Display Text
```

Build an H3 RefMod from five to eight photos:

```
Local Image Loader [refs]         → Create H3 RefMod [refs_bundle] → Save H3 RefMod
                   [refs_preview] → Preview Image
```

## Troubleshooting

**The folder does not load.** Check that the path exists and ComfyUI can read it. The node serves files only from ComfyUI's input and output folders and your saved paths. Save the folder with **☆ Save path** to allow it. A drive root, your home folder and the folders above it can't be saved; save a folder inside your home folder instead.

**A ref is missing from `refs`.** The file was moved, deleted or is outside the allowed folders. The console names the skipped file.

**Thumbnails are slow in a large folder.** Sort by date to find recent files, or split the folder into subfolders.

## Technical details

The gallery calls the node's API routes to list folders, make 320 px thumbnails and save each node's choices. The server checks every path against the allowed folders before it reads a file, and checks the saved choices again when the workflow runs.
