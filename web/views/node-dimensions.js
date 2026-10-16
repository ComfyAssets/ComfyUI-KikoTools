import { createButton, createField } from '../ui/core.js';
import { createDialog } from '../ui/dialog.js';

const activeDialogs = new WeakMap();

export function resolveNodeSize(values, minimum) {
    const size = values.map(Number);
    if (values.some(value => String(value).trim() === '') || size.some(value => !Number.isSafeInteger(value) || value <= 0)) return null;
    return size.map((value, index) => Math.max(value, minimum[index]));
}

export function showNodeDimensionsDialog(node, app) {
    const existing = activeDialogs.get(node);
    if (existing) {
        existing.querySelector('.width').focus();
        return existing;
    }
    const dialog = createDialog({ title: 'Node Dimensions', settings: app.ui.settings, fallbackFocus: app.canvas.canvas });
    const form = document.createElement('form');
    form.id = `${dialog.element.id}-form`;
    form.noValidate = true;
    const hint = document.createElement('p');
    hint.id = `${form.id}-hint`;
    hint.textContent = 'Minimum size is enforced based on node content.';
    hint.className = 'ca-dialog-hint';
    const fields = document.createElement('div');
    fields.className = 'ca-dimension-fields';
    const error = document.createElement('p');
    error.id = `${form.id}-error`;
    error.className = 'ca-dialog-error';
    error.setAttribute('aria-live', 'polite');
    const inputs = ['Width', 'Height'].map((name, index) => {
        const input = document.createElement('input');
        Object.assign(input, { type: 'number', min: '1', step: '1', required: true, value: String(Math.round(node.size[index])), className: name.toLowerCase() });
        input.setAttribute('aria-describedby', `${hint.id} ${error.id}`);
        fields.append(createField(`${name} (px)`, input, `${form.id}-${name.toLowerCase()}`));
        return input;
    });
    form.append(hint, fields, error);
    dialog.body.append(form);
    const cancel = createButton('Cancel');
    const apply = createButton('Apply', 'ca-primary');
    apply.type = 'submit';
    apply.setAttribute('form', form.id);
    dialog.actions.append(cancel, apply);
    dialog.scope.listen(cancel, 'click', () => dialog.close('cancel'));
    dialog.scope.listen(form, 'submit', event => {
        event.preventDefault();
        const size = resolveNodeSize(inputs.map(input => input.value), node.computeSize());
        if (!size) {
            error.textContent = 'Enter positive whole numbers for width and height.';
            for (const input of inputs) input.setAttribute('aria-invalid', String(!resolveNodeSize([input.value], [1])));
            inputs.find(input => input.getAttribute('aria-invalid') === 'true').focus();
            return;
        }
        node.setSize(size);
        node.setDirtyCanvas(true, true);
        dialog.close('apply');
    });
    const original = node.onRemoved;
    const onRemoved = function (...args) {
        dialog.close('removed');
        return original?.apply(this, args);
    };
    node.onRemoved = onRemoved;
    activeDialogs.set(node, dialog.element);
    dialog.scope.cleanup(() => {
        activeDialogs.delete(node);
        if (node.onRemoved === onRemoved) node.onRemoved = original;
    });
    dialog.open(inputs[0]);
    inputs[0].select();
    return dialog.element;
}
