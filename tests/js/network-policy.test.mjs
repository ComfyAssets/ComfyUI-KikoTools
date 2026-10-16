import test from 'node:test';
import assert from 'node:assert/strict';
import { isFixtureURL } from '../../tools/testing/network-policy.mjs';
const base = 'http://127.0.0.1:8766';
test('the network guard allows the test origin and WebKit local blob URLs', () => {
    assert.equal(isFixtureURL(`${base}/extensions/kikotools/display_any.js`, base), true);
    assert.equal(isFixtureURL(`blob:${base}/local-script`, base), true);
});
test('the network guard denies external destinations and other localhost ports', () => {
    for (const url of ['https://example.com/model', 'http://127.0.0.1:9000/private', 'blob:https://example.com/script', 'data:text/plain,fixture']) {
        assert.equal(isFixtureURL(url, base), false, url);
    }
});
