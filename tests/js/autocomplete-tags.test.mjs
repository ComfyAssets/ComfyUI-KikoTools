import test from 'node:test';
import assert from 'node:assert/strict';
import { parseTagList, searchTags, tagQuery } from '../../web/autocomplete/tags.js';

test('four-column packs preserve categories, popularity and quoted aliases', () => {
    const tags = parseTagList('\ufefftag,category,post_count,aliases\r\nblue_eyes,0,900,"blue_eye,azure_eyes"\r\nartist_name,1,700,"artist,artist_alias"\r\n');
    assert.deepEqual(tags.map(({ name, category, frequency, aliases }) => ({ name, category, frequency, aliases })), [
        { name: 'blue_eyes', category: 0, frequency: 900, aliases: ['blue_eye', 'azure_eyes'] },
        { name: 'artist_name', category: 1, frequency: 700, aliases: ['artist', 'artist_alias'] },
    ]);
    assert.equal(searchTags(tags, 'azure', 5)[0].value, 'blue_eyes');
});
test('legacy words, frequencies and headerless packs remain compatible', () => {
    assert.deepEqual(parseTagList('low,2\nhigh,100\nplain\n').map(tag => [tag.name, tag.frequency]), [['high', 100], ['low', 2], ['plain', 0]]);
    assert.equal(parseTagList('long_hair,0,6317335,')[0].frequency, 6317335);
    assert.equal(parseTagList('"say""hello",0,12,"nickname"')[0].name, 'say"hello');
});
test('invalid data fails clearly instead of replacing a valid list with garbage', () => {
    for (const text of ['', '<!doctype html><html>error</html>', '<script>alert(1)</script>', 'x,0,NaN,', 'x,2,12,', 'x,-1', '"unfinished', 'x,0,1,a,extra', 'x,0,1,"a"tail', 'name,category,post_count,aliases\n']) {
        assert.throws(() => parseTagList(text), Error, text);
    }
    assert.throws(() => parseTagList('x'.repeat(32 * 1024 * 1024 + 1)), /large/i);
});
test('duplicates merge aliases while retaining the highest frequency', () => {
    const tags = parseTagList('blue_eyes,0,100,azure\nblue_eyes,0,200,blue_eye');
    assert.equal(tags.length, 1);
    assert.equal(tags[0].frequency, 200);
    assert.deepEqual(tags[0].aliases, ['azure', 'blue_eye']);
});
test('search ranks exact canonical and alias matches, prefixes, then substrings by popularity', () => {
    const tags = parseTagList('blue_sky,0,100,azure\nblue_eyes,0,900,\nlight_blue,0,500,\nblue,0,1,\n');
    assert.deepEqual(searchTags(tags, 'blue', 3).map(tag => tag.name), ['blue', 'blue_eyes', 'blue_sky']);
    assert.equal(searchTags(tags, 'AZURE', 1)[0].name, 'blue_sky');
    assert.deepEqual(searchTags(tags, 'missing', 3), []);
    assert.deepEqual(searchTags(tags, '', 0), []);
    assert.deepEqual(searchTags(tags, '', 2).map(tag => tag.name), ['blue_eyes', 'light_blue']);
});
test('search handles 300,000 tags with bounded results and canonical alias insertion', () => {
    const text = Array.from({ length: 300000 }, (_, i) => `tag_${i},0,${i},alias_${i}`).join('\n');
    const tags = parseTagList(text);
    assert.equal(tags.length, 300000);
    const matches = searchTags(tags, 'alias_299999', 20);
    assert.equal(matches.length, 1);
    assert.equal(matches[0].value, 'tag_299999');
});

test('tag data supports Unicode, emoticons and quoted commas as plain text', () => {
    const tags = parseTagList('heart,0,50,<3\n>_<,0,20,\n日本語,3,10,"別名,にほんご"');
    assert.equal(searchTags(tags, '<3', 1)[0].value, 'heart');
    assert.equal(searchTags(tags, 'にほんご', 1)[0].value, '日本語');
    assert.equal(searchTags(tags, '>_<', 1)[0].value, '>_<');
});

test('worker reports parsed tag records and errors through its message boundary', async () => {
    const messages = [];
    globalThis.self = { postMessage: message => messages.push(message) };
    try {
        await import('../../web/autocomplete/tag-worker.js');
        self.onmessage({ data: 'blue_eyes,0,20,azure' });
        self.onmessage({ data: 'bad,0,invalid,' });
        assert.equal(messages[0].tags[0].frequency, 20);
        assert.match(messages[1].error, /post count/);
    } finally { delete globalThis.self; }
});

test('prompt query boundaries preserve Unicode, punctuation and surrounding weighting syntax', () => {
    assert.deepEqual(tagQuery('sky, 日本'), { prefix: '日本', start: 5 });
    assert.deepEqual(tagQuery('(o_o)'), { prefix: '(o_o)', start: 0 });
    assert.deepEqual(tagQuery('<3'), { prefix: '<3', start: 0 });
    assert.deepEqual(tagQuery('sky, (日本', true), { prefix: '日本', start: 6 });
    assert.deepEqual(tagQuery('hatsune_miku_(vocaloid'), { prefix: 'hatsune_miku_(vocaloid', start: 0 });
    assert.deepEqual(tagQuery('foo\nmiku/vocal'), { prefix: 'miku/vocal', start: 4 });
    assert.deepEqual(tagQuery('🎨🎨'), { prefix: '🎨🎨', start: 0 });
    assert.equal(tagQuery('sky, '), null);
    assert.equal(tagQuery('(', true), null);
});
