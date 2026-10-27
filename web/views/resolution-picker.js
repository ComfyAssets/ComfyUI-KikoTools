import { createButton } from '../ui/core.js';

const CUSTOM_CHIP = 'custom';

function createToggle(text, pressed, disabled) {
    const button = createButton(text, '');
    button.setAttribute('aria-pressed', String(pressed));
    button.disabled = disabled;
    return button;
}

const SHAPE_LONG_SIDE = 18;
const SHAPE_MIN_SIDE = 6;

function createShape(chipId) {
    const [w, h] = chipId.split(':').map(Number);
    const short = Math.max(SHAPE_MIN_SIDE, Math.round((SHAPE_LONG_SIDE * Math.min(w, h)) / Math.max(w, h)));
    const shape = document.createElement('span');
    shape.className = 'ca-resolution-shape';
    shape.setAttribute('aria-hidden', 'true');
    shape.style.width = `${w >= h ? SHAPE_LONG_SIDE : short}px`;
    shape.style.height = `${h >= w ? SHAPE_LONG_SIDE : short}px`;
    return shape;
}

export function createResolutionPickerView(scope, actions) {
    const element = document.createElement('div');
    element.className = 'ca-tools ca-resolution-picker';
    const header = document.createElement('p');
    header.className = 'ca-resolution-header';
    const chips = document.createElement('div');
    chips.className = 'ca-resolution-chips';
    chips.setAttribute('role', 'group');
    chips.setAttribute('aria-label', 'Aspect ratio');
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'ca-resolution-ratio';
    input.placeholder = '16:9';
    input.setAttribute('aria-label', 'Custom ratio');
    input.hidden = true;
    const sizes = document.createElement('div');
    sizes.className = 'ca-resolution-sizes';
    sizes.setAttribute('role', 'group');
    sizes.setAttribute('aria-label', 'Resolution');
    const status = document.createElement('p');
    status.className = 'ca-resolution-status';
    status.setAttribute('role', 'status');
    element.append(header, chips, input, sizes, status);

    scope.listen(chips, 'click', event => {
        const button = event.target.closest('button[data-chip]');
        if (!button || button.disabled) return;
        if (button.dataset.chip === CUSTOM_CHIP) actions.openCustom();
        else actions.selectChip(button.dataset.chip);
    });
    scope.listen(sizes, 'click', event => {
        const button = event.target.closest('button[data-width]');
        if (button && !button.disabled) actions.selectSize(Number(button.dataset.width), Number(button.dataset.height));
    });
    scope.listen(input, 'keydown', event => {
        if (event.key === 'Enter') actions.commitRatio(input.value);
    });
    scope.listen(input, 'change', () => actions.commitRatio(input.value));

    let message = '';
    let isMessageError = false;
    let warning = '';
    const showStatus = () => {
        status.textContent = message || warning;
        status.dataset.error = String(Boolean(message) && isMessageError);
    };

    return {
        element, input,
        setStatus(text, isError = false) {
            message = text;
            isMessageError = Boolean(isError);
            showStatus();
        },
        setWarning(text) {
            warning = text;
            showStatus();
        },
        render(state) {
            const focused = document.activeElement;
            const focusSelector = chips.contains(focused) ? `button[data-chip="${focused.dataset.chip}"]`
                : sizes.contains(focused) ? `button[data-width="${focused.dataset.width}"][data-height="${focused.dataset.height}"]` : null;
            header.textContent = state.header;
            chips.replaceChildren(...state.chips.map(chip => {
                const button = createToggle(chip.label, chip.active, state.disabled || chip.disabled);
                button.dataset.chip = chip.id;
                if (chip.id !== CUSTOM_CHIP) button.prepend(createShape(chip.id));
                return button;
            }));
            input.hidden = !state.customOpen;
            input.disabled = state.disabled;
            if (state.customOpen && document.activeElement !== input && input.value !== state.ratioText) input.value = state.ratioText;
            sizes.replaceChildren(...state.entries.map(entry => {
                const button = createToggle(`${entry.w} × ${entry.h}`, entry.active, state.disabled);
                button.dataset.width = entry.w;
                button.dataset.height = entry.h;
                return button;
            }));
            if (focusSelector) element.querySelector(focusSelector)?.focus();
            if (state.error !== undefined) this.setStatus(state.error || '', Boolean(state.error));
        },
    };
}
