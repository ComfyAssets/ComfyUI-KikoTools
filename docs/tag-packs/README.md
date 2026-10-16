# Autocomplete tag packs

ComfyAssets prepares filtered autocomplete data from Danbooru's public
`tags.json` and `tag_aliases.json` APIs. Dataset releases are versioned separately
from KikoTools and stored as release assets, keeping bulk data out of Git history.

## Danbooru — Illustrious / NoobAI, 2026-10-16

[Download the CSV and manifest](https://github.com/ComfyAssets/ComfyUI-KikoTools/releases/tag/tags-2026-10-16).
This snapshot contains 165,158 canonical tags, their categories, post counts, and
aliases. The adjacent manifest records the retrieval date, model targets,
selection filters, schema, byte size, and SHA-256 checksum.

The UTF-8 CSV has no header. Columns are `tag,category,post_count,aliases`.
Aliases share a comma-separated field; use a CSV parser that respects quoting.
An empty alias field means no aliases. Category codes are 0 (general), 1
(artist), 3 (copyright), 4 (character), and 5 (meta).

The existing URL loader expects `tag,frequency`; it cannot correctly consume
this four-column pack yet. Automatic installation, local import, and settings
integration remain pending. Publishing the asset does not change the default
autocomplete source.

## Source and terms

Source data: [Danbooru](https://danbooru.donmai.us/), collected 2026-10-16.
Selection and packaging: ComfyAssets. This is an independent filtered snapshot,
not an official Danbooru release or a guarantee of model compatibility.

Refer to [Danbooru's Terms of Service](https://danbooru.donmai.us/terms) and the
[official terms template](https://github.com/danbooru/danbooru/blob/master/app/views/static/terms_of_service.html.erb).
The template's Copyright Infringement section identifies tags as factual
information that is generally not copyrightable. Its API Usage section requires
compliance with API rate limits. This reference does not claim an explicit
dataset license or extend KikoTools' software license to upstream data.
