import { app } from '../../scripts/app.js';
import { createButton, createScope, mountTheme } from './ui/core.js';
import { clampIndex, summary } from './ui/h3-reference-prompter.js';

const NODE_CLASS = 'KikoH3ReferencePrompter';
const NODE_WIDTH = 460;
const FALLBACK_PANEL_HEIGHT = 120;
const FIT_RETRY_FRAMES = 60;
const FIT_SLACK = 1;
const EMPTY_TEXT = 'Run the workflow to see the written prompt.';
const COPIED_TEXT = 'Copied';
const COPY_FAILED_TEXT = 'Copy failed; select the text and copy it by hand';

function part(tag, className, text = '') {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = text;
    return element;
}

function createPanel() {
    const element = part('div', 'ca-tools ca-h3-prompter');
    const empty = part('p', 'ca-h3-empty', EMPTY_TEXT);
    const bar = part('div', 'ca-h3-bar');
    const count = part('span', 'ca-h3-summary');
    const nav = part('div', 'ca-h3-nav');
    const previous = createButton('‹', 'ca-icon-button');
    previous.setAttribute('aria-label', 'Previous prompt');
    const position = part('span', 'ca-h3-position');
    const next = createButton('›', 'ca-icon-button');
    next.setAttribute('aria-label', 'Next prompt');
    nav.append(previous, position, next);
    const copy = createButton('Copy', 'ca-h3-copy');
    copy.setAttribute('aria-label', 'Copy prompt');
    bar.append(count, nav, copy);
    const text = part('div', 'ca-h3-text');
    text.tabIndex = 0;
    const status = part('p', 'ca-h3-status');
    status.setAttribute('role', 'status');
    const notes = part('details', 'ca-h3-notes');
    const notesTitle = part('summary', '', 'Picture notes');
    const notesText = part('div', 'ca-h3-notes-text');
    notes.append(notesTitle, notesText);
    element.append(empty, bar, text, status, notes);
    return { element, empty, bar, count, nav, previous, position, next, copy, text, status, notes, notesText };
}

function mountPanel(node) {
    const scope = createScope();
    const view = createPanel();
    const state = { prompts: [], notes: [], index: 0 };
    let panelHeight = FALLBACK_PANEL_HEIGHT;
    let fitRetryPending = false;

    // Natural height: padding plus the visible children and the gaps between them.
    // Returns 0 while the element is detached or not laid out.
    function measurePanel() {
        const element = view.element;
        if (!element.isConnected || element.offsetParent === null) return 0;
        const style = getComputedStyle(element);
        const visible = Array.from(element.children).filter(child => getComputedStyle(child).display !== 'none');
        if (!visible.length || visible.every(child => child.offsetHeight === 0)) return 0;
        const gap = parseFloat(style.rowGap) || 0;
        const padding = (parseFloat(style.paddingTop) || 0) + (parseFloat(style.paddingBottom) || 0);
        return Math.ceil(padding + visible.reduce((sum, child) => sum + child.offsetHeight, 0) + gap * (visible.length - 1)) + FIT_SLACK;
    }

    function fitNodeHeight(attempt = 0) {
        if (scope.signal.aborted) return;
        const measured = measurePanel();
        if (!measured) {
            if (attempt < FIT_RETRY_FRAMES && !fitRetryPending && typeof requestAnimationFrame === 'function') {
                fitRetryPending = true;
                requestAnimationFrame(() => {
                    fitRetryPending = false;
                    fitNodeHeight(attempt + 1);
                });
            }
            return;
        }
        panelHeight = measured;
        const target = node.computeSize?.()?.[1];
        if (!Number.isFinite(target) || Math.abs(target - node.size[1]) < 1) return;
        node.setSize([node.size[0], target]);
        node.graph?.setDirtyCanvas?.(true, true);
    }

    function render() {
        if (scope.signal.aborted) return;
        const { prompts, notes, index } = state;
        const has = prompts.length > 0;
        view.empty.hidden = has;
        view.bar.hidden = !has;
        view.text.hidden = !has;
        view.status.hidden = !has || !view.status.textContent;
        view.nav.hidden = prompts.length < 2;
        const note = has ? notes[index] ?? '' : '';
        view.notes.hidden = !note;
        view.notesText.textContent = note;
        view.count.textContent = summary(prompts);
        view.text.textContent = has ? prompts[index] : '';
        view.position.textContent = `${index + 1} / ${prompts.length}`;
        view.previous.disabled = index <= 0;
        view.next.disabled = index >= prompts.length - 1;
        fitNodeHeight();
    }

    function setStatus(message) {
        view.status.textContent = message;
        view.status.hidden = !message;
        fitNodeHeight();
    }

    function show(delta) {
        state.index = clampIndex(state.index + delta, state.prompts.length);
        setStatus('');
        render();
    }

    async function copyPrompt() {
        const prompt = state.prompts[state.index];
        if (prompt === undefined) return;
        try {
            await navigator.clipboard.writeText(prompt);
            setStatus(COPIED_TEXT);
        } catch {
            setStatus(COPY_FAILED_TEXT);
        }
    }

    scope.listen(view.previous, 'click', () => show(-1));
    scope.listen(view.next, 'click', () => show(1));
    scope.listen(view.copy, 'click', copyPrompt);
    scope.listen(view.notes, 'toggle', () => fitNodeHeight());

    node.addDOMWidget('h3_prompt_panel', 'div', view.element, {
        serialize: false, hideOnZoom: false, getMinHeight: () => panelHeight, getMaxHeight: () => panelHeight,
    });
    node.setSize([NODE_WIDTH, node.computeSize?.()?.[1] ?? node.size[1]]);
    if (typeof ResizeObserver === 'function') {
        let refitScheduled = false;
        const observer = new ResizeObserver(() => {
            if (scope.signal.aborted || refitScheduled) return;
            refitScheduled = true;
            requestAnimationFrame(() => {
                refitScheduled = false;
                if (scope.signal.aborted) return;
                const measured = measurePanel();
                if (measured && measured !== panelHeight) fitNodeHeight();
            });
        });
        for (const child of view.element.children) observer.observe(child);
        scope.cleanup(() => observer.disconnect());
    }
    mountTheme(view.element, app.ui.settings, scope);
    scope.cleanup(() => view.element.remove());

    const onExecuted = node.onExecuted;
    node.onExecuted = function (message) {
        const result = onExecuted?.apply(this, arguments);
        const prompts = Array.isArray(message?.h3_prompts) ? message.h3_prompts.map(String) : [];
        state.prompts = prompts;
        state.notes = Array.isArray(message?.h3_notes) ? message.h3_notes.map(String) : [];
        state.index = clampIndex(state.index, prompts.length);
        view.status.textContent = '';
        render();
        return result;
    };

    const onRemoved = node.onRemoved;
    node.onRemoved = function () {
        scope.dispose();
        return onRemoved?.apply(this, arguments);
    };

    render();
}

app.registerExtension({
    name: 'kikotools.h3ReferencePrompter',
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_CLASS) return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            mountPanel(this);
            return result;
        };
    },
});
