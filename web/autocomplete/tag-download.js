import { MAX_TAG_BYTES } from './tags.js';

export async function readTagResponse(response, { maxBytes = MAX_TAG_BYTES, signal } = {}) {
    const tooLarge = () => new Error(`Tag file too large. Maximum size is ${maxBytes === MAX_TAG_BYTES ? '32 MB' : `${maxBytes} bytes`}.`);
    if (signal?.aborted) {
        await response.body?.cancel();
        signal.throwIfAborted();
    }
    if (Number(response.headers.get('content-length')) > maxBytes) {
        await response.body?.cancel();
        throw tooLarge();
    }
    if (!response.body) return '';
    const reader = response.body.getReader();
    const abort = () => { reader.cancel().catch(() => {}); };
    signal?.addEventListener('abort', abort, { once: true });
    const decoder = new TextDecoder();
    const parts = [];
    let bytes = 0;
    try {
        while (true) {
            signal?.throwIfAborted();
            const { done, value } = await reader.read();
            signal?.throwIfAborted();
            if (done) break;
            bytes += value.byteLength;
            if (bytes > maxBytes) {
                await reader.cancel();
                throw tooLarge();
            }
            parts.push(decoder.decode(value, { stream: true }));
        }
        parts.push(decoder.decode());
        return parts.join('');
    } finally {
        signal?.removeEventListener('abort', abort);
        reader.releaseLock();
    }
}
