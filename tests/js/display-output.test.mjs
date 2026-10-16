import { test } from 'node:test';
import assert from 'node:assert/strict';
import { outputSections } from '../../web/views/text-output.js';
import { restoreDisplayOutput } from '../../web/controllers/display-node.js';

test('display text recognizes paired prompts and preserves ordinary text verbatim', () => {
    assert.deepEqual(outputSections('text', 'Positive prompt: bright ** metadata\nNegative prompt: blur ** metadata').map(section => section.text), ['bright', 'blur']);
    assert.deepEqual(outputSections('text', 'POSITIVE PROMPT: sun\nNEGATIVE PROMPT: rain').map(section => section.text), ['sun', 'rain']);
    for (const text of ['', 'Positive prompt: alone', '<script>hello</script>\nnext']) {
        assert.deepEqual(outputSections('text', text).map(section => section.text), [text]);
    }
    const long = Array.from({ length: 45 }, (_, index) => `Line ${index}`).join('\n');
    assert.deepEqual(outputSections('any', long).map(section => section.text), [long]);
});

test('versioned display snapshots preserve complete output including empty text', () => {
    for (const kind of ['text', 'any']) {
        for (const text of ['', 'mode\nfull\noutput']) {
            assert.equal(restoreDisplayOutput({ kikoDisplay: { version: 1, text }, widgets_values: ['stale'] }, kind, false), text);
        }
        assert.equal(restoreDisplayOutput({}, kind, false), null);
        assert.equal(restoreDisplayOutput({ widgets_values: [] }, kind, false), null);
    }
});

test('legacy display workflows restore prompt pairs, converted inputs and every chunk', () => {
    assert.equal(restoreDisplayOutput({ widgets_values: ['✓ Positive Prompt', 'sun', null, '✗ Negative Prompt', 'rain', null] }, 'text', false), 'Positive prompt: sun\nNegative prompt: rain');
    assert.equal(restoreDisplayOutput({ widgets_values: ['converted', 'saved text', null] }, 'text', true), 'saved text');
    assert.equal(restoreDisplayOutput({ widgets_values: ['raw value', 'first\nchunk', 'second\nchunk', null] }, 'any', false), 'first\nchunk\nsecond\nchunk');
    assert.equal(restoreDisplayOutput({ widgets_values: ['converted', 'tensor shape', 'shape', null] }, 'any', true), 'shape');
    assert.equal(restoreDisplayOutput({ widgets_values: ['tensor shape'] }, 'any', false), null);
    assert.equal(restoreDisplayOutput({ widgets_values: [''] }, 'text', false), '');
    assert.equal(restoreDisplayOutput({ kikoDisplay: { version: 99, text: 'unknown' }, widgets_values: ['legacy'] }, 'text', false), 'legacy');
});

test('prompt detection retains leading markdown markers accepted by existing workflows', () => {
    assert.equal(outputSections('text', 'Positive prompt: **sun\nNegative prompt: rain')[0].text, '**sun');
});
