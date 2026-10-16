"""Logic for the Model Compare Sheet node: tile files on disk into a labeled grid."""

import math
import os
import re
from datetime import datetime
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from ...base.model_folders import is_within, natural_sort

GRID_FILENAME = "grid.png"
PREVIEW_FILENAME = "grid_preview.png"
PREVIEW_WIDTH = 1024
BACKGROUND = (28, 28, 28)
LABEL_COLOR = (235, 235, 235)


def resolve_run_dir(output_dir: str, run_name: str) -> str:
    """Directory for one compare run, always inside output/model_compare."""
    if not run_name or os.path.isabs(run_name) or ".." in run_name.split("/"):
        raise ValueError(f"Invalid run_name: {run_name!r}")
    run_dir = os.path.join(output_dir, "model_compare", run_name)
    if not is_within(run_dir, output_dir):
        raise ValueError(f"Invalid run_name: {run_name!r}")
    return run_dir


def tile_filename(index: int, label: str, batch_index: int, batch_size: int) -> str:
    """'03_label.png', or '03_label_2.png' for the second image of a batch."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", label)
    suffix = f"_{batch_index + 1}" if batch_size > 1 else ""
    return f"{index:02d}_{safe}{suffix}.png"


def label_from_filename(filename: str) -> str:
    stem = os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r"^\d+_", "", stem)


def list_tiles(run_dir: str) -> List[str]:
    """PNG tiles in a run directory in natural order, excluding the grid itself."""
    names = [
        f
        for f in os.listdir(run_dir)
        if f.lower().endswith(".png") and f not in (GRID_FILENAME, PREVIEW_FILENAME)
    ]
    return [os.path.join(run_dir, f) for f in natural_sort(names)]


def archive_previous_sweep(run_dir: str) -> Optional[str]:
    """Rename a run folder that already holds tiles to '<run_dir>_<timestamp>'.

    Called when a sweep starts over (index 0) so stale tiles from an
    interrupted sweep never end up in the new grid. Returns the archive path,
    or None when there was nothing to archive.
    """
    if not os.path.isdir(run_dir) or not list_tiles(run_dir):
        return None
    stamp = datetime.fromtimestamp(os.path.getmtime(run_dir)).strftime("%Y%m%d-%H%M%S")
    archive = f"{run_dir}_{stamp}"
    n = 1
    while os.path.exists(archive):
        n += 1
        archive = f"{run_dir}_{stamp}_{n}"
    os.rename(run_dir, archive)
    return archive


def _font(font_size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", font_size)
    except OSError:
        return ImageFont.load_default(size=font_size)


def _fit_label(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    while text and draw.textlength(text, font=font) > max_width:
        text = text[:-2] + "…" if len(text) > 1 else ""
    return text


def build_contact_sheet(
    paths: List[str], columns: int, tile_width: int, font_size: int
) -> Image.Image:
    """Tile the images at `paths` into a grid with each file's label underneath."""
    tiles = []
    for path in paths:
        with Image.open(path) as im:
            im = im.convert("RGB")
            tile_height = max(1, round(im.height * tile_width / im.width))
            tiles.append((im.resize((tile_width, tile_height), Image.LANCZOS), path))

    band = font_size * 2
    cell_height = max(t.height for t, _ in tiles) + band
    cols = min(len(tiles), columns)
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (cols * tile_width, rows * cell_height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    font = _font(font_size)

    for i, (tile, path) in enumerate(tiles):
        x = (i % cols) * tile_width
        y = (i // cols) * cell_height
        sheet.paste(tile, (x, y))
        label = _fit_label(draw, label_from_filename(path), font, tile_width - 8)
        text_x = x + (tile_width - draw.textlength(label, font=font)) / 2
        text_y = y + tile.height + (band - font_size) / 2
        draw.text((text_x, text_y), label, fill=LABEL_COLOR, font=font)
    return sheet


def preview_of(sheet: Image.Image) -> Image.Image:
    """A copy of the sheet no wider than PREVIEW_WIDTH, for the node preview and galleries."""
    if sheet.width <= PREVIEW_WIDTH:
        return sheet
    height = max(1, round(sheet.height * PREVIEW_WIDTH / sheet.width))
    return sheet.resize((PREVIEW_WIDTH, height), Image.LANCZOS)
