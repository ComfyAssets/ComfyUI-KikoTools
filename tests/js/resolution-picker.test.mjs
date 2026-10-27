import test from 'node:test';
import assert from 'node:assert/strict';
import {
    defaultEntry,
    deriveSelection,
    effectiveSize,
    megapixels,
    parseRatio,
    sizesForRatio,
    sizeOnModelChange,
} from '../../web/ui/resolution-picker.js';

const chips = ['1:1', '4:5', '5:4', '3:4', '4:3', '2:3', '3:2', '9:16', '16:9', '21:9', '9:21'];
const mirror = { '1:1': '1:1', '4:5': '5:4', '5:4': '4:5', '3:4': '4:3', '4:3': '3:4', '2:3': '3:2', '3:2': '2:3', '9:16': '16:9', '16:9': '9:16', '21:9': '9:21', '9:21': '21:9' };

function sizesFor(listed) {
    return Object.fromEntries(chips.map((chip) => [chip, listed[chip] || []]));
}

const payload = {
    chips,
    mirror,
    default: 'SDXL',
    families: [
        {
            label: 'SDXL', aliases: ['SDXL 1.0'], models: [], group: 'image', vaeRatio: 8, step: 64, megapixels: [1.0], default: [1024, 1024],
            sizes: sizesFor({ '1:1': [[1024, 1024]], '3:2': [[1216, 832]], '2:3': [[832, 1216]], '16:9': [[1344, 768]], '9:16': [[768, 1344]] }),
        },
        {
            label: 'HunyuanImage 2.1', aliases: [], models: [], group: 'image', vaeRatio: 32, step: 32, megapixels: [4.0], default: [2048, 2048],
            sizes: sizesFor({ '1:1': [[2048, 2048]], '16:9': [[2560, 1536]], '9:16': [[1536, 2560]] }),
        },
    ],
};

test('parseRatio accepts the documented forms and rejects malformed input', () => {
    for (const text of ['16:9', ' 16 / 9 ', '16x9', '16×9', '16X9']) assert.deepEqual(parseRatio(text), [16, 9]);
    for (const text of ['0:5', '16:', 'a:b', '99999999:1', '', null]) assert.equal(parseRatio(text), null);
});
test('deriveSelection prefers authored membership, then the 7% band, then custom', () => {
    assert.deepEqual(deriveSelection(payload, 'HunyuanImage 2.1', 2560, 1536), { family: payload.families[1], chip: '16:9', entryIndex: 0, custom: false, ratioText: '5:3' });
    assert.equal(deriveSelection(payload, 'SDXL', 1200, 800).chip, '3:2');           // 1.5 exactly, not listed
    assert.equal(deriveSelection(payload, 'SDXL', 1200, 800).entryIndex, -1);
    const custom = deriveSelection(payload, 'SDXL', 1600, 800);          // 2:1 is >7% from every chip
    assert.deepEqual([custom.chip, custom.custom, custom.ratioText], [null, true, '2:1']);
    assert.equal(deriveSelection(payload, 'SDXL 1.0', 1024, 1024).chip, '1:1');      // alias
    assert.equal(deriveSelection(payload, 'nope', 1024, 1024).family, null);
});
test('sizesForRatio follows the core formula per tier and effectiveSize rounds to the step', () => {
    assert.deepEqual(sizesForRatio({ step: 16, megapixels: [1, 2] }, [16, 9]), [[1360, 768], [1936, 1088]]);
    assert.deepEqual(sizesForRatio({ step: 16, megapixels: [1, 4] }, [20, 1]), [[4576, 224]]); // 4 MP tier would exceed 8192
    assert.deepEqual(effectiveSize(payload.families[1], 70, 1000), [64, 992]);
    assert.deepEqual(effectiveSize(null, 1001, 1001), [1000, 1000]);
    assert.equal(megapixels(1216, 832), '1.0');
});
test('model change keeps listed sizes, else the same chip default, else the family default', () => {
    assert.deepEqual(sizeOnModelChange(payload, 'HunyuanImage 2.1', 2560, 1536, '16:9'), [2560, 1536]);
    assert.deepEqual(sizeOnModelChange(payload, 'HunyuanImage 2.1', 1344, 768, '16:9'), [2560, 1536]);
    assert.deepEqual(sizeOnModelChange(payload, 'HunyuanImage 2.1', 1216, 832, '3:2'), [2048, 2048]);
    assert.deepEqual(defaultEntry(payload.families[0], '21:9'), null);
});
