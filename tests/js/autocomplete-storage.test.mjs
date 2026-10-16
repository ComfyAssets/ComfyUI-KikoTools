import test from 'node:test';
import assert from 'node:assert/strict';
import { tagCache, parseTagFile } from '../../web/autocomplete/tag-storage.js';

test('a blocked cache operation cannot write after its caller has received an error', async () => {
    const request = {};
    let closed = false, wrote = false;
    globalThis.indexedDB = { open: () => request };
    try {
        const operation = tagCache({ source: 'new-file' });
        request.onblocked();
        await assert.rejects(operation, /blocked/);
        request.result = { close: () => { closed = true; }, transaction: () => { wrote = true; throw new Error('Abandoned operation wrote data'); } };
        request.onsuccess();
        assert.equal(closed, true);
        assert.equal(wrote, false);
    } finally { delete globalThis.indexedDB; }
});

test('cancelled imports never start workers, and running workers terminate on cancellation or failure', async () => {
    await assert.rejects(parseTagFile('tag', AbortSignal.abort()), { name: 'AbortError' });
    let current;
    globalThis.Worker = class {
        constructor() { current = this; this.terminated = false; }
        postMessage() {}
        terminate() { this.terminated = true; }
    };
    try {
        const controller = new AbortController();
        const aborted = parseTagFile('tag', controller.signal);
        controller.abort();
        await assert.rejects(aborted, { name: 'AbortError' });
        assert.equal(current.terminated, true);
        const failed = parseTagFile('tag', new AbortController().signal);
        current.onerror();
        await assert.rejects(failed, /Could not parse/);
        assert.equal(current.terminated, true);
    } finally { delete globalThis.Worker; }
});
