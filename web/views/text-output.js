import { createButton, createScope, mountTheme } from '../ui/core.js';

let nextOutput = 0;

export function outputSections(kind, text) {
    if (kind === 'text') {
        const positive = text.match(/Positive prompt:\s*([\s\S]*?)(?=Negative prompt:|$)/i);
        const negative = text.match(/Negative prompt:\s*([\s\S]*?)(?=\*\*|$)/i);
        if (positive && negative) {
            let positiveText = positive[1].trim();
            const marker = positiveText.indexOf('**');
            if (marker > 0) positiveText = positiveText.slice(0, marker).trim();
            return [
                { label: 'Positive prompt', copy: 'Copy positive', text: positiveText },
                { label: 'Negative prompt', copy: 'Copy negative', text: negative[1].trim() },
            ];
        }
    }
    return [{ label: kind === 'text' ? 'Text output' : 'Value output', copy: kind === 'text' ? 'Copy text' : 'Copy value', text }];
}

export function createTextOutputView(scope, kind, settings) {
    const element = document.createElement('div');
    element.className = 'ca-tools ca-text-output';
    element.dataset.outputKind = kind;
    const header = document.createElement('header');
    const title = document.createElement('h2');
    title.textContent = kind === 'text' ? 'Display Text' : 'Display Any';
    const brand = document.createElement('span');
    brand.textContent = 'ComfyAssets';
    header.append(title, brand);
    const content = document.createElement('div');
    content.className = 'ca-output-content';
    const status = document.createElement('p');
    status.role = 'status';
    element.append(header, content, status);
    mountTheme(element, settings, scope);
    let renderScope;
    scope.cleanup(() => {
        renderScope?.dispose();
        element.remove();
    });
    return {
        element,
        update(text) {
            renderScope?.dispose();
            const current = createScope();
            renderScope = current;
            content.replaceChildren();
            status.textContent = '';
            delete status.dataset.error;
            const clearStatus = current.debounce(() => { status.textContent = ''; }, 1500);
            for (const section of outputSections(kind, text)) {
                const row = document.createElement('div');
                row.className = 'ca-output-section';
                const toolbar = document.createElement('div');
                toolbar.className = 'ca-output-toolbar';
                const input = document.createElement('textarea');
                input.id = `ca-output-${++nextOutput}`;
                input.readOnly = true;
                input.spellcheck = false;
                input.value = section.text;
                const label = document.createElement('label');
                label.htmlFor = input.id;
                label.textContent = section.label;
                const copy = createButton(section.copy, 'ca-primary');
                toolbar.append(label, copy);
                row.append(toolbar, input);
                content.append(row);
                current.listen(copy, 'click', async () => {
                    try {
                        await navigator.clipboard.writeText(section.text);
                        if (current.signal.aborted) return;
                        delete status.dataset.error;
                        status.textContent = 'Copied.';
                        clearStatus();
                    } catch {
                        if (current.signal.aborted) return;
                        status.dataset.error = 'true';
                        status.textContent = 'Could not copy. Select the text and copy it manually.';
                    }
                });
            }
        },
    };
}
