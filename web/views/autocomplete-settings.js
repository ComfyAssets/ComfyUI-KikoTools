import { createButton, createField, createScope, createSwitch, mountTheme } from '../ui/core.js';
import { createDialog } from '../ui/dialog.js';
import { MAX_TAG_BYTES } from '../autocomplete/tags.js';
import { parseTagFile } from '../autocomplete/tag-storage.js';

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
    const group = (title, parent = form) => {
        const fieldset = document.createElement('fieldset');
        const legend = document.createElement('legend');
        legend.textContent = title;
        fieldset.append(legend);
        parent.append(fieldset);
        return fieldset;
    };
    const addSwitch = (parent, key, label) => {
        const field = createSwitch(label, '', `${form.id}-${key}`);
        const input = field.querySelector('input');
        input.checked = autocomplete.settings[key] !== false;
        fields.set(key, input);
        parent.append(field);
    };
    const addInput = (parent, key, label, type = 'text', limits = {}) => {
        const input = document.createElement('input');
        Object.assign(input, { type, value: autocomplete.settings[key] ?? '', ...limits });
        fields.set(key, input);
        parent.append(createField(label, input, `${form.id}-${key}`));
        return input;
    };
    const sources = group('Sources');
    for (const [key, label] of [['enabled', 'Enable Autocomplete'], ['showEmbeddings', 'Show Embeddings'], ['showLoras', 'Show LoRAs'], ['showCustomWords', 'Show Custom Words']]) addSwitch(sources, key, label);
    const tags = group('Tags and custom words');
    const count = document.createElement('p');
    count.className = 'ca-dialog-hint';
    count.textContent = `${autocomplete.customWords.length.toLocaleString()} tags loaded`;
    const hint = document.createElement('p');
    hint.className = 'ca-dialog-hint';
    hint.textContent = 'Import CSV or TXT, or load a URL. Lists replace the current tags when you save. Supports tag,frequency and tag,category,post_count,aliases. Maximum 32 MB.';
    const pack = document.createElement('a');
    pack.href = 'https://github.com/ComfyAssets/ComfyUI-KikoTools/releases/tag/tags-2026-10-16';
    pack.target = '_blank';
    pack.rel = 'noopener noreferrer';
    pack.textContent = 'Download the Danbooru tag pack';
    const source = document.createElement('p');
    source.className = 'ca-dialog-hint ca-tag-source';
    source.textContent = `Current source: ${(autocomplete.settings.tagSource || autocomplete.settings.customWordsUrl || 'None').replace(/^file:/, '')}`;
    tags.append(count, source, hint, pack);
    const url = addInput(tags, 'customWordsUrl', 'Tag list URL', 'url');
    const load = createButton('Load URL');
    const file = document.createElement('input');
    file.type = 'file';
    file.accept = '.csv,.txt,text/csv,text/plain';
    tags.append(load, createField('Tag list file', file, `${form.id}-file`));
    const advanced = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = 'Triggers, matching and insertion';
    advanced.append(summary);
    form.append(advanced);
    const matching = group('Triggers and matching', advanced);
    addInput(matching, 'embeddingTrigger', 'Embedding trigger');
    addInput(matching, 'loraTrigger', 'LoRA trigger');
    addInput(matching, 'quickTrigger', 'Quick embedding trigger');
    addInput(matching, 'minChars', 'Minimum characters', 'number', { min: 1, max: 10, step: 1, required: true });
    addInput(matching, 'maxSuggestions', 'Maximum suggestions', 'number', { min: 1, max: 100, step: 1, required: true });
    addSwitch(matching, 'sortByDirectory', 'Group by directory');
    const insertion = group('Insertion', advanced);
    for (const [key, label] of [['autoInsertComma', 'Auto-insert comma'], ['replaceUnderscores', 'Replace underscores with spaces'], ['insertOnTab', 'Insert on Tab'], ['insertOnEnter', 'Insert on Enter']]) addSwitch(insertion, key, label);
    const status = document.createElement('p');
    status.role = 'status';
    status.className = 'ca-tag-status';
    status.textContent = autocomplete.customWordsError || '';
    tags.append(status);
    dialog.body.append(form);
    const cancel = createButton('Cancel');
    const save = createButton('Save Settings', 'ca-primary');
    save.type = 'submit';
    save.setAttribute('form', form.id);
    dialog.actions.append(cancel, save);
    let pending, busy = false;
    const prepare = async callback => {
        busy = true;
        load.disabled = file.disabled = save.disabled = true;
        status.dataset.error = 'false';
        status.textContent = 'Loading tags…';
        try {
            const result = await callback();
            if (dialog.scope.signal.aborted) return;
            pending = result;
            status.textContent = `${pending.tags.length.toLocaleString()} tags ready. Save Settings to apply.`;
        } catch (error) {
            if (dialog.scope.signal.aborted) return;
            status.dataset.error = 'true';
            status.textContent = `Could not load tags: ${error.message}`;
        } finally {
            busy = false;
            load.disabled = file.disabled = save.disabled = false;
        }
    };
    dialog.scope.listen(load, 'click', () => {
        if (!url.value.trim() || !url.reportValidity()) {
            status.dataset.error = 'true';
            status.textContent = 'Enter a valid tag-list URL.';
            return;
        }
        prepare(() => autocomplete.fetchTagList(url.value.trim(), dialog.scope.signal));
    });
    dialog.scope.listen(file, 'change', () => {
        const selected = file.files[0];
        if (!selected) return;
        prepare(async () => {
            if (selected.size > MAX_TAG_BYTES) throw new Error('Tag file too large. Maximum size is 32 MB.');
            const text = await selected.text();
            const tags = await parseTagFile(text, dialog.scope.signal);
            return { text, tags, source: `file:${selected.name}` };
        });
        file.value = '';
    });
    dialog.scope.listen(cancel, 'click', () => dialog.close('cancel'));
    dialog.scope.listen(form, 'submit', async event => {
        event.preventDefault();
        if (busy) return;
        const next = {};
        for (const [key, input] of fields) next[key] = input.type === 'checkbox' ? input.checked : input.type === 'number' ? Number(input.value) : input.value.trim();
        next.embeddingTrigger ||= 'embedding:';
        next.loraTrigger ||= '<lora:';
        next.tagSource = pending?.source || (next.customWordsUrl !== autocomplete.settings.customWordsUrl ? next.customWordsUrl : autocomplete.settings.tagSource);
        save.disabled = true;
        try {
            await autocomplete.saveTagSettings(next, pending);
            dialog.close('save');
        } catch (error) {
            status.dataset.error = 'true';
            status.textContent = error.message;
            save.disabled = false;
        }
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
