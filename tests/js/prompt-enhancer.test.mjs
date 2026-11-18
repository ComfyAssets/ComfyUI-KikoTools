import test from 'node:test';
import assert from 'node:assert/strict';
import { copyResultMessage } from '../../web/ui/prompt-enhancer.js';

test('success message names the copied path', () => {
    assert.match(copyResultMessage(200, { path: '/u/x.md' }), /\/u\/x\.md/);
});

test('existing file message says it already exists and names the path', () => {
    const message = copyResultMessage(409, { error: 'already exists', path: '/u/x.md' });
    assert.match(message, /already exists/);
    assert.match(message, /\/u\/x\.md/);
});

test('rejected requests show the server error', () => {
    assert.match(copyResultMessage(400, { error: 'Unknown base model' }), /Unknown base model/);
    assert.match(copyResultMessage(500, null), /500/);
});
