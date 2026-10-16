import { createScope } from '../ui/core.js';
import { createTextOutputView } from '../views/text-output.js';

export function restoreDisplayOutput(data, kind, hasInputWidget) {
    if (data.kikoDisplay?.version === 1 && typeof data.kikoDisplay.text === 'string') return data.kikoDisplay.text;
    if (!Array.isArray(data.widgets_values)) return null;
    const values = data.widgets_values.slice(hasInputWidget && data.widgets_values.length > 1 ? 1 : 0);
    if (kind === 'any' && ['raw value', 'tensor shape'].includes(values[0])) values.shift();
    const strings = values.filter(value => typeof value === 'string');
    if (!strings.length) return null;
    if (kind === 'text' && strings[0] === '✓ Positive Prompt' && strings[2] === '✗ Negative Prompt') {
        return `Positive prompt: ${strings[1]}\nNegative prompt: ${strings[3]}`;
    }
    return kind === 'any' ? strings.join('\n') : strings[0];
}

function updateOutput(node, text) {
    if (node.displayOutput.scope.signal.aborted) return;
    node.displayOutput.text = text;
    node.displayOutput.view.update(text);
    node.setDirtyCanvas(true, true);
}

export function registerDisplayNode(nodeType, app, kind) {
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
        const result = onNodeCreated?.apply(this, arguments);
        const scope = createScope();
        const view = createTextOutputView(scope, kind, app.ui.settings);
        this.displayOutput = { scope, view, text: '' };
        this.addDOMWidget('kiko_display_output', 'div', view.element, {
            serialize: false, hideOnZoom: false,
            getMinHeight: () => kind === 'text' ? 240 : 180,
        });
        this.setSize([Math.max(this.size[0], kind === 'text' ? 400 : 450), Math.max(this.size[1], kind === 'text' ? 300 : 250)]);
        updateOutput(this, kind === 'text' ? 'Text will appear here after execution...' : 'Value will appear here...');
        return result;
    };
    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
        const result = onExecuted?.apply(this, arguments);
        if (typeof message?.text?.[0] === 'string') updateOutput(this, message.text[0]);
        return result;
    };
    const configure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (data) {
        const text = restoreDisplayOutput(data, kind, Boolean(this.inputs?.[0]?.widget));
        const result = configure?.apply(this, arguments);
        if (text !== null) updateOutput(this, text);
        return result;
    };
    const onSerialize = nodeType.prototype.onSerialize;
    nodeType.prototype.onSerialize = function (data) {
        const result = onSerialize?.apply(this, arguments);
        data.kikoDisplay = { version: 1, text: this.displayOutput.text };
        return result;
    };
    const onRemoved = nodeType.prototype.onRemoved;
    nodeType.prototype.onRemoved = function () {
        this.displayOutput.scope.dispose();
        return onRemoved?.apply(this, arguments);
    };
}
