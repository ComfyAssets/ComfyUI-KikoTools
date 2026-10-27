import { createButton } from '../ui/core.js';

const CUSTOM_CHIP = 'custom';

function createToggle(text, pressed, disabled) {
    const button = createButton(text, '');
    button.setAttribute('aria-pressed', String(pressed));
    button.disabled = disabled;
    return button;
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

    return {
        element, input,
        setStatus(text, isError = false) {
            status.textContent = text;
            status.dataset.error = String(Boolean(isError));
        },
        render(state) {
            header.textContent = state.header;
            chips.replaceChildren(...state.chips.map(chip => {
                const button = createToggle(chip.label, chip.active, state.disabled || chip.disabled);
                button.dataset.chip = chip.id;
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
            if (state.error !== undefined) this.setStatus(state.error || '', Boolean(state.error));
        },
    };
}
