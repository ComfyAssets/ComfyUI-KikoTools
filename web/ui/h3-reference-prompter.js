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
