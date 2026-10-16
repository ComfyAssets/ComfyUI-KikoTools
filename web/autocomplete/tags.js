export const MAX_TAG_BYTES = 32 * 1024 * 1024;

function* csvRows(text) {
    let row = [], field = '', quoted = false, closed = false;
    for (let i = 0; i <= text.length; i++) {
        const char = text[i];
        if (quoted) {
            if (char === undefined) throw new Error('Unclosed CSV quote.');
            if (char === '"') {
                if (text[i + 1] === '"') { field += '"'; i++; }
                else { quoted = false; closed = true; }
            } else field += char;
        } else if (char === ',' || char === '\n' || char === undefined) {
            row.push(field.trim());
            field = ''; closed = false;
            if (char !== ',') {
                if (row.some(value => value !== '')) yield row;
                row = [];
            }
        } else if (char === '\r' && (text[i + 1] === '\n' || i === text.length - 1)) {
            continue;
        } else if (char === '"' && !field && !closed) quoted = true;
        else {
            if (closed && char.trim()) throw new Error('Unexpected text after CSV quote.');
            field += char;
        }
    }
}

export function parseTagList(text) {
    if (new TextEncoder().encode(text).byteLength > MAX_TAG_BYTES) throw new Error('Tag file too large. Maximum size is 32 MB.');
    if (/^\s*<(?:!doctype|html|script|body|iframe)\b/i.test(text)) throw new Error('Expected a tag list, received HTML or script content.');
    const unique = new Map();
    let first = true;
    for (const row of csvRows(text.replace(/^\ufeff/, ''))) {
        if (first && ['tag', 'name'].includes(row[0].toLowerCase()) && ['category', 'frequency', 'post_count'].includes(row[1]?.toLowerCase())) {
            first = false; continue;
        }
        first = false;
        if (![1, 2, 4].includes(row.length)) throw new Error('Expected tag,frequency or tag,category,post_count,aliases.');
        const name = row[0];
        if (!name || name.length > 500 || /[\u0000-\u001f\u007f]/.test(name)) throw new Error('Invalid tag name.');
        const count = row.length === 4 ? row[2] : row[1] || '0';
        if (!/^\d+$/.test(count) || !Number.isSafeInteger(Number(count))) throw new Error(`Invalid post count for ${name}.`);
        const category = row.length === 4 ? Number(row[1]) : null;
        if (row.length === 4 && (!/^[01345]$/.test(row[1]))) throw new Error(`Invalid category for ${name}.`);
        const aliases = row.length === 4 ? [...new Set(row[3].split(',').map(value => value.trim()).filter(Boolean))] : [];
        if (aliases.some(alias => alias.length > 500 || /[\u0000-\u001f\u007f]/.test(alias))) throw new Error(`Invalid alias for ${name}.`);
        const existing = unique.get(name);
        if (existing) {
            existing.frequency = Math.max(existing.frequency, Number(count));
            existing.aliases = [...new Set([...existing.aliases, ...aliases])];
        } else unique.set(name, { name, category, frequency: Number(count), aliases });
    }
    if (!unique.size) throw new Error('No tags found in the file.');
    for (const tag of unique.values()) tag.searchText = [tag.name, ...tag.aliases].join('\n').toLowerCase();
    return [...unique.values()].sort((a, b) => b.frequency - a.frequency || a.name.localeCompare(b.name));
}

export function searchTags(tags, prefix, limit) {
    if (limit <= 0) return [];
    prefix = prefix.toLowerCase();
    const buckets = [[], [], []];
    for (const tag of tags) {
        if (tag.searchText && !tag.searchText.includes(prefix)) continue;
        const names = [tag.name, ...(tag.aliases || [])];
        let tier = 3;
        for (const name of names) {
            const lower = name.toLowerCase();
            if (lower === prefix) { tier = 0; break; }
            if (lower.startsWith(prefix)) tier = Math.min(tier, 1);
            else if (lower.includes(prefix)) tier = Math.min(tier, 2);
        }
        if (tier < 3 && buckets[tier].length < limit) buckets[tier].push(tag);
        if (buckets[0].length >= limit) break;
    }
    return buckets.flat().slice(0, limit).map(tag => ({ ...tag, fullPath: tag.name, type: 'custom', display: tag.name, value: tag.name }));
}

export function tagQuery(text, weighted = false) {
    const match = text.match(/[^\s,]+$/u);
    if (!match) return null;
    const leading = weighted ? match[0].match(/^[\[(]*/)[0].length : 0;
    const prefix = match[0].slice(leading);
    return prefix ? { prefix, start: match.index + leading } : null;
}
