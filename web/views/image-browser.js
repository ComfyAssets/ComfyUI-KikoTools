import { createButton, createField, createSelect, createSegments, createSwitch, mountTheme } from '../ui/core.js';

export function createImageBrowser(id, settings, scope) {
    const element = document.createElement('div');
    element.className = 'ca-tools ca-image-browser';
    element.innerHTML = `<div class="kiko-container-wrapper">
        <div class="ca-browser-header"><strong>Local Image Loader</strong><span>ComfyAssets</span></div>
        <div class="kiko-controls kiko-path-controls"></div>
        <div class="ca-directory"><label class="ca-field-label" for="${id}-path">Directory</label><div class="kiko-controls ca-path-row"><div class="kiko-path-input-wrapper"><input id="${id}-path" class="kiko-path-input" type="text" spellcheck="false" placeholder="Enter a directory…"><div class="kiko-autocomplete-dropdown"></div></div></div></div>
        <div class="kiko-controls ca-options"><div class="ca-sort"></div></div>
        <div class="ca-gallery-tools"></div>
        <div class="kiko-status-message" role="status">Loading…</div>
        <div class="kiko-cardholder" data-view="grid"></div>
        <div class="ca-browser-footer"><span data-file-count></span><div class="kiko-pagination"></div></div>
        <div class="ca-selection"><span class="ca-field-label">Selected media</span><strong data-selection>No media selected</strong></div>
    </div>`;
    const saved = createSelect([['', '— Saved paths —']], 'kiko-path-presets');
    saved.setAttribute('aria-label', 'Saved paths');
    const remove = createButton('×', 'kiko-delete-path ca-danger');
    remove.setAttribute('aria-label', 'Remove saved path');
    element.querySelector('.kiko-path-controls').append(saved, createButton('☆ Save path', 'kiko-save-path'), remove);
    const up = createButton('↑', 'kiko-up-folder ca-icon-button');
    up.setAttribute('aria-label', 'Parent folder');
    const pathRow = element.querySelector('.ca-path-row');
    pathRow.prepend(up);
    pathRow.append(createButton('Browse', 'kiko-browse ca-primary'));
    element.querySelector('.ca-options').prepend(createSwitch('Hide dot folders', 'kiko-hide-dot-folders', `${id}-hidden`));
    const refresh = createButton('↻', 'kiko-refresh ca-icon-button');
    refresh.setAttribute('aria-label', 'Refresh folder');
    element.querySelector('.ca-sort').append(
        createField('Sort', createSelect([['name', 'Name'], ['date', 'Date'], ['size', 'Size']], 'kiko-sort-by'), `${id}-sort`),
        createField('Order', createSelect([['asc', '↑ Ascending'], ['desc', '↓ Descending']], 'kiko-sort-order'), `${id}-order`), refresh,
    );
    const filter = document.createElement('input');
    filter.type = 'search';
    filter.placeholder = 'Filter this page…';
    filter.className = 'ca-file-filter';
    filter.setAttribute('aria-label', 'Filter this page');
    element.querySelector('.ca-gallery-tools').append(filter, createSegments('Gallery layout', [['grid', 'Grid'], ['list', 'List']], `${id}-view`, scope, value => { element.querySelector('.kiko-cardholder').dataset.view = value; }));
    mountTheme(element, settings, scope);
    return element;
}
