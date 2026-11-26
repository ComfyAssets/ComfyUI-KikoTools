import test from 'node:test';
import assert from 'node:assert/strict';
import { clampIndex, summary, wordCount } from '../../web/ui/h3-reference-prompter.js';

test('summary counts prompts and words, singular for one', () => {
    assert.equal(summary(['one two three']), '1 prompt · 3 words');
    assert.equal(summary(['a b', 'c d e']), '2 prompts · 5 words');
});

test('summary is empty text when there are no prompts', () => {
    assert.equal(summary([]), '');
    assert.equal(summary(undefined), '');
});

test('clampIndex keeps valid indexes and clamps the rest', () => {
    assert.equal(clampIndex(1, 3), 1);
    assert.equal(clampIndex(5, 3), 2);
    assert.equal(clampIndex(-2, 3), 0);
    assert.equal(clampIndex(1.7, 3), 1);
    assert.equal(clampIndex(Number.NaN, 3), 0);
    assert.equal(clampIndex(2, 0), 0);
});

test('wordCount splits on any whitespace and ignores edges', () => {
    assert.equal(wordCount('  a\tb\n\nc  '), 3);
    assert.equal(wordCount(''), 0);
    assert.equal(wordCount(null), 0);
});
