export function wordCount(text) {
    const trimmed = typeof text === 'string' ? text.trim() : '';
    return trimmed ? trimmed.split(/\s+/).length : 0;
}

export function clampIndex(index, length) {
    if (!(length > 0) || !Number.isFinite(index)) return 0;
    return Math.min(Math.max(Math.trunc(index), 0), length - 1);
}

export function summary(prompts) {
    if (!Array.isArray(prompts) || !prompts.length) return '';
    const words = prompts.reduce((sum, prompt) => sum + wordCount(prompt), 0);
    return `${prompts.length} ${prompts.length === 1 ? 'prompt' : 'prompts'} · ${words} ${words === 1 ? 'word' : 'words'}`;
}

// A workflow saved while the draft was a text box stores the draft as the first
// widget value. `count` is the number of values the node saves today; a list
// that is exactly one longer still carries that draft, so it is dropped.
export function withoutLegacyDraft(values, count) {
    if (!Array.isArray(values) || !(count > 0) || values.length !== count + 1) return values;
    return values.slice(1);
}
