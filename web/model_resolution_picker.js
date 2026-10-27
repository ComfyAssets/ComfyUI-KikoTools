import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { createScope, mountTheme } from './ui/core.js';
import { swapDimensions } from './ui/dimensions.js';
import { mountDimensionSwap } from './ui/dimension-swap.js';
import { defaultEntry, deriveSelection, effectiveSize, megapixels, parseRatio, sizesForRatio } from './ui/resolution-picker.js';
import { createResolutionPickerView } from './views/resolution-picker.js';

const FAMILIES_ROUTE = '/kikotools/model_resolution/families';
const CUSTOM_CHIP = 'custom';
const FALLBACK_STEP = 8;
const NODE_SIZE = [340, 600];
const MIN_PANEL_HEIGHT = 320;
const WRAPPED_WIDGETS = ['model', 'width', 'height'];

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
    let view;

    const readSize = () => ['width', 'height'].map(name => Number(widgetOf(node, name)?.value));

    function buildState() {
        const [width, height] = readSize();
        const wired = isWiredIn(node, 'width') || isWiredIn(node, 'height');
        const model = widgetOf(node, 'model')?.value;
        const empty = { disabled: true, chips: [], customOpen: false, ratioText: '', entries: [] };
        if (wired) return { ...empty, header: 'Dimensions are wired in' };
        if (failed || (payload && !Number.isFinite(width + height))) {
            const [w, h] = effectiveSize(null, width, height);
            return { ...empty, header: `${w} × ${h}` };
        }
        if (!payload) return { ...empty, header: 'Loading sizes…' };
        const selection = deriveSelection(payload, model, width, height);
        const { family, chip } = selection;
        const [w, h] = effectiveSize(family, width, height);
        const custom = node.resolutionCustom;
        const ratio = custom.open ? parseRatio(custom.text) : null;
        let list = [];
        if (family && custom.open) list = ratio ? sizesForRatio(family, ratio) : [];
        else if (family && chip) list = family.sizes[chip] || [];
        const showCustom = custom.open || selection.custom;
        const chips = payload.chips.map(id => ({
            id, label: id, active: !showCustom && chip === id, disabled: !family?.sizes[id]?.length,
        }));
        chips.push({ id: CUSTOM_CHIP, label: 'Custom ratio', active: showCustom, disabled: !family });
        return {
            disabled: false,
            header: `${w} × ${h} · ${chip || selection.ratioText} · ${megapixels(w, h)} MP`,
            chips,
            customOpen: custom.open,
            ratioText: custom.text,
            entries: list.map(([ew, eh]) => ({ w: ew, h: eh, active: ew === width && eh === height })),
            selection,
        };
    }

    function render() {
        if (scope.signal.aborted) return;
        const state = buildState();
        view.render(state);
        const swap = node.swapButtonWidget?.element?.querySelector('button');
        if (swap) swap.disabled = state.header === 'Dimensions are wired in';
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

    const actions = {
        selectChip(chip) {
            if (!payload) return;
            node.resolutionCustom.open = false;
            const { family, entryIndex, chip: current } = currentSelection();
            const entry = family && defaultEntry(family, chip);
            if (!entry || (current === chip && entryIndex >= 0)) return render();
            writeSize(entry[0], entry[1]);
        },
        openCustom() {
            if (!payload) return;
            node.resolutionCustom = { open: true, text: currentSelection().ratioText };
            render();
        },
        commitRatio(text) {
            node.resolutionCustom.text = text;
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
            if (!writing) render();
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

    render();
    loadFamilies(api).then(
        loaded => {
            payload = loaded;
            render();
        },
        () => {
            if (scope.signal.aborted) return;
            failed = true;
            view.setStatus('Sizes unavailable; type width and height', true);
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
