import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { createScope, mountTheme } from './ui/core.js';
import { swapDimensions } from './ui/dimensions.js';
import { mountDimensionSwap } from './ui/dimension-swap.js';
import { defaultEntry, deriveSelection, dropdownOptions, effectiveSize, megapixels, modelOptions, parseRatio, parseSizeLabel, sizeLabel, sizeOnModelChange, sizesForRatio } from './ui/resolution-picker.js';
import { createResolutionPickerView } from './views/resolution-picker.js';

const FAMILIES_ROUTE = '/kikotools/model_resolution/families';
const CUSTOM_CHIP = 'custom';
const CHIP_IDS = ['1:1', '4:5', '5:4', '3:4', '4:3', '2:3', '3:2', '9:16', '16:9', '21:9', '9:21'];
const UNAVAILABLE_STATUS = 'Sizes unavailable; type width and height';
const RATIO_ERROR = 'Enter a ratio like 16:9';
const FALLBACK_STEP = 8;
const NODE_SIZE = [340, 600];
const MIN_PANEL_HEIGHT = 320;
const LEGACY_VALUE_COUNT = 4;
const LEGACY_WIDGET_ORDER = ['model', 'width', 'height', 'batch_size'];
const WRAPPED_WIDGETS = ['model', 'resolution', 'width', 'height'];

let familiesPromise;

function loadFamilies(client) {
    if (!familiesPromise) {
        familiesPromise = client.fetchApi(FAMILIES_ROUTE)
            .then(response => {
                if (!response.ok) throw new Error(`Families request failed: ${response.status}`);
                return response.json();
            })
            .catch(error => {
                familiesPromise = undefined;
                throw error;
            });
    }
    return familiesPromise;
}

function isWiredIn(node, name) {
    return Boolean(node.inputs?.some(input => input.widget?.name === name && input.link != null));
}

function widgetOf(node, name) {
    return node.widgets?.find(widget => widget.name === name);
}

