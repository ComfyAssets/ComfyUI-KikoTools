const swapping = new WeakSet();

export function extractResolutionFromPreset(value) {
    return typeof value === 'string' && value !== 'custom' ? value.split(' - ')[0].trim() : null;
}

export function dimensionsFromPreset(value) {
    const match = extractResolutionFromPreset(value)?.match(/^(\d+)\s*[×x]\s*(\d+)$/);
    if (!match) return null;
    const dimensions = match.slice(1).map(Number);
    return dimensions.every(value => Number.isSafeInteger(value) && value > 0) ? dimensions : null;
}

function widgets(node) {
    return ['preset', 'width', 'height'].map(name => node.widgets.find(widget => widget.name === name));
}

function notifyDimensions(width, height, canvas, node, pos, event) {
    for (const widget of [width, height]) widget.callback?.(widget.value, canvas, node, pos, event);
}

export function bindDimensionPresets(node, app) {
    const [preset] = widgets(node);
    if (!preset) return;
    const callback = preset.callback;
    preset.callback = function (value, canvas = app.canvas, owner = node, pos = [0, 0], event = null) {
        const result = callback?.apply(this, arguments);
        if (swapping.has(node)) return result;
        const dimensions = dimensionsFromPreset(value);
        const [, width, height] = widgets(node);
        if (dimensions && width && height) {
            [width.value, height.value] = dimensions;
            notifyDimensions(width, height, canvas, owner, pos, event);
        }
        return result;
    };
}

export function swapDimensions(node, app) {
    const [preset, width, height] = widgets(node);
    if (!preset || !width || !height || swapping.has(node)) return;
    const custom = preset.value === 'custom';
    const dimensions = custom ? [width.value, height.value] : dimensionsFromPreset(preset.value);
    if (!dimensions) return;
    const [w, h] = dimensions;
    let match;
    if (!custom) {
        let options = Array.isArray(preset.options) ? preset.options : preset.options?.values;
        if (typeof options === 'function') options = options.call(preset);
        match = (Array.isArray(options) ? options : []).find(value => {
            const parsed = dimensionsFromPreset(value);
            return parsed?.[0] === h && parsed?.[1] === w;
        });
    }
    swapping.add(node);
    try {
        [width.value, height.value] = [h, w];
        if (!custom) {
            preset.value = match || 'custom';
            preset.callback?.(preset.value, app.canvas, node, [0, 0], null);
        }
        notifyDimensions(width, height, app.canvas, node, [0, 0], null);
        node.graph?.setDirtyCanvas?.(true, true);
    } finally {
        swapping.delete(node);
    }
}
