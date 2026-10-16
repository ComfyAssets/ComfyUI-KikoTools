import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import { bindDimensionPresets, extractResolutionFromPreset, swapDimensions } from '../../web/ui/dimensions.js';

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

async function dimensionNode(preset, options = ['custom', '832×1216 - portrait', '1216×832 - landscape'], file = 'width_height_swap.js') {
    const { extension, app } = load(file, { bindDimensionPresets, extractResolutionFromPreset, swapDimensions, mountDimensionSwap() {} });
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
    await extension.beforeRegisterNodeDef(Node, { name: file === 'width_height_swap.js' ? 'WidthHeightSelector' : 'EmptyLatentBatch' }, app);
    Node.prototype.createSwapButton = () => {};
    const node = new Node();
    node.onNodeCreated();
    assert.equal(originalCreated, 1);
    return node;
}

for (const file of ['width_height_swap.js', 'empty_latent_batch_swap.js']) {
test(`${file}: custom dimensions swap and callbacks receive the actual node`, async () => {
    const node = await dimensionNode('custom', undefined, file);
    const calls = [];
    for (const widget of node.widgets.slice(1)) widget.callback = (value, canvas, owner) => calls.push({ value, owner });
    node.swapDimensions();
    assert.deepEqual(node.widgets.map(widget => widget.value), ['custom', 1216, 832]);
    assert.equal(calls.length, 2);
    for (const call of calls) assert.equal(call.owner, node);
});

test(`${file}: formatted preset swaps to its matching landscape preset without throwing`, async () => {
    const node = await dimensionNode('832×1216 - portrait', undefined, file);
    node.swapDimensions();
    assert.deepEqual(node.widgets.map(widget => widget.value), ['1216×832 - landscape', 1216, 832]);
});

test(`${file}: a preset without a reverse switches to custom dimensions`, async () => {
    const node = await dimensionNode('832×1216 - portrait', ['custom', '832×1216 - portrait'], file);
    node.swapDimensions();
    assert.deepEqual(node.widgets.map(widget => widget.value), ['custom', 1216, 832]);
});

test(`${file}: preset changes preserve original callbacks and update both dimensions`, async () => {
    const node = await dimensionNode('custom', undefined, file);
    node.widgets[0].callback('1216×832 - landscape', {}, node);
    assert.deepEqual(node.widgets.slice(1).map(widget => widget.value), [1216, 832]);
    assert.equal(node.extractResolutionFromPreset('custom'), null);
    assert.equal(node.originalPresetCalls, 1);
});

test(`${file}: a preset swap notifies each dimension callback exactly once`, async () => {
    const node = await dimensionNode('832×1216 - portrait', undefined, file);
    const calls = [];
    for (const widget of node.widgets.slice(1)) widget.callback = function (value, canvas, owner) { calls.push({ name: this.name, value, owner }); };
    node.swapDimensions();
    assert.deepEqual(calls.map(call => [call.name, call.value]), [['width', 1216], ['height', 832]]);
    assert.equal(node.originalPresetCalls, 1);
    for (const call of calls) assert.equal(call.owner, node);
});

test(`${file}: ASCII resolutions match reversed presets and unfamiliar formatted presets update dimensions`, async () => {
    const node = await dimensionNode('832x1216 - portrait', ['custom', '832x1216 - portrait', '1216x832 - landscape'], file);
    node.swapDimensions();
    assert.deepEqual(node.widgets.map(widget => widget.value), ['1216x832 - landscape', 1216, 832]);
    node.widgets[0].callback('2040×1080 - future preset', {}, node);
    assert.deepEqual(node.widgets.slice(1).map(widget => widget.value), [2040, 1080]);
});

test(`${file}: malformed presets do not write invalid dimensions`, async () => {
    const node = await dimensionNode('invalidx960', undefined, file);
    node.swapDimensions();
    assert.deepEqual(node.widgets.map(widget => widget.value), ['invalidx960', 832, 1216]);
});

test(`${file}: unrelated node definitions retain their lifecycle methods`, async () => {
    const { extension, app } = load(file);
    class Node { onNodeCreated() {} }
    const original = Node.prototype.onNodeCreated;
    await extension.beforeRegisterNodeDef(Node, { name: 'OtherNode' }, app);
    assert.equal(Node.prototype.onNodeCreated, original);
});

test(`${file}: creation preserves hook arguments, results and existing canvas hooks`, async () => {
    const { extension, app } = load(file, { bindDimensionPresets, extractResolutionFromPreset, swapDimensions, mountDimensionSwap() {} });
    class Node {
        constructor() { this.widgets = []; }
        onNodeCreated(value) { this.received = value; return 'original result'; }
        onDrawForeground() {}
        onMouseDown() {}
        onMouseMove() {}
    }
    const hooks = [Node.prototype.onDrawForeground, Node.prototype.onMouseDown, Node.prototype.onMouseMove];
    await extension.beforeRegisterNodeDef(Node, { name: file === 'width_height_swap.js' ? 'WidthHeightSelector' : 'EmptyLatentBatch' }, app);
    const node = new Node();
    assert.equal(node.onNodeCreated('original argument'), 'original result');
    assert.equal(node.received, 'original argument');
    assert.deepEqual([Node.prototype.onDrawForeground, Node.prototype.onMouseDown, Node.prototype.onMouseMove], hooks);
});

test(`${file}: nodes without an existing creation hook initialize safely`, async () => {
    const { extension, app } = load(file, { bindDimensionPresets, extractResolutionFromPreset, swapDimensions, mountDimensionSwap() {} });
    class Node { constructor() { this.widgets = []; } }
    await extension.beforeRegisterNodeDef(Node, { name: file === 'width_height_swap.js' ? 'WidthHeightSelector' : 'EmptyLatentBatch' }, app);
    assert.equal(new Node().onNodeCreated(), undefined);
});
}

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

