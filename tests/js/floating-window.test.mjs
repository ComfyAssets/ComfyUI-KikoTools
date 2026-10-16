import test from 'node:test';
import assert from 'node:assert/strict';
import { fitWindowRect } from '../../web/ui/floating-window.js';

test('window bounds keep its controls reachable after moving outside the viewport', () => {
    const rect = fitWindowRect({ x: -100, y: 900, width: 420, height: 400 }, { width: 1000, height: 700 });
    assert.equal(rect.x, 8);
    assert.equal(rect.y + rect.height, 692);
});

test('window fitting respects minimum sizes and small viewports', () => {
    const small = fitWindowRect({ x: 0, y: 0, width: 10, height: 10 }, { width: 1000, height: 700 });
    assert.equal(small.width, 280);
    assert.equal(small.height, 200);
    const narrow = fitWindowRect({ x: 800, y: 600, width: 900, height: 800 }, { width: 260, height: 180 });
    assert.equal(narrow.width, 244);
    assert.equal(narrow.height, 164);
    assert.equal(narrow.x, 8);
    assert.equal(narrow.y, 8);
});
