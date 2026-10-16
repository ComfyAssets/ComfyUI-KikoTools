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

In ComfyUI Settings, search **Embedding Autocomplete**, open its settings,
then download the pack and choose the CSV under **Tag list file**. Enable
**Show Custom Words** and select **Save Settings**. Importing stages the list;
Cancel leaves the active list unchanged. The browser caches the saved file in
IndexedDB for offline use and restores it after a refresh. Clearing browser site
data removes this cache. There is no server-side autocomplete folder to populate.

Alternatively, enter a CSV/TXT URL and select **Load URL**, then save. Remote
servers must allow browser cross-origin requests; for GitHub release assets,
download and import the file locally. Existing one-column word lists and
`tag,frequency` lists remain supported. The default URL is unchanged.

Parsing runs in a Web Worker with a 32 MB UTF-8 limit. Search checks canonical
names and aliases, inserts the canonical tag, and ranks exact matches ahead of
prefixes and substrings, then by descending post count. The number of displayed
results is bounded by Maximum suggestions. Categories are retained in records;
category-specific controls are not currently exposed.

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
