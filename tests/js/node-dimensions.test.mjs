import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolveNodeSize } from '../../web/views/node-dimensions.js';

test('node dimensions accept whole pixels and respect content minimums', () => {
    assert.deepEqual(resolveNodeSize(['640', '480'], [180, 120]), [640, 480]);
    assert.deepEqual(resolveNodeSize(['1', '10'], [180, 120]), [180, 120]);
});

test('node dimensions reject missing, fractional, unsafe and nonpositive values', () => {
    for (const value of ['', ' ', '0', '-1', '1.5', 'Infinity', 'NaN', '9007199254740992']) {
        assert.equal(resolveNodeSize([value, '480'], [180, 120]), null, value);
        assert.equal(resolveNodeSize(['640', value], [180, 120]), null, value);
    }
});
