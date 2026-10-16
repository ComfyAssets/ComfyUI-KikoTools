import test from 'node:test';
import assert from 'node:assert/strict';
import { readTagResponse } from '../../web/autocomplete/tag-download.js';

function response(chunks, headers = {}) {
    let index = 0, cancelled = false;
    const body = new ReadableStream({
        pull(controller) { if (index < chunks.length) controller.enqueue(chunks[index++]); else controller.close(); },
        cancel() { cancelled = true; },
    }, { highWaterMark: 0 });
    return { value: new Response(body, { headers }), cancelled: () => cancelled, read: () => index };
}
const encode = value => new TextEncoder().encode(value);

test('tag downloads stop reading at the byte limit with missing or dishonest headers', async () => {
    for (const headers of [{}, { 'content-length': '1' }]) {
        const stream = response([encode('1234'), encode('56789'), encode('unread')], headers);
        await assert.rejects(readTagResponse(stream.value, { maxBytes: 8 }), /large/i);
        assert.equal(stream.cancelled(), true);
        assert.equal(stream.read(), 2);
        assert.equal(stream.value.body.locked, false);
    }
});
test('oversized declared downloads are cancelled without reading their contents', async () => {
    const stream = response([encode('unread')], { 'content-length': '100' });
    await assert.rejects(readTagResponse(stream.value, { maxBytes: 8 }), /large/i);
    assert.equal(stream.read(), 0);
    assert.equal(stream.cancelled(), true);
});
test('streamed UTF-8 survives split code points and an exact byte limit', async () => {
    const bytes = encode('日本語');
    const stream = response([bytes.slice(0, 2), bytes.slice(2, 5), bytes.slice(5)]);
    assert.equal(await readTagResponse(stream.value, { maxBytes: bytes.length }), '日本語');
    assert.equal(stream.value.body.locked, false);
    assert.equal(await readTagResponse(new Response(null)), '');
});
test('aborted or failed downloads release their reader and preserve the error', { timeout: 2000 }, async () => {
    const controller = new AbortController();
    let cancelled = false;
    const stream = new ReadableStream({ cancel() { cancelled = true; } });
    const value = new Response(stream);
    const pending = readTagResponse(value, { signal: controller.signal });
    controller.abort();
    await assert.rejects(pending, { name: 'AbortError' });
    assert.equal(cancelled, true);
    assert.equal(value.body.locked, false);
    const stopped = response([encode('unread')]);
    await assert.rejects(readTagResponse(stopped.value, { signal: AbortSignal.abort() }), { name: 'AbortError' });
    assert.equal(stopped.cancelled(), true);
    const error = new Error('Network interrupted');
    const failed = new Response(new ReadableStream({ start(stream) { stream.error(error); } }));
    await assert.rejects(readTagResponse(failed), /Network interrupted/);
    assert.equal(failed.body.locked, false);
});
