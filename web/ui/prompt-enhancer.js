export const COPY_MENU_LABEL = 'Copy system prompt to user folder';

export function copyResultMessage(status, body) {
    if (status === 200) return `Copied to ${body?.path}`;
    if (status === 409) return `File already exists: ${body?.path}`;
    return body?.error || `Copy failed (${status})`;
}
