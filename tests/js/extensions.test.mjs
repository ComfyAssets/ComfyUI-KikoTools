import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

function load(file, extra = {}) {
    const extensions = [];
    const timers = new Map();
    const app = { registerExtension: extension => extensions.push(extension), canvas: {}, graph: { setDirtyCanvas() {} } };
    const context = vm.createContext({
        app, console: { log() {}, error() {} },
        setTimeout: callback => { const id = Symbol(); timers.set(id, callback); return id; },
        clearTimeout: id => timers.delete(id),
        ...extra,
    });
    const filename = fileURLToPath(new URL(`../../web/${file}`, import.meta.url));
    vm.runInContext(readFileSync(filename, 'utf8').replace(/^import .*;\s*$/gm, match => match.replace(/[^\r\n]/g, ' ')), context, { filename });
    return { extension: extensions[0], app, timers, context };
}

async function dimensionNode(preset, options = ['custom', '832×1216 - portrait', '1216×832 - landscape']) {
    const { extension, app } = load('width_height_swap.js');
    let originalCreated = 0;
    class Node {
        constructor() {
            this.originalPresetCalls = 0;
            this.widgets = [
                { name: 'preset', value: preset, options: { values: options }, callback(value, canvas, node) { node.originalPresetCalls++; } },
                { name: 'width', value: 832 }, { name: 'height', value: 1216 },
            ];
            this.graph = app.graph;
        }
        onNodeCreated() { originalCreated++; }
    }
    await extension.beforeRegisterNodeDef(Node, { name: 'WidthHeightSelector' }, app);
    const node = new Node();
    node.onNodeCreated();
    assert.equal(originalCreated, 1);
    return node;
}

test('custom dimensions swap and callbacks receive the actual node', async () => {
    const node = await dimensionNode('custom');
    const calls = [];
    for (const widget of node.widgets.slice(1)) widget.callback = (value, canvas, owner) => calls.push({ value, owner });
    node.swapDimensions();
    assert.deepEqual(node.widgets.map(widget => widget.value), ['custom', 1216, 832]);
    assert.equal(calls.length, 2);
    for (const call of calls) assert.equal(call.owner, node);
});

test('formatted preset swaps to its matching landscape preset without throwing', async () => {
    const node = await dimensionNode('832×1216 - portrait');
    node.swapDimensions();
    assert.deepEqual(node.widgets.map(widget => widget.value), ['1216×832 - landscape', 1216, 832]);
});

test('a preset without a reverse switches to custom dimensions', async () => {
    const node = await dimensionNode('832×1216 - portrait', ['custom', '832×1216 - portrait']);
    node.swapDimensions();
    assert.deepEqual(node.widgets.map(widget => widget.value), ['custom', 1216, 832]);
});

test('preset changes preserve original callbacks and update both dimensions', async () => {
    const node = await dimensionNode('custom');
    node.widgets[0].callback('1216×832 - landscape', {}, node);
    assert.deepEqual(node.widgets.slice(1).map(widget => widget.value), [1216, 832]);
    assert.equal(node.extractResolutionFromPreset('custom'), null);
    assert.equal(node.originalPresetCalls, 1);
});

test('unrelated node definitions retain their lifecycle methods', async () => {
    const { extension, app } = load('width_height_swap.js');
    class Node { onNodeCreated() {} }
    const original = Node.prototype.onNodeCreated;
    await extension.beforeRegisterNodeDef(Node, { name: 'OtherNode' }, app);
    assert.equal(Node.prototype.onNodeCreated, original);
});

test('Gemini repeated execution restores the user color and removal cancels its timer', async () => {
    const { extension, app, timers } = load('gemini_prompt_ui.js');
    let removed = 0;
    class Node { onRemoved() { removed++; } }
    await extension.beforeRegisterNodeDef(Node, { name: 'GeminiPrompt' }, app);
    const node = new Node();
    node.status = { value: 'Ready' };
    node.bgcolor = '#123456';
    node.onExecuted({});
    node.onExecuted({ output: { prompt: ['Error: unavailable'] } });
    assert.equal(timers.size, 1);
    assert.equal(node.bgcolor, '#552222');
    [...timers.values()][0]();
    assert.equal(node.bgcolor, '#123456');
    assert.equal(node.status.value, 'Ready');
    timers.clear();
    node.onExecuted({});
    node.onRemoved();
    assert.equal(timers.size, 0);
    assert.equal(removed, 1);
});

test('execution following respects enablement and ignores missing nodes', async () => {
    const settings = new Map();
    const listeners = new Map();
    const centered = [];
    const extensions = [];
    const node = { id: '7', type: 'DisplayAny', title: 'Display' };
    const app = {
        registerExtension: extension => extensions.push(extension),
        ui: { settings: { addSetting: setting => settings.set(setting.id, setting.defaultValue), getSettingValue: id => settings.get(id) } },
        graph: { _nodes: [node], getNodeById: id => id === node.id ? node : undefined },
        canvas: { centerOnNode: node => centered.push(node) }, runningNodeId: '7',
    };
    load('kiko_follow_execution.js', { app, api: { addEventListener: (name, callback) => listeners.set(name, callback) } });
    const extension = extensions[0];
    await extension.init();
    await extension.setup();
    assert.equal(extension.getCanvasMenuItems().length, 0);
    settings.set('kikotools.follow_execution.enabled', true);
    settings.set('kikotools.follow_execution.auto_start', true);
    listeners.get('execution_start')();
    listeners.get('executing')({ detail: '7' });
    listeners.get('executing')({ detail: 'missing' });
    assert.deepEqual(centered, [node]);
    settings.set('kikotools.follow_execution.enabled', false);
    listeners.get('execution_start')();
    listeners.get('executing')({ detail: '7' });
    assert.equal(centered.length, 1);
});


test('gallery HTML escaping handles filenames and attribute delimiters', () => {
    const { context } = load('kiko_local_image_loader.js', { document: { getElementById: () => ({}) } });
    const escape = vm.runInContext('escapeHtml', context);
    assert.equal(escape(null), '');
    assert.equal(escape(`<img src="x" onerror='run()'>&`), '&lt;img src=&quot;x&quot; onerror=&#39;run()&#39;&gt;&amp;');
});

test('gallery HTTP errors preserve actionable server detail and handle non-JSON responses', async () => {
    const { context } = load('kiko_local_image_loader.js', { document: { getElementById: () => ({}) } });
    const describe = vm.runInContext('describeHttpError', context);
    assert.equal(await describe({ status: 403, json: async () => ({ error: 'Choose an allowed root' }) }), 'Choose an allowed root');
    assert.match(await describe({ status: 403, json: async () => { throw new Error('not JSON'); } }), /allowed folders/);
    assert.match(await describe({ status: 400, json: async () => ({}) }), /Invalid path/);
});

test('gallery HTTP errors cover null bodies, message details, and generic status fallbacks', async () => {
    const { context } = load('kiko_local_image_loader.js', { document: { getElementById: () => ({}) } });
    const describe = vm.runInContext('describeHttpError', context);
    for (const [status, body, expected] of [
        [400, { error: 'Invalid directory' }, 'Invalid directory'],
        [403, { message: 'Not an allowed root' }, 'Not an allowed root'],
        [400, null, 'Invalid path or request'],
        [500, { error: 'Storage unavailable' }, 'Storage unavailable'],
        [404, { message: 'Missing image' }, 'Missing image'],
        [502, null, 'Request failed (HTTP 502)'],
        [503, {}, 'Request failed (HTTP 503)'],
    ]) assert.equal(await describe({ status, json: async () => body }), expected);
});
