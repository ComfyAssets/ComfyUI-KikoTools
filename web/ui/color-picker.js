import { createButton, createField, createScope, createSlider, mountTheme } from './core.js';
import { hexToHsv, hsvToHex, normalizeHex } from './color.js';

let nextPickerId = 0;
const presets = ['#0877BB', '#D0021B', '#F5A623', '#F8E71C', '#8B572A', '#7ED321',
    '#417505', '#BD10E0', '#9013FE', '#4A90D9', '#50E3C2', '#B8E986', '#000000', '#4A4A4A', '#9B9B9B', '#FFFFFF'];

class ColorPicker extends HTMLElement {
    connectedCallback() {
        if (this.scope && !this.scope.signal.aborted) return;
        this.scope = createScope();
        this.classList.add('ca-tools', 'ca-color-picker');
        mountTheme(this, this.settings, this.scope);
        const id = `ca-color-${++nextPickerId}`;
        this.trigger = createButton(`Choose ${this.label.toLowerCase()}`, 'ca-color-trigger');
        const swatch = document.createElement('span');
        swatch.className = 'ca-color-swatch';
        swatch.setAttribute('aria-hidden', 'true');
        this.trigger.prepend(swatch);
        const value = document.createElement('span');
        value.className = 'ca-color-value';
        this.dialog = document.createElement('dialog');
        this.dialog.className = 'ca-tools ca-color-dialog';
        mountTheme(this.dialog, this.settings, this.scope);
        this.dialog.setAttribute('aria-labelledby', `${id}-title`);
        const heading = document.createElement('h2');
        heading.id = `${id}-title`;
        heading.textContent = this.label;
        const hint = document.createElement('p');
        hint.textContent = 'Changes apply immediately.';
        hint.className = 'ca-color-hint';
        this.hexInput = document.createElement('input');
        Object.assign(this.hexInput, { type: 'text', maxLength: 7, autocomplete: 'off', spellcheck: false, pattern: '#?[0-9a-fA-F]{6}' });
        this.hexInput.setAttribute('aria-invalid', 'false');
        this.error = document.createElement('p');
        this.error.id = `${id}-error`;
        this.error.className = 'ca-color-error';
        this.error.setAttribute('role', 'alert');
        this.hexInput.setAttribute('aria-describedby', this.error.id);
        this.dialog.append(heading, hint, createField('Hex color', this.hexInput, `${id}-hex`), this.error);
        this.sliders = [];
        for (const [key, label, max, unit] of [['h', 'Hue', 360, 'degrees'], ['s', 'Saturation', 100, '%'], ['v', 'Brightness', 100, '%']]) {
            const field = createSlider(label, { id: `${id}-${key}`, min: 0, max, step: 1, value: 0, unit }, this.scope, next => {
                this.hsv[key] = next;
                this.hex = hsvToHex(this.hsv.h, this.hsv.s, this.hsv.v);
                this.sync();
                this.onChange(this.hex);
            });
            this.sliders.push({ field, key, unit });
            this.dialog.append(field);
        }
        const palette = document.createElement('div');
        palette.className = 'ca-color-presets';
        for (const color of presets) {
            const button = createButton('', 'ca-color-preset');
            button.setAttribute('aria-label', `Use color ${color}`);
            button.style.setProperty('--ca-picked-color', color);
            button.dataset.color = color.toLowerCase();
            this.scope.listen(button, 'click', () => this.applyHex(color));
            palette.append(button);
        }
        const done = createButton('Done', 'ca-primary');
        done.classList.add('ca-color-done');
        this.dialog.append(palette, done);
        this.replaceChildren(this.trigger, value);
        document.body.append(this.dialog);
        this.valueDisplay = value;
        this.scope.listen(this.trigger, 'click', () => this.dialog.showModal());
        this.scope.listen(done, 'click', () => this.dialog.close());
        this.scope.listen(this.dialog, 'keydown', event => event.stopPropagation());
        this.scope.listen(this.dialog, 'close', () => { if (this.isConnected) this.trigger.focus(); });
        this.scope.listen(this.hexInput, 'change', () => this.applyHex(this.hexInput.value));
        this.scope.cleanup(() => {
            if (this.dialog.open) this.dialog.close();
            this.dialog.remove();
            this.replaceChildren();
        });
        this.sync();
    }

    disconnectedCallback() {
        const scope = this.scope;
        queueMicrotask(() => { if (!this.isConnected) scope.dispose(); });
    }

    applyHex(value) {
        const hex = normalizeHex(value);
        if (!hex) {
            this.hexInput.setAttribute('aria-invalid', 'true');
            this.error.textContent = 'Use six hexadecimal digits, for example #0877BB.';
            return;
        }
        this.hex = hex;
        this.hsv = hexToHsv(hex);
        this.sync();
        this.onChange(hex);
    }

    sync() {
        this.style.setProperty('--ca-picked-color', this.hex);
        this.hexInput.value = this.hex.toUpperCase();
        this.hexInput.setAttribute('aria-invalid', 'false');
        this.error.textContent = '';
        this.valueDisplay.textContent = this.hex.toUpperCase();
        for (const { field, key, unit } of this.sliders) {
            const value = Math.round(this.hsv[key]);
            const input = field.querySelector('input');
            input.value = value;
            input.setAttribute('aria-valuetext', `${value} ${unit}`);
            field.querySelector('output').value = key === 'h' ? `${value}°` : `${value} %`;
        }
        this.dialog.querySelectorAll('button[data-color]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.color === this.hex)));
    }
}

if (!customElements.get('ca-color-picker')) customElements.define('ca-color-picker', ColorPicker);

export function createColorPicker(value, onChange, settings, label = 'Color') {
    const picker = document.createElement('ca-color-picker');
    picker.hex = normalizeHex(value) || '#0877bb';
    picker.hsv = hexToHsv(picker.hex);
    picker.onChange = onChange;
    picker.settings = settings;
    picker.label = label;
    return picker;
}
