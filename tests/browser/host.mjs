// A test double for the ComfyUI host; extension implementations load unchanged.
const extensions = [];
const settings = new Map();
const settingDefinitions = new Map();
const nodes = new Map();
let nextId = 1;
function el(tag, props = {}, children = []) {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(props)) {
        if (name === 'style') Object.assign(element.style, value);
        else if (name === 'parent') value.appendChild(element);
        else element[name] = value;
    }
    element.append(...children);
    return element;
}
const app = {
    registerExtension(extension) {
        if (extensions.some(item => item.name === extension.name)) throw new Error(`Duplicate extension ${extension.name}`);
        extensions.push(extension);
    },
    ui: { settings: {
        addSetting(setting) { settingDefinitions.set(setting.id, setting); if (!settings.has(setting.id)) settings.set(setting.id, setting.defaultValue); },
        getSettingValue: id => settings.get(id),
        setSettingValue(id, value) { settings.set(id, value); settingDefinitions.get(id)?.onChange?.(value); },
    }, dialog: { show: text => { const dialog = el('div', { className: 'host-dialog', textContent: text }); document.body.append(dialog); } } },
    graph: {
        _nodes: [],
        add(node) { this._nodes.push(node); nodes.set(String(node.id), node); },
        getNodeById: id => nodes.get(String(id)),
        setDirtyCanvas() {},
    },
    canvas: { selected_nodes: {}, centerOnNode(node) { app.centeredNode = node.id; } },
};
const api = new EventTarget();
api.fetchApi = (path, options) => fetch(path, options);
api.getEmbeddings = async () => [];
function widget(node, name, value, multiline = false) {
    const inputEl = el(multiline ? 'textarea' : 'input', { 'ariaLabel': name });
    const result = { name, inputEl, options: {}, callback() {}, onRemove() { inputEl.remove(); } };
    Object.defineProperty(result, 'value', { get: () => inputEl.value, set: value => { inputEl.value = value; } });
    result.value = value ?? '';
    inputEl.addEventListener('change', () => result.callback(result.value, app.canvas, node, [0, 0], null));
    node.widgets.push(result);
    node.element.append(inputEl);
    return result;
}
const widgets = { STRING(node, name, data) { return { widget: widget(node, name, '', data[1]?.multiline) }; } };
class HostNode {
    constructor(name, initial) {
        this.id = nextId++;
        this.type = name;
        this.title = name;
        this.widgets = [];
        this.size = [500, 300];
        this.pos = [0, 0];
        this.flags = {};
        this.inputs = [];
        this.properties = {};
        this.graph = app.graph;
        this.element = el('section', { className: 'host-node' });
        this.element.dataset.node = name;
        this.domElement = this.element;
        this.element.style.cssText = 'position:relative;width:min(800px,95vw);min-height:120px;margin:12px;border:1px solid #888;';
        document.querySelector('#nodes').append(this.element);
        for (const [key, value] of Object.entries(initial)) {
            const entry = name === 'TextInput' && key === 'text'
                ? widgets.STRING(this, key, ['STRING', { multiline: true }], app).widget
                : widget(this, key, value);
            entry.value = value;
            if (key === 'preset') entry.options.values = ['custom', '832×1216 - portrait', '1216×832 - landscape'];
        }
    }
    addDOMWidget(name, type, element, options = {}) { this.element.append(element); const result = { name, element, options, onRemove: () => element.remove() }; this.widgets.push(result); return result; }
    addWidget(type, name, value, callback, options = {}) {
        if (type !== 'button') { const entry = widget(this, name, value); entry.callback = callback; return entry; }
        const button = el('button', { textContent: name, onclick: () => callback() });
        this.element.append(button);
        const result = { type, name, value, callback, options, onRemove: () => button.remove() };
        this.widgets.push(result);
        return result;
    }
    addCustomWidget(entry) { this.widgets.push(entry); if (entry.type === 'button') { const button = el('button', { textContent: entry.text, onclick: () => entry.callback() }); this.element.append(button); entry.onRemove = () => button.remove(); } return entry; }
    setSize(size) { this.size = size; }
    computeSize() { return this.size; }
    onResize(size) { this.size = size; }
    setDirtyCanvas() {}
    configure(info) {
        this.properties = info.properties || {};
        const editable = this.widgets.filter(entry => entry.inputEl);
        (info.widgets_values || []).forEach((value, index) => { if (editable[index]) editable[index].value = value; });
        this.onConfigure?.(info);
    }
    onNodeCreated() { this.created = true; }
    onExecuted() { this.executions = (this.executions || 0) + 1; }
    onRemoved() { this.removed = true; }
}
async function createNode(name, initial = {}) {
    class Node extends HostNode {}
    Node.category = 'ComfyAssets';
    for (const extension of extensions) await extension.beforeRegisterNodeDef?.(Node, { name }, app);
    const node = new Node(name, initial);
    app.graph.add(node);
    node.onNodeCreated();
    return node.id;
}
function removeNode(id) {
    const node = nodes.get(String(id));
    node.onRemoved?.();
    for (const entry of node.widgets) { entry.onRemoved?.(); entry.onRemove?.(); }
    node.element.remove();
    nodes.delete(String(id));
    app.graph._nodes = app.graph._nodes.filter(item => item !== node);
    return node;
}
window.kikoHost = { app, api, widgets, el, extensions, settings, settingDefinitions, nodes, createNode, removeNode,
    emit: (name, detail) => api.dispatchEvent(new CustomEvent(name, { detail })) };
const manifest = await (await fetch('/__test__/state')).json();
for (const name of manifest.extensions) await import(`/extensions/kikotools/${name}`);
for (const extension of extensions) await extension.init?.(app);
for (const extension of extensions) await extension.setup?.(app);
window.kikoHost.ready = true;
document.body.dataset.ready = 'true';
