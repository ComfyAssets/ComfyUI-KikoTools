import { createButton, createScope, createSwitch, mountTheme } from '../ui/core.js';
import { createDialog } from '../ui/dialog.js';

export function openAutocompleteSettings(autocomplete, settings, fallbackFocus) {
    const existing = autocomplete.settingsDialog;
    if (existing && !existing.scope.signal.aborted) {
        existing.element.querySelector('input').focus();
        return existing;
    }
    autocomplete.hideSuggestions();
    const dialog = createDialog({ title: 'Embedding Autocomplete Settings', settings, fallbackFocus });
    autocomplete.settingsDialog = dialog;
    dialog.element.classList.add('ca-autocomplete-settings');
    const form = document.createElement('form');
    form.id = `${dialog.element.id}-form`;
    const fields = new Map();
    for (const [key, label] of [['enabled', 'Enable Autocomplete'], ['showEmbeddings', 'Show Embeddings'], ['showLoras', 'Show LoRAs'], ['showCustomWords', 'Show Custom Words']]) {
        const field = createSwitch(label, '', `${form.id}-${key}`);
        const input = field.querySelector('input');
        input.checked = autocomplete.settings[key] !== false;
        fields.set(key, input);
        form.append(field);
    }
    const hint = document.createElement('p');
    hint.className = 'ca-dialog-hint';
    hint.textContent = 'Choose which sources appear while typing. Your saved triggers, matching and insertion preferences are preserved.';
    const status = document.createElement('p');
    status.role = 'status';
    status.className = 'ca-dialog-error';
    dialog.body.append(hint, form, status);
    const cancel = createButton('Cancel');
    const save = createButton('Save Settings', 'ca-primary');
    save.type = 'submit';
    save.setAttribute('form', form.id);
    dialog.actions.append(cancel, save);
    dialog.scope.listen(cancel, 'click', () => dialog.close('cancel'));
    dialog.scope.listen(form, 'submit', event => {
        event.preventDefault();
        const previous = { ...autocomplete.settings };
        for (const [key, input] of fields) autocomplete.settings[key] = input.checked;
        if (!autocomplete.saveSettings()) {
            Object.assign(autocomplete.settings, previous);
            status.textContent = 'Could not save settings. Check browser storage and try again.';
            return;
        }
        if (autocomplete.settings.showEmbeddings || autocomplete.settings.showLoras) autocomplete.fetchResourcesDebounced();
        if (autocomplete.settings.showCustomWords && !previous.showCustomWords && autocomplete.settings.customWordsUrl) autocomplete.loadCustomWords(autocomplete.settings.customWordsUrl);
        dialog.close('save');
    });
    dialog.scope.cleanup(() => { if (autocomplete.settingsDialog === dialog) autocomplete.settingsDialog = null; });
    dialog.open(fields.get('enabled'));
    return dialog;
}

export function createAutocompleteLauncher(autocomplete, settings, fallbackFocus) {
    if (!customElements.get('kiko-autocomplete-launcher')) {
        customElements.define('kiko-autocomplete-launcher', class extends HTMLElement {
            connectedCallback() {
                if (this.scope && !this.scope.signal.aborted) return;
                this.scope = createScope();
                this.className = 'ca-tools ca-autocomplete-launcher';
                mountTheme(this, this.settings, this.scope);
                const button = createButton('Open Settings', 'ca-primary');
                this.replaceChildren(button);
                this.scope.listen(button, 'click', () => {
                    this.dialog = openAutocompleteSettings(this.autocomplete, this.settings, this.fallbackFocus);
                    this.dialog.owner = this;
                });
                this.scope.cleanup(() => { if (this.dialog?.owner === this) this.dialog.close('removed'); });
            }
            disconnectedCallback() {
                const scope = this.scope;
                queueMicrotask(() => { if (!this.isConnected) scope.dispose(); });
            }
        });
    }
    const row = document.createElement('tr');
    row.className = 'kikotools-settings-row';
    const label = document.createElement('td');
    label.textContent = 'Embedding Autocomplete Configuration';
    const value = document.createElement('td');
    const launcher = document.createElement('kiko-autocomplete-launcher');
    Object.assign(launcher, { autocomplete, settings, fallbackFocus });
    value.append(launcher);
    row.append(label, value);
    return row;
}
