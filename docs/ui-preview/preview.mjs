const root = document.documentElement;
const loader = document.querySelector('[data-loader]');
const gallery = document.querySelector('[data-gallery]');
const status = document.querySelector('[data-status]');
const selection = document.querySelector('[data-selection]');
const clear = document.querySelector('[data-clear]');
const error = document.querySelector('.ca-error');
const filter = document.querySelector('#filter');
const path = document.querySelector('#directory');
const sort = document.querySelector('#sort');
let selected = '';
let descending = false;
const files = [
    { name: 'alpine-lake.png', scene: 'lake', size: '1536 × 1024', order: 3 },
    { name: 'desert-dunes.png', scene: 'dune', size: '1536 × 1024', order: 6 },
    { name: 'forest-study.png', scene: 'forest', size: '1024 × 1536', order: 4 },
    { name: 'coastal-light.png', scene: 'coast', size: '1536 × 1024', order: 1 },
    { name: 'studio-shapes.png', scene: 'studio', size: '1024 × 1024', order: 2 },
    { name: 'night-ridge.png', scene: 'night', size: '1536 × 1024', order: 5 },
];

function renderFiles() {
    const visible = files.filter(file => file.name.includes(filter.value.toLowerCase()));
    visible.sort((a, b) => {
        const order = sort.value === 'name' ? a.name.localeCompare(b.name)
            : sort.value === 'size' ? a.size.localeCompare(b.size) : a.order - b.order;
        return descending ? -order : order;
    });
    gallery.replaceChildren(...visible.map(file => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'ca-file';
        button.setAttribute('aria-label', `Select ${file.name}`);
        button.setAttribute('aria-pressed', String(file.name === selected));
        const scene = document.createElement('span');
        scene.className = `ca-scene ca-scene-${file.scene}`;
        scene.setAttribute('aria-hidden', 'true');
        const check = document.createElement('span');
        check.className = 'ca-file-check';
        check.textContent = '✓';
        check.setAttribute('aria-hidden', 'true');
        const name = document.createElement('span');
        name.className = 'ca-file-name';
        name.textContent = file.name;
        const meta = document.createElement('span');
        meta.className = 'ca-file-meta';
        meta.textContent = `${file.size} · PNG`;
        button.append(scene, check, name, meta);
        button.addEventListener('click', () => {
            selected = file.name;
            selection.textContent = file.name;
            clear.disabled = false;
            for (const item of gallery.children) item.setAttribute('aria-pressed', String(item === button));
            status.textContent = `Selected ${file.name} · demo selection`;
        });
        return button;
    }));
    document.querySelector('[data-empty]').hidden = visible.length > 0;
    document.querySelector('[data-count]').textContent = `${visible.length} sample files`;
}

document.querySelectorAll('[name="theme"]').forEach(input => {
    input.addEventListener('change', () => { root.dataset.theme = input.value; });
});
document.querySelector('#node-width').addEventListener('input', event => {
    loader.style.setProperty('--ca-preview-width', `${event.target.value}px`);
    document.querySelector('[data-width]').value = `${event.target.value} px`;
});
document.querySelectorAll('[name="view"]').forEach(input => {
    input.addEventListener('change', () => { gallery.dataset.view = input.value; });
});
document.querySelector('#thumbnail-size').addEventListener('input', event => {
    gallery.style.setProperty('--ca-thumbnail-size', `${event.target.value}px`);
    document.querySelector('[data-thumbnail-size]').value = `${event.target.value} px`;
});
filter.addEventListener('input', renderFiles);
sort.addEventListener('change', renderFiles);
document.querySelector('[data-sort-order]').addEventListener('click', event => {
    descending = !descending;
    event.currentTarget.setAttribute('aria-pressed', String(descending));
    event.currentTarget.setAttribute('aria-label', descending ? 'Sort ascending' : 'Sort descending');
    event.currentTarget.textContent = descending ? '↓' : '↑';
    renderFiles();
});
document.querySelector('#hide-dot').addEventListener('change', event => {
    status.textContent = event.target.checked ? 'Dot folders hidden · sample content unchanged' : 'Dot folders visible · no hidden folders in this sample';
});
function browse() {
    error.hidden = true;
    status.textContent = `Previewing ${path.value || '/input'} · sample content only`;
    renderFiles();
}
document.querySelector('.ca-path-form').addEventListener('submit', event => { event.preventDefault(); browse(); });
document.querySelector('[data-refresh]').addEventListener('click', browse);
document.querySelector('[data-retry]').addEventListener('click', browse);
document.querySelector('#saved-paths').addEventListener('change', event => { path.value = event.target.value; browse(); });
document.querySelector('[data-save-path]').addEventListener('click', () => {
    if (!path.value.trim()) { status.textContent = 'Enter a directory before saving a sample path'; return; }
    const presets = document.querySelector('#saved-paths');
    if (![...presets.options].some(option => option.value === path.value)) presets.add(new Option(path.value, path.value));
    presets.value = path.value;
    status.textContent = 'Path saved for this preview session';
});
document.querySelector('[data-parent]').addEventListener('click', () => {
    path.value = path.value.replace(/\/+$/, '').split('/').slice(0, -1).join('/') || '/';
    browse();
});
clear.addEventListener('click', () => {
    selected = '';
    selection.textContent = 'No image selected';
    clear.disabled = true;
    renderFiles();
    status.textContent = 'Selection cleared';
});
document.querySelector('[data-error-example]').addEventListener('click', () => {
    error.hidden = false;
    status.textContent = 'Error example shown · use Retry to return';
});
document.querySelector('[data-primary-example]').addEventListener('click', () => {
    status.textContent = 'Primary action example · blue is shared across both tools';
});
let nextRow = 1;
const rows = document.querySelector('[data-prompt-rows]');
const reset = document.querySelector('[data-reset-rows]');
function addRow() {
    const id = nextRow++;
    const row = document.createElement('div');
    row.className = 'ca-prompt-row';
    row.innerHTML = `<div class="ca-row"><label class="ca-switch" for="prompt-enabled-${id}"><input id="prompt-enabled-${id}" type="checkbox" role="switch" checked>Row ${id}</label><button type="button" class="ca-icon-button" aria-label="Remove row ${id}">×</button></div><label for="prompt-${id}" class="ca-visually-hidden">Prompt row ${id}</label><textarea id="prompt-${id}" placeholder="Write a prompt…"></textarea>`;
    row.querySelector('button').addEventListener('click', () => {
        row.remove();
        reset.disabled = rows.children.length === 1 && rows.firstChild.querySelector('textarea').value === '';
        document.querySelector('[data-add-row]').focus();
    });
    row.querySelector('textarea').addEventListener('input', () => { reset.disabled = false; });
    row.querySelector('input').addEventListener('change', event => { row.querySelector('textarea').disabled = !event.target.checked; reset.disabled = false; });
    rows.append(row);
}
document.querySelector('[data-add-row]').addEventListener('click', () => { addRow(); reset.disabled = false; rows.lastChild.querySelector('textarea').focus(); });
reset.addEventListener('click', () => { rows.replaceChildren(); nextRow = 1; addRow(); reset.disabled = true; document.querySelector('[data-add-row]').focus(); });
addRow();
renderFiles();