async function followFixture() {
    const settings = new Map();
    const definitions = new Map();
    const centered = [];
    const api = new EventTarget();
    let extension;
    const node = { id: '7', type: 'DisplayAny', pos: [10, 20], getTitle: () => 'Display' };
    const app = {
        registerExtension: value => { extension = value; },
        ui: { settings: {
            addSetting(value) { definitions.set(value.id, value); settings.set(value.id, value.defaultValue); },
            getSettingValue: key => settings.get(key),
        } },
        graph: { _nodes: [node], getNodeById: id => app.graph._nodes.find(node => node.id === id) },
        canvas: { centerOnNode: node => centered.push(node) }, runningNodeId: '7',
    };
    load('kiko_follow_execution.js', { app, api });
    await extension.init();
    function set(key, value) {
        const id = `kikotools.follow_execution.${key}`;
        settings.set(id, value);
        definitions.get(id).onChange?.(value);
    }
    const emit = (type, detail = null) => {
        const event = new Event(type);
        event.detail = detail;
        api.dispatchEvent(event);
    };
    return { extension, app, node, settings, centered, emit, set };
}

test('Follow Execution stops immediately when disabled without a menu or execution restart', async () => {
    const f = await followFixture();
    f.set('enabled', true);
    f.set('auto_start', true);
    await f.extension.setup();
    f.emit('executing', '7');
    assert.equal(f.centered.length, 1);
    f.set('enabled', false);
    f.emit('executing', '7');
    assert.equal(f.centered.length, 1);
    f.set('enabled', true);
    f.emit('executing', '7');
    assert.equal(f.centered.length, 1);
    f.emit('execution_start');
    f.emit('executing', '7');
    assert.equal(f.centered.length, 2);
});

test('Follow Execution setup subscribes once per event across repeated setup', async () => {
    const f = await followFixture();
    f.set('enabled', true);
    f.set('auto_start', true);
    for (let i = 0; i < 3; i++) await f.extension.setup();
    f.emit('executing', '7');
    assert.deepEqual(f.centered, [f.node]);
});

test('Follow Execution menus safely group prototype-like types and sort nodes by position', async () => {
    const f = await followFixture();
    f.set('enabled', true);
    await f.extension.setup();
    f.app.graph._nodes = ['constructor', '__proto__', 'toString', 'constructor'].map((type, index) => ({
        id: String(index), type, pos: [30 - index * 10, 0], getTitle: () => type,
    }));
    const menu = f.extension.getCanvasMenuItems().find(item => item?.content === '🫶 Go to node');
    const options = menu.submenu.options;
    assert.deepEqual(Array.from(options, item => item.content), ['__proto__', 'constructor', 'toString']);
    const constructors = options[1].submenu.options;
    assert.match(constructors[0].content, /#3 \(0, 0\)/);
    assert.match(constructors[1].content, /#0 \(30, 0\)/);
    constructors[0].callback();
    assert.equal(f.centered[0], f.app.graph._nodes[3]);
});

test('Follow Execution ignores a stale follow menu after disabling the feature', async () => {
    const f = await followFixture();
    f.set('enabled', true);
    await f.extension.setup();
    const follow = f.extension.getCanvasMenuItems()[1];
    f.set('enabled', false);
    follow.callback();
    assert.equal(f.centered.length, 0);
    f.set('enabled', true);
    f.emit('executing', '7');
    assert.equal(f.centered.length, 0);
});

test('Follow Execution does not resume after disabling and re-enabling between events', async () => {
    const f = await followFixture();
    f.set('enabled', true);
    f.set('auto_start', true);
    await f.extension.setup();
    f.set('enabled', false);
    f.set('enabled', true);
    f.emit('executing', '7');
    assert.equal(f.centered.length, 0);
});