function mountPicker(node) {
    const scope = createScope();
    node.resolutionScope = scope;
    node.resolutionCustom = { open: false, text: '' };
    let payload = null;
    let failed = false;
    let writing = false;
    let lastChip = null;
    let modelLabel = widgetOf(node, 'model')?.value;
    let pendingModel = null;
    let view;
    let optionsKey = '';

    const readSize = () => ['width', 'height'].map(name => Number(widgetOf(node, name)?.value));

    function buildState() {
        const [width, height] = readSize();
        const wired = isWiredIn(node, 'width') || isWiredIn(node, 'height');
        const model = widgetOf(node, 'model')?.value;
        const staticChips = () => [...CHIP_IDS, CUSTOM_CHIP].map(id => ({
            id, label: id === CUSTOM_CHIP ? 'Custom ratio' : id, active: false, disabled: true,
        }));
        const empty = { disabled: true, chips: staticChips(), customOpen: false, ratioText: '', entries: [] };
        if (wired) return { ...empty, wired, header: 'Dimensions are wired in' };
        if (failed || (payload && !Number.isFinite(width + height))) {
            const [w, h] = effectiveSize(null, width, height);
            return { ...empty, header: `${w} × ${h}` };
        }
        if (!payload) return { ...empty, header: 'Loading sizes…' };
        const selection = deriveSelection(payload, model, width, height);
        const { family, chip } = selection;
        lastChip = chip;
        const [w, h] = effectiveSize(family, width, height);
        const custom = node.resolutionCustom;
        const ratio = custom.open ? parseRatio(custom.text) : null;
        let list = [];
        if (family && custom.open) list = ratio ? sizesForRatio(family, ratio) : [];
        else if (family && chip) list = family.sizes[chip] || [];
        const showCustom = custom.open || selection.custom;
        const chips = CHIP_IDS.map(id => ({
            id, label: id, active: !showCustom && chip === id, disabled: !family?.sizes[id]?.length,
        }));
        chips.push({ id: CUSTOM_CHIP, label: 'Custom ratio', active: showCustom, disabled: !family });
        return {
            wired: false,
            disabled: false,
            header: `${w} × ${h} · ${chip || selection.ratioText} · ${megapixels(w, h)} MP`,
            chips,
            customOpen: custom.open,
            ratioText: custom.text,
            entries: list.map(([ew, eh]) => ({ w: ew, h: eh, active: ew === width && eh === height })),
            selection,
        };
    }

    function syncResolution(state) {
        const widget = widgetOf(node, 'resolution');
        if (!widget) return;
        const selection = state.selection;
        if (!selection) {
            // Direct assignment fires no callback; a stale label must not override width/height.
            widget.value = 'custom';
            return;
        }
        const chip = state.customOpen || selection.custom ? null : selection.chip;
        const key = `${selection.family?.label}|${chip}`;
        if (key !== optionsKey) {
            optionsKey = key;
            widget.options.values = dropdownOptions(payload, selection.family?.label, chip);
        }
        const [width, height] = readSize();
        const label = selection.entryIndex >= 0 ? sizeLabel(width, height, selection.chip) : 'custom';
        widget.value = widget.options.values.includes(label) ? label : 'custom';
    }

    function syncModelOptions() {
        const widget = widgetOf(node, 'model');
        if (!widget || !payload) return;
        const values = modelOptions(payload, widget.value);
        const current = widget.options.values;
        if (!Array.isArray(current) || current.length !== values.length || current.some((item, index) => item !== values[index])) {
            widget.options.values = values;
        }
    }

    function render() {
        if (scope.signal.aborted) return;
        syncModelOptions();
        const state = buildState();
        view.render(state);
        syncResolution(state);
        const swap = node.swapButtonWidget?.element?.querySelector('button');
        if (swap) swap.disabled = state.wired;
    }

    function writeSize(w, h) {
        const width = widgetOf(node, 'width');
        const height = widgetOf(node, 'height');
        if (!width || !height || writing) return;
        writing = true;
        try {
            width.value = w;
            height.value = h;
            for (const widget of [width, height]) widget.callback?.(widget.value, app.canvas, node, [0, 0], null);
            node.graph?.setDirtyCanvas?.(true, true);
        } finally {
            writing = false;
        }
        render();
    }

    const currentSelection = () => {
        const [width, height] = readSize();
        return deriveSelection(payload, widgetOf(node, 'model')?.value, width, height);
    };

    function applyModelChange(label) {
        const [width, height] = readSize();
        const wired = isWiredIn(node, 'width') || isWiredIn(node, 'height');
        if (!payload || wired || !Number.isFinite(width + height)) return render();
        const [w, h] = sizeOnModelChange(payload, label, width, height, lastChip);
        if (w !== width || h !== height) writeSize(w, h);
        else render();
    }

    function applyPendingModelChange() {
        const pending = pendingModel;
        pendingModel = null;
        if (!pending || scope.signal.aborted || widgetOf(node, 'model')?.value !== pending.to) return;
        const [width, height] = readSize();
        const { chip } = deriveSelection(payload, pending.from, width, height);
        lastChip = chip;
        applyModelChange(pending.to);
    }

    const actions = {
        selectChip(chip) {
            if (!payload) return;
            view.setStatus('');
            node.resolutionCustom.open = false;
            const [width, height] = readSize();
            const { family } = currentSelection();
            const entry = family && defaultEntry(family, chip);
            const listed = family?.sizes[chip]?.some(([w, h]) => w === width && h === height);
            if (!entry || listed) return render();
            writeSize(entry[0], entry[1]);
        },
        openCustom() {
            if (!payload) return;
            node.resolutionCustom = { open: true, text: currentSelection().ratioText };
            render();
        },
        commitRatio(text) {
            const custom = node.resolutionCustom;
            if (!parseRatio(text)) {
                view.setStatus(RATIO_ERROR, true);
                return;
            }
            view.setStatus('');
            if (text.trim() === custom.text) return;
            custom.text = text.trim();
            render();
        },
        selectSize: writeSize,
    };

    view = createResolutionPickerView(scope, actions);
    node.setSize(NODE_SIZE);
    node.addDOMWidget('resolution_picker', 'div', view.element, {
        serialize: false, hideOnZoom: false, getMinHeight: () => MIN_PANEL_HEIGHT,
    });
    mountTheme(view.element, app.ui.settings, scope);
    scope.cleanup(() => view.element.remove());

    for (const name of WRAPPED_WIDGETS) {
        const widget = widgetOf(node, name);
        if (!widget) continue;
        const callback = widget.callback;
        widget.callback = function () {
            const result = callback?.apply(this, arguments);
            if (writing) return result;
            if (name === 'resolution') {
                const size = isWiredIn(node, 'width') || isWiredIn(node, 'height')
                    ? null : parseSizeLabel(arguments[0] ?? this.value);
                if (size) writeSize(size[0], size[1]);
                else render();
            } else if (name === 'model') {
                const label = arguments[0] ?? this.value;
                if (!payload && !failed) {
                    pendingModel = { from: pendingModel ? pendingModel.from : modelLabel, to: label };
                    modelLabel = label;
                    render();
                } else {
                    modelLabel = label;
                    applyModelChange(label);
                }
            }
            else render();
            return result;
        };
    }

    node.swapDimensions = () => {
        swapDimensions(node, app);
        render();
    };
    node.createSwapButton = () => mountDimensionSwap(node, app);
    node.createSwapButton();

    const onRemoved = node.onRemoved;
    node.onRemoved = function () {
        scope.dispose();
        return onRemoved?.apply(this, arguments);
    };

    // Workflows saved before the resolution widget carry four values
    // (model, width, height, batch_size) and load shifted by one slot.
    const onConfigure = node.onConfigure;
    node.onConfigure = function (info) {
        const result = onConfigure?.apply(this, arguments);
        const values = info?.widgets_values;
        if (Array.isArray(values) && values.length === LEGACY_VALUE_COUNT) {
            LEGACY_WIDGET_ORDER.forEach((name, index) => {
                const widget = widgetOf(node, name);
                if (widget) widget.value = values[index];
            });
            const resolution = widgetOf(node, 'resolution');
            if (resolution) resolution.value = 'custom';
            modelLabel = widgetOf(node, 'model')?.value;
            render();
        }
        return result;
    };

    const onConnectionsChange = node.onConnectionsChange;
    node.onConnectionsChange = function () {
        const result = onConnectionsChange?.apply(this, arguments);
        render();
        return result;
    };

    render();
    loadFamilies(api).then(
        loaded => {
            payload = loaded;
            view.setWarning(loaded.warnings?.[0] || '');
            if (pendingModel) applyPendingModelChange();
            else render();
        },
        () => {
            if (scope.signal.aborted) return;
            failed = true;
            view.setStatus(UNAVAILABLE_STATUS, true);
            render();
        },
    );
}

app.registerExtension({
    name: 'comfyassets.ModelResolutionPicker',
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== 'ModelResolutionPicker') return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            mountPicker(this);
            return result;
        };
    },
});
