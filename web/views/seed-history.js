import { createButton } from '../ui/core.js';

let nextHistoryId = 0;

export function createSeedHistoryView(scope, actions) {
    const element = document.createElement('div');
    element.className = 'ca-tools ca-seed-history';
    const header = document.createElement('header');
    header.className = 'ca-seed-header';
    const title = document.createElement('h3');
    title.textContent = 'Seed History';
    const brand = document.createElement('span');
    brand.textContent = 'ComfyAssets';
    header.append(title, brand);
    const toolbar = document.createElement('div');
    toolbar.className = 'ca-seed-actions';
    const generate = createButton('Generate', 'ca-primary');
    const clear = createButton('Clear', 'ca-danger');
    const disclosure = createButton('Hide history', 'ca-seed-disclosure');
    disclosure.setAttribute('aria-expanded', 'true');
    toolbar.append(generate, clear);
    const list = document.createElement('ol');
    list.className = 'ca-seed-list';
    list.id = `ca-seed-list-${++nextHistoryId}`;
    list.setAttribute('role', 'list');
    list.setAttribute('aria-label', 'Recent seeds');
    disclosure.setAttribute('aria-controls', list.id);
    const empty = document.createElement('p');
    empty.className = 'ca-seed-empty';
    empty.textContent = 'No seeds tracked';
    const status = document.createElement('div');
    status.className = 'ca-seed-status';
    status.setAttribute('role', 'status');
    element.append(header, toolbar, disclosure, list, empty, status);
    scope.listen(generate, 'click', actions.generate);
    scope.listen(clear, 'click', actions.clear);
    scope.listen(disclosure, 'click', () => actions.expand(list.hidden));
    scope.listen(list, 'click', event => {
        const button = event.target.closest('button[data-seed-index]');
        if (button) actions.select(Number(button.dataset.seedIndex));
    });
    return {
        element, list, disclosure, status,
        expand(expanded) {
            list.hidden = !expanded;
            disclosure.textContent = expanded ? 'Hide history' : 'Show history';
            disclosure.setAttribute('aria-expanded', String(expanded));
            empty.hidden = !expanded || list.childElementCount > 0;
        },
        render(history, selectedSeed, formatTime) {
            const focused = list.contains(document.activeElement) ? document.activeElement.dataset.seed : null;
            list.replaceChildren(...history.map((item, index) => {
                const row = document.createElement('li');
                const button = createButton('', 'ca-seed-entry');
                button.dataset.seedIndex = index;
                button.dataset.seed = item.seed;
                button.setAttribute('aria-label', `Use seed ${item.seed}`);
                button.setAttribute('aria-pressed', String(item.seed === selectedSeed));
                const seed = document.createElement('span');
                seed.className = 'ca-seed-value';
                seed.textContent = item.seed;
                const time = document.createElement('span');
                time.className = 'ca-seed-time';
                time.textContent = formatTime(item.timestamp);
                button.append(seed, time);
                row.append(button);
                return row;
            }));
            empty.hidden = list.hidden || history.length > 0;
            if (focused !== null) list.querySelector(`button[data-seed="${focused}"]`)?.focus();
        },
    };
}
