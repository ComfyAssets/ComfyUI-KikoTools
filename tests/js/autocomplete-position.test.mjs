import test from 'node:test';
import assert from 'node:assert/strict';
import { suggestionPosition } from '../../web/ui/autocomplete-suggestions.js';

test('completion popup stays within the viewport and flips above a low field', () => {
    assert.deepEqual(suggestionPosition({ left: 20, top: 40, bottom: 80 }, { width: 220, height: 150 }, { width: 800, height: 600 }), { left: 20, top: 84 });
    assert.deepEqual(suggestionPosition({ left: 300, top: 400, bottom: 440 }, { width: 220, height: 150 }, { width: 320, height: 480 }), { left: 92, top: 246 });
    assert.deepEqual(suggestionPosition({ left: -30, top: 2, bottom: 10 }, { width: 300, height: 300 }, { width: 240, height: 200 }), { left: 8, top: 8 });
});
