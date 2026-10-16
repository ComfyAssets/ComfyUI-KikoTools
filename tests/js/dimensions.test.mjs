import test from 'node:test';
import assert from 'node:assert/strict';
import { bindDimensionPresets, dimensionsFromPreset, swapDimensions } from '../../web/ui/dimensions.js';

const app = { canvas: {} };

test('resolution parsing accepts supplied formats and rejects invalid dimensions', () => {
    assert.deepEqual(dimensionsFromPreset(' 928x1664 - Qwen'), [928, 1664]);
    assert.deepEqual(dimensionsFromPreset('1664×928'), [1664, 928]);
    for (const value of [null, {}, 'custom', '0x100', '12.5x100', 'x100', '999999999999999999999x100']) assert.equal(dimensionsFromPreset(value), null);
});

test('preset callbacks preserve returns and default host context without changing custom dimensions', () => {
    const calls = [];
    const node = { widgets: [
        { name: 'preset', callback() { return 'original'; } },
        { name: 'width', value: 64, callback(value, canvas, owner) { calls.push([this.name, value, canvas, owner]); } },
        { name: 'height', value: 128 },
    ] };
    bindDimensionPresets(node, app);
    assert.equal(node.widgets[0].callback('custom'), 'original');
    assert.equal(node.widgets[0].callback('928×1664 - Qwen'), 'original');
    assert.deepEqual(calls, [['width', 928, app.canvas, node]]);
    assert.equal(node.widgets[2].value, 1664);
});

test('incomplete widgets and unavailable reverse options are safe', () => {
    bindDimensionPresets({ widgets: [] }, app);
    swapDimensions({ widgets: [] }, app);
    const node = { widgets: [{ name: 'preset', value: '640×960' }, { name: 'width', value: 1 }, { name: 'height', value: 2 }] };
    bindDimensionPresets(node, app);
    swapDimensions(node, app);
    assert.deepEqual(node.widgets.map(widget => widget.value), ['custom', 960, 640]);
    node.widgets.pop();
    node.widgets[0].callback('640×960');
    swapDimensions(node, app);
    assert.equal(node.widgets[1].value, 960);
});

test('dynamic and array option lists match reverse dimensions', () => {
    for (const options of [['custom', '960x640'], { values: () => ['custom', '960×640'] }]) {
        const node = { widgets: [{ name: 'preset', value: '640×960', options }, { name: 'width', value: 1 }, { name: 'height', value: 2 }] };
        bindDimensionPresets(node, app);
        swapDimensions(node, app);
        assert.equal(node.widgets[0].value, Array.isArray(options) ? '960x640' : '960×640');
    }
});

test('a throwing or recursive preset callback does not leave swapping locked', () => {
    let fail = true;
    const node = { widgets: [
        { name: 'preset', value: '640×960', options: { values: ['640×960', '960×640'] }, callback() { swapDimensions(node, app); if (fail) throw new Error('callback failed'); } },
        { name: 'width', value: 640 }, { name: 'height', value: 960 },
    ] };
    bindDimensionPresets(node, app);
    assert.throws(() => swapDimensions(node, app), /callback failed/);
    fail = false;
    swapDimensions(node, app);
    assert.deepEqual(node.widgets.map(widget => widget.value), ['640×960', 640, 960]);
});
