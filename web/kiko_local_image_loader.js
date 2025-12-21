import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

// Setup global lightbox for image preview
function setupGlobalLightbox() {
    if (document.getElementById('kiko-image-lightbox')) return;

    const lightboxId = 'kiko-image-lightbox';
    const lightboxHTML = `
        <div id="${lightboxId}" class="lightbox-overlay">
            <button class="lightbox-close">&times;</button>
            <button class="lightbox-prev">&lt;</button>
            <button class="lightbox-next">&gt;</button>
            <div class="lightbox-content">
                <img src="" alt="Preview" style="display: none;">
                <video src="" controls autoplay style="display: none;"></video>
                <audio src="" controls autoplay style="display: none;"></audio>
            </div>
            <div class="lightbox-dimensions"></div>
        </div>
    `;

    const lightboxCSS = `
        #${lightboxId} {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.85);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            box-sizing: border-box;
            -webkit-user-select: none;
            user-select: none;
        }
        #${lightboxId} .lightbox-content {
            position: relative;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }
        #${lightboxId} img, #${lightboxId} video {
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
            transition: transform 0.1s ease-out;
            transform: scale(1) translate(0, 0);
        }
        #${lightboxId} audio {
            width: 80%;
            max-width: 600px;
        }
        #${lightboxId} img {
            cursor: grab;
        }
        #${lightboxId} img.panning {
            cursor: grabbing;
        }
        #${lightboxId} .lightbox-close {
            position: absolute;
            top: 15px;
            right: 20px;
            width: 35px;
            height: 35px;
            background-color: rgba(0,0,0,0.5);
            color: #fff;
            border-radius: 50%;
            border: 2px solid #fff;
            font-size: 24px;
            line-height: 30px;
            text-align: center;
            cursor: pointer;
            z-index: 10002;
        }
        #${lightboxId} .lightbox-prev, #${lightboxId} .lightbox-next {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 45px;
            height: 60px;
            background-color: rgba(0,0,0,0.4);
            color: #fff;
            border: none;
            font-size: 30px;
            cursor: pointer;
            z-index: 10001;
            transition: background-color 0.2s;
        }
        #${lightboxId} .lightbox-prev:hover, #${lightboxId} .lightbox-next:hover {
            background-color: rgba(0,0,0,0.7);
        }
        #${lightboxId} .lightbox-prev {
            left: 15px;
        }
        #${lightboxId} .lightbox-next {
            right: 15px;
        }
        #${lightboxId} [disabled] {
            display: none;
        }
        #${lightboxId} .lightbox-dimensions {
            position: absolute;
            bottom: 0px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.7);
            color: #fff;
            padding: 2px 4px;
            border-radius: 5px;
            font-size: 14px;
            z-index: 10001;
        }
    `;

    document.body.insertAdjacentHTML('beforeend', lightboxHTML);
    const styleEl = document.createElement('style');
    styleEl.textContent = lightboxCSS;
    document.head.appendChild(styleEl);
}

setupGlobalLightbox();

app.registerExtension({
    name: "KikoTools.LocalImageLoader",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "KikoLocalImageLoader") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated?.apply(this, arguments);

                const galleryContainer = document.createElement("div");
                const uniqueId = `kiko-gallery-${Math.random().toString(36).substring(2, 9)}`;
                galleryContainer.id = uniqueId;

                const folderSVG = `<svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><path d="M928 320H488L416 232c-15.1-18.9-38.3-29.9-63.1-29.9H128c-35.3 0-64 28.7-64 64v512c0 35.3 28.7 64 64 64h800c35.3 0 64-28.7 64-64V384c0-35.3-28.7-64-64-64z" fill="#F4D03F"></path></svg>`;
                const videoSVG = `<svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><path d="M895.9 203.4H128.1c-35.3 0-64 28.7-64 64v489.2c0 35.3 28.7 64 64 64h767.8c35.3 0 64-28.7 64-64V267.4c0-35.3-28.7-64-64-64zM384 691.2V332.8L668.1 512 384 691.2z" fill="#AED6F1"></path></svg>`;
                const audioSVG = `<svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><path d="M768 256H256c-35.3 0-64 28.7-64 64v384c0 35.3 28.7 64 64 64h512c35.3 0 64-28.7 64-64V320c0-35.3-28.7-64-64-64zM512 665.6c-84.8 0-153.6-68.8-153.6-153.6S427.2 358.4 512 358.4s153.6 68.8 153.6 153.6-68.8 153.6-153.6 153.6z" fill="#A9DFBF"></path><path d="M512 409.6c-56.5 0-102.4 45.9-102.4 102.4s45.9 102.4 102.4 102.4 102.4-45.9 102.4-102.4-45.9-102.4-102.4-102.4z" fill="#A9DFBF"></path></svg>`;

                galleryContainer.innerHTML = `
                    <style>
                        #${uniqueId} {
                            width: 100%;
                            height: 100%;
                            overflow: hidden;
                            box-sizing: border-box;
                        }
                        #${uniqueId} .kiko-container-wrapper {
                            width: 100%;
                            height: 100%;
                            font-family: sans-serif;
                            color: #ccc;
                            box-sizing: border-box;
                            display: flex;
                            flex-direction: column;
                            padding: 5px;
                            overflow: hidden;
                        }
                        #${uniqueId} .kiko-controls {
                            display: flex;
                            flex-wrap: wrap;
                            gap: 5px;
                            margin-bottom: 5px;
                            align-items: center;
                            flex-shrink: 0;
                        }
                        #${uniqueId} .kiko-controls label {
                            margin-left: 0px;
                            font-size: 11px;
                            white-space: nowrap;
                        }
                        #${uniqueId} .kiko-controls input,
                        #${uniqueId} .kiko-controls select,
                        #${uniqueId} .kiko-controls button {
                            background-color: #333;
                            color: #ccc;
                            border: 1px solid #555;
                            border-radius: 4px;
                            padding: 2px 4px;
                            font-size: 11px;
                        }
                        #${uniqueId} .kiko-controls input[type=text] {
                            flex-grow: 1;
                            min-width: 100px;
                        }
                        #${uniqueId} .kiko-path-controls {
                            flex-grow: 1;
                            display: flex;
                            gap: 3px;
                        }
                        #${uniqueId} .kiko-path-presets {
                            flex-grow: 1;
                        }
                        #${uniqueId} .kiko-controls button {
                            cursor: pointer;
                        }
                        #${uniqueId} .kiko-controls button:hover {
                            background-color: #444;
                        }
                        #${uniqueId} .kiko-controls button:disabled {
                            background-color: #222;
                            cursor: not-allowed;
                        }
                        #${uniqueId} .kiko-cardholder {
                            position: relative;
                            overflow-y: auto;
                            overflow-x: hidden;
                            background: #222;
                            padding: 3px;
                            border-radius: 5px;
                            flex-grow: 1;
                            flex-shrink: 1;
                            min-height: 200px;
                            width: 100%;
                            transition: opacity 0.2s ease-in-out;
                        }
                        #${uniqueId} .kiko-gallery-card {
                            position: absolute;
                            border: 3px solid transparent;
                            border-radius: 8px;
                            box-sizing: border-box;
                            transition: all 0.3s ease;
                            cursor: pointer;
                            display: flex;
                            flex-direction: column;
                            background-color: #2a2a2a;
                        }
                        #${uniqueId} .kiko-gallery-card.kiko-selected {
                            border-color: #00FFC9;
                        }
                        #${uniqueId} .kiko-card-media-wrapper {
                            flex-grow: 1;
                            position: relative;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            min-height: 100px;
                        }
                        #${uniqueId} .kiko-gallery-card img,
                        #${uniqueId} .kiko-gallery-card video {
                            width: 100%;
                            height: auto;
                            border-top-left-radius: 5px;
                            border-top-right-radius: 5px;
                            display: block;
                        }
                        #${uniqueId} .kiko-folder-card,
                        #${uniqueId} .kiko-audio-card {
                            background-color: transparent;
                            flex-grow: 1;
                            padding: 10px;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                            text-align: center;
                        }
                        #${uniqueId} .kiko-folder-card:hover,
                        #${uniqueId} .kiko-audio-card:hover {
                            background-color: #444;
                        }
                        #${uniqueId} .kiko-parent-folder-card {
                            background-color: transparent;
                        }
                        #${uniqueId} .kiko-parent-folder-card:hover {
                            background-color: #555;
                        }
                        #${uniqueId} .kiko-folder-icon,
                        #${uniqueId} .kiko-audio-icon {
                            width: 60%;
                            height: 60%;
                            margin-bottom: 8px;
                        }
                        #${uniqueId} .kiko-folder-name,
                        #${uniqueId} .kiko-audio-name {
                            font-size: 12px;
                            word-break: break-all;
                            user-select: none;
                        }
                        #${uniqueId} .kiko-video-card-overlay {
                            position: absolute;
                            top: 5px;
                            left: 5px;
                            width: 24px;
                            height: 24px;
                            opacity: 0.8;
                            pointer-events: none;
                        }
                        #${uniqueId} .kiko-card-info-panel {
                            flex-shrink: 0;
                            background-color: #353535;
                            padding: 4px;
                            border-bottom-left-radius: 5px;
                            border-bottom-right-radius: 5px;
                            min-height: 24px;
                            font-size: 10px;
                            text-align: center;
                            color: #aaa;
                        }
                        #${uniqueId} .kiko-pagination {
                            display: flex;
                            justify-content: center;
                            gap: 3px;
                            margin-top: 3px;
                            flex-shrink: 0;
                            padding-bottom: 2px;
                        }
                        #${uniqueId} .kiko-status-message {
                            position: absolute;
                            top: 50%;
                            left: 50%;
                            transform: translate(-50%, -50%);
                            background-color: rgba(0, 0, 0, 0.8);
                            color: white;
                            padding: 10px;
                            border-radius: 5px;
                            display: none;
                            z-index: 1000;
                        }
                        #${uniqueId} .kiko-path-input-wrapper {
                            position: relative;
                            flex-grow: 1;
                            min-width: 100px;
                        }
                        #${uniqueId} .kiko-path-input-wrapper input {
                            width: 100%;
                            box-sizing: border-box;
                        }
                        #${uniqueId} .kiko-autocomplete-dropdown {
                            position: absolute;
                            top: 100%;
                            left: 0;
                            right: 0;
                            max-height: 250px;
                            overflow-y: auto;
                            background-color: #2a2a2a;
                            border: 1px solid #555;
                            border-top: none;
                            border-radius: 0 0 4px 4px;
                            z-index: 2000;
                            display: none;
                        }
                        #${uniqueId} .kiko-autocomplete-dropdown.visible {
                            display: block;
                        }
                        #${uniqueId} .kiko-autocomplete-item {
                            padding: 6px 8px;
                            cursor: pointer;
                            display: flex;
                            align-items: center;
                            gap: 8px;
                            font-size: 12px;
                            border-bottom: 1px solid #333;
                        }
                        #${uniqueId} .kiko-autocomplete-item:last-child {
                            border-bottom: none;
                        }
                        #${uniqueId} .kiko-autocomplete-item:hover,
                        #${uniqueId} .kiko-autocomplete-item.selected {
                            background-color: #3a3a3a;
                        }
                        #${uniqueId} .kiko-autocomplete-item .folder-icon {
                            width: 16px;
                            height: 16px;
                            flex-shrink: 0;
                        }
                        #${uniqueId} .kiko-autocomplete-item .path-text {
                            overflow: hidden;
                            text-overflow: ellipsis;
                            white-space: nowrap;
                        }
                        #${uniqueId} .kiko-autocomplete-item .folder-name {
                            color: #fff;
                        }
                        #${uniqueId} .kiko-autocomplete-item .parent-path {
                            color: #888;
                            font-size: 10px;
                        }
                    </style>

                    <div class="kiko-container-wrapper">
                        <!-- Path controls -->
                        <div class="kiko-controls">
                            <div class="kiko-path-controls">
                                <select class="kiko-path-presets" title="Saved paths">
                                    <option value="">-- Saved Paths --</option>
                                </select>
                                <button class="kiko-save-path" title="Save current path to favorites">💾</button>
                                <button class="kiko-delete-path" title="Remove selected path from favorites">✕</button>
                            </div>
                        </div>

                        <!-- Directory input -->
                        <div class="kiko-controls">
                            <button class="kiko-up-folder" title="Navigate to parent folder">⬆️</button>
                            <div class="kiko-path-input-wrapper">
                                <input type="text" class="kiko-path-input" placeholder="Enter directory path... (type / to browse)" />
                                <div class="kiko-autocomplete-dropdown"></div>
                            </div>
                            <button class="kiko-browse" title="Refresh folder">🔄</button>
                        </div>

                        <!-- View options -->
                        <div class="kiko-controls">
                            <label>
                                <input type="checkbox" class="kiko-hide-dot-folders" checked /> Hide .folders
                            </label>
                            <select class="kiko-sort-by">
                                <option value="name">Name</option>
                                <option value="date">Date</option>
                                <option value="size">Size</option>
                            </select>
                            <select class="kiko-sort-order">
                                <option value="asc">↑</option>
                                <option value="desc">↓</option>
                            </select>
                            <button class="kiko-refresh">🔄</button>
                        </div>

                        <!-- Gallery -->
                        <div class="kiko-cardholder">
                            <div class="kiko-status-message">Loading...</div>
                        </div>

                        <!-- Pagination -->
                        <div class="kiko-pagination"></div>
                    </div>
                `;

                // Add the widget to the node
                this.galleryWidget = this.addDOMWidget("kiko_local_image_gallery", "div", galleryContainer, {
                    serialize: false,
                });

                // Set initial size for the node
                this.size = [800, 600];
                this.setSize(this.size);

                // Initialize gallery functionality
                const node = this;
                const container = galleryContainer.querySelector('.kiko-container-wrapper');
                const pathInput = container.querySelector('.kiko-path-input');
                const pathPresets = container.querySelector('.kiko-path-presets');
                const savePathBtn = container.querySelector('.kiko-save-path');
                const deletePathBtn = container.querySelector('.kiko-delete-path');
                const browseBtn = container.querySelector('.kiko-browse');
                const upFolderBtn = container.querySelector('.kiko-up-folder');
                const hideDotFolders = container.querySelector('.kiko-hide-dot-folders');
                const sortBy = container.querySelector('.kiko-sort-by');
                const sortOrder = container.querySelector('.kiko-sort-order');
                const refreshBtn = container.querySelector('.kiko-refresh');
                const cardHolder = container.querySelector('.kiko-cardholder');
                const pagination = container.querySelector('.kiko-pagination');
                const statusMessage = container.querySelector('.kiko-status-message');
                const autocompleteDropdown = container.querySelector('.kiko-autocomplete-dropdown');

                let currentPage = 1;
                let totalPages = 1;
                let currentDirectory = '';
                let parentDirectory = null;
                let currentItems = [];
                let selectedPaths = {
                    image: null,
                    video: null,
                    audio: null
                };

                // Utility: Debounce function
                const debounce = (func, delay) => {
                    let timeoutId;
                    return (...args) => {
                        clearTimeout(timeoutId);
                        timeoutId = setTimeout(() => func.apply(this, args), delay);
                    };
                };

                // Apply responsive masonry layout
                const applyMasonryLayout = () => {
                    const minCardWidth = 120;
                    const gap = 5;
                    const containerWidth = cardHolder.clientWidth - 10; // Account for padding
                    if (containerWidth <= 0) return;

                    const columnCount = Math.max(1, Math.floor(containerWidth / (minCardWidth + gap)));
                    const totalGapSpace = (columnCount - 1) * gap;
                    const actualCardWidth = Math.floor((containerWidth - totalGapSpace) / columnCount);
                    const columnHeights = new Array(columnCount).fill(0);

                    const cards = cardHolder.querySelectorAll('.kiko-gallery-card');
                    cards.forEach(card => {
                        card.style.width = `${actualCardWidth}px`;
                        const minHeight = Math.min(...columnHeights);
                        const columnIndex = columnHeights.indexOf(minHeight);
                        card.style.left = `${columnIndex * (actualCardWidth + gap)}px`;
                        card.style.top = `${minHeight}px`;
                        columnHeights[columnIndex] += card.offsetHeight + gap;
                    });

                    // Set container height - let scrollbar handle overflow
                    const maxHeight = Math.max(...columnHeights);
                    if (maxHeight > 0) {
                        cardHolder.style.minHeight = `${Math.min(200, maxHeight)}px`;
                    }
                };

                const debouncedLayout = debounce(applyMasonryLayout, 20);

                // Set up ResizeObserver for responsive layout
                new ResizeObserver(debouncedLayout).observe(cardHolder);

                // Autocomplete functionality
                let autocompleteSelectedIndex = -1;
                let autocompleteSuggestions = [];
                const smallFolderSVG = `<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" width="16" height="16"><path d="M928 320H488L416 232c-15.1-18.9-38.3-29.9-63.1-29.9H128c-35.3 0-64 28.7-64 64v512c0 35.3 28.7 64 64 64h800c35.3 0 64-28.7 64-64V384c0-35.3-28.7-64-64-64z" fill="#F4D03F"></path></svg>`;

                async function fetchDirectorySuggestions(path) {
                    try {
                        const response = await api.fetchApi(`/kiko_local_image_loader/list_directories?path=${encodeURIComponent(path)}`);
                        const data = await response.json();
                        return data.directories || [];
                    } catch (error) {
                        console.error('Error fetching directories:', error);
                        return [];
                    }
                }

                function renderAutocompleteSuggestions(suggestions) {
                    autocompleteSuggestions = suggestions;
                    autocompleteSelectedIndex = -1;

                    if (suggestions.length === 0) {
                        autocompleteDropdown.classList.remove('visible');
                        autocompleteDropdown.innerHTML = '';
                        return;
                    }

                    autocompleteDropdown.innerHTML = suggestions.map((path, index) => {
                        const parts = path.split('/').filter(p => p);
                        const folderName = parts.pop() || path;
                        const parentPath = parts.length > 0 ? '/' + parts.join('/') : '';

                        return `
                            <div class="kiko-autocomplete-item" data-index="${index}" data-path="${path}">
                                <div class="folder-icon">${smallFolderSVG}</div>
                                <div class="path-text">
                                    <span class="folder-name">${folderName}</span>
                                    ${parentPath ? `<span class="parent-path"> — ${parentPath}</span>` : ''}
                                </div>
                            </div>
                        `;
                    }).join('');

                    autocompleteDropdown.classList.add('visible');

                    // Add click handlers to items
                    autocompleteDropdown.querySelectorAll('.kiko-autocomplete-item').forEach(item => {
                        item.addEventListener('mousedown', (e) => {
                            e.preventDefault(); // Prevent blur from hiding dropdown before click registers
                            const path = item.dataset.path;
                            selectAutocompleteSuggestion(path);
                        });
                    });
                }

                function hideAutocomplete() {
                    autocompleteDropdown.classList.remove('visible');
                    autocompleteDropdown.innerHTML = '';
                    autocompleteSuggestions = [];
                    autocompleteSelectedIndex = -1;
                }

                function selectAutocompleteSuggestion(path) {
                    pathInput.value = path + '/';
                    hideAutocomplete();
                    // Trigger another fetch to show contents of selected directory
                    debouncedAutocomplete(path + '/');
                }

                function updateAutocompleteSelection() {
                    const items = autocompleteDropdown.querySelectorAll('.kiko-autocomplete-item');
                    items.forEach((item, index) => {
                        if (index === autocompleteSelectedIndex) {
                            item.classList.add('selected');
                            item.scrollIntoView({ block: 'nearest' });
                        } else {
                            item.classList.remove('selected');
                        }
                    });
                }

                const debouncedAutocomplete = debounce(async (value) => {
                    const suggestions = await fetchDirectorySuggestions(value);
                    renderAutocompleteSuggestions(suggestions);
                }, 150);

                // Path input event handlers for autocomplete
                pathInput.addEventListener('input', (e) => {
                    const value = e.target.value;
                    if (value.length > 0) {
                        debouncedAutocomplete(value);
                    } else {
                        hideAutocomplete();
                    }
                });

                pathInput.addEventListener('focus', () => {
                    const value = pathInput.value;
                    if (value.length > 0) {
                        debouncedAutocomplete(value);
                    }
                });

                pathInput.addEventListener('blur', () => {
                    // Delay hiding to allow click events to register
                    setTimeout(hideAutocomplete, 150);
                });

                pathInput.addEventListener('keydown', (e) => {
                    if (!autocompleteDropdown.classList.contains('visible')) {
                        if (e.key === 'Enter') {
                            loadImages(pathInput.value);
                            e.preventDefault();
                        }
                        return;
                    }

                    switch (e.key) {
                        case 'ArrowDown':
                            e.preventDefault();
                            autocompleteSelectedIndex = Math.min(autocompleteSelectedIndex + 1, autocompleteSuggestions.length - 1);
                            updateAutocompleteSelection();
                            break;
                        case 'ArrowUp':
                            e.preventDefault();
                            autocompleteSelectedIndex = Math.max(autocompleteSelectedIndex - 1, -1);
                            updateAutocompleteSelection();
                            break;
                        case 'Enter':
                            e.preventDefault();
                            if (autocompleteSelectedIndex >= 0 && autocompleteSelectedIndex < autocompleteSuggestions.length) {
                                selectAutocompleteSuggestion(autocompleteSuggestions[autocompleteSelectedIndex]);
                            } else {
                                hideAutocomplete();
                                loadImages(pathInput.value);
                            }
                            break;
                        case 'Escape':
                            hideAutocomplete();
                            break;
                        case 'Tab':
                            if (autocompleteSelectedIndex >= 0) {
                                e.preventDefault();
                                selectAutocompleteSuggestion(autocompleteSuggestions[autocompleteSelectedIndex]);
                            } else if (autocompleteSuggestions.length === 1) {
                                e.preventDefault();
                                selectAutocompleteSuggestion(autocompleteSuggestions[0]);
                            }
                            break;
                    }
                });

                // Load saved paths
                async function loadSavedPaths() {
                    try {
                        const response = await api.fetchApi('/kiko_local_image_loader/get_saved_paths');
                        const data = await response.json();

                        pathPresets.innerHTML = '<option value="">-- Saved Paths --</option>';
                        data.saved_paths?.forEach(path => {
                            const option = document.createElement('option');
                            option.value = path;
                            option.textContent = path.split('/').pop() || path;
                            option.title = path;
                            pathPresets.appendChild(option);
                        });
                    } catch (error) {
                        console.error('Error loading saved paths:', error);
                    }
                }

                // Save current path
                savePathBtn.onclick = async () => {
                    if (!currentDirectory) return;

                    try {
                        const response = await api.fetchApi('/kiko_local_image_loader/get_saved_paths');
                        const data = await response.json();
                        const savedPaths = data.saved_paths || [];

                        if (!savedPaths.includes(currentDirectory)) {
                            savedPaths.push(currentDirectory);
                            await api.fetchApi('/kiko_local_image_loader/save_paths', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ paths: savedPaths })
                            });
                            await loadSavedPaths();
                        }
                    } catch (error) {
                        console.error('Error saving path:', error);
                    }
                };

                // Delete selected saved path
                deletePathBtn.onclick = async () => {
                    const selectedPath = pathPresets.value;
                    if (!selectedPath) return;

                    try {
                        const response = await api.fetchApi('/kiko_local_image_loader/get_saved_paths');
                        const data = await response.json();
                        const savedPaths = data.saved_paths || [];

                        const updatedPaths = savedPaths.filter(p => p !== selectedPath);
                        if (updatedPaths.length !== savedPaths.length) {
                            await api.fetchApi('/kiko_local_image_loader/save_paths', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ paths: updatedPaths })
                            });
                            await loadSavedPaths();
                        }
                    } catch (error) {
                        console.error('Error deleting path:', error);
                    }
                };

                // Navigate to parent directory
                upFolderBtn.onclick = () => {
                    if (parentDirectory) {
                        loadImages(parentDirectory);
                    }
                };

                // Load images from directory
                async function loadImages(directory, page = 1) {
                    if (!directory) return;

                    statusMessage.style.display = 'block';
                    statusMessage.textContent = 'Loading...';

                    const params = new URLSearchParams({
                        directory: directory,
                        page: page.toString(),
                        per_page: '50',
                        show_videos: 'true',
                        show_audio: 'true',
                        hide_dot_folders: hideDotFolders.checked,
                        sort_by: sortBy.value,
                        sort_order: sortOrder.value
                    });

                    try {
                        const response = await api.fetchApi(`/kiko_local_image_loader/images?${params}`);
                        const data = await response.json();

                        if (data.error) {
                            statusMessage.textContent = data.error;
                            return;
                        }

                        currentDirectory = data.current_directory;
                        parentDirectory = data.parent_directory;
                        currentPage = data.current_page;
                        totalPages = data.total_pages;
                        currentItems = data.items;

                        pathInput.value = currentDirectory;
                        upFolderBtn.disabled = !parentDirectory;

                        renderGallery();
                        renderPagination();

                        statusMessage.style.display = 'none';
                    } catch (error) {
                        console.error('Error loading images:', error);
                        statusMessage.textContent = 'Error loading directory';
                    }
                }

                // Render gallery cards
                function renderGallery() {
                    cardHolder.innerHTML = '';

                    if (currentItems.length === 0 && !parentDirectory) {
                        cardHolder.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">No items found</div>';
                        return;
                    }

                    // Create items array with parent folder at the beginning if it exists
                    const itemsToRender = parentDirectory
                        ? [{ type: 'parent_dir', name: '..', path: parentDirectory }, ...currentItems]
                        : currentItems;

                    itemsToRender.forEach((item, index) => {
                        const card = document.createElement('div');
                        card.className = 'kiko-gallery-card';

                        if (item.type === 'parent_dir') {
                            // Parent directory (..) with white up arrow on blue folder
                            const upArrowSVG = `<svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><path d="M928 320H488L416 232c-15.1-18.9-38.3-29.9-63.1-29.9H128c-35.3 0-64 28.7-64 64v512c0 35.3 28.7 64 64 64h800c35.3 0 64-28.7 64-64V384c0-35.3-28.7-64-64-64z" fill="#4DA6FF"></path><path d="M512 420l-160 160h112v176h96V580h112z" fill="#FFFFFF" stroke="#333" stroke-width="8"/></svg>`;
                            card.innerHTML = `
                                <div class="kiko-card-media-wrapper">
                                    <div class="kiko-folder-card kiko-parent-folder-card">
                                        <div class="kiko-folder-icon">${upArrowSVG}</div>
                                        <div class="kiko-folder-name">.. (Up)</div>
                                    </div>
                                </div>
                            `;
                            card.onclick = () => {
                                loadImages(item.path);
                            };
                        } else if (item.type === 'dir') {
                            card.innerHTML = `
                                <div class="kiko-card-media-wrapper">
                                    <div class="kiko-folder-card">
                                        <div class="kiko-folder-icon">${folderSVG}</div>
                                        <div class="kiko-folder-name">${item.name}</div>
                                    </div>
                                </div>
                            `;
                            card.onclick = () => {
                                loadImages(item.path);
                            };
                        } else if (item.type === 'image') {
                            const thumbnailUrl = `/kiko_local_image_loader/thumbnail?filepath=${encodeURIComponent(item.path)}`;
                            card.innerHTML = `
                                <div class="kiko-card-media-wrapper">
                                    <img src="${thumbnailUrl}" alt="${item.name}" />
                                </div>
                                <div class="kiko-card-info-panel">${item.name}</div>
                            `;

                            // Trigger layout when image loads
                            const img = card.querySelector('img');
                            if (img) {
                                img.onload = debouncedLayout;
                            }

                            // Single click to select
                            card.onclick = () => selectMedia(item, 'image', card);

                            // Double click to open in new tab
                            card.ondblclick = (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                const fullImageUrl = `/kiko_local_image_loader/view?filepath=${encodeURIComponent(item.path)}`;
                                window.open(fullImageUrl, '_blank');
                            };
                        } else if (item.type === 'video') {
                            const thumbnailUrl = `/kiko_local_image_loader/thumbnail?filepath=${encodeURIComponent(item.path)}`;
                            card.innerHTML = `
                                <div class="kiko-card-media-wrapper">
                                    <img src="${thumbnailUrl}" alt="${item.name}" />
                                    <div class="kiko-video-card-overlay">${videoSVG}</div>
                                </div>
                                <div class="kiko-card-info-panel">${item.name}</div>
                            `;

                            const img = card.querySelector('img');
                            if (img) {
                                img.onload = debouncedLayout;
                            }

                            // Single click to select
                            card.onclick = () => selectMedia(item, 'video', card);

                            // Double click to open in new tab
                            card.ondblclick = (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                const fullVideoUrl = `/kiko_local_image_loader/view?filepath=${encodeURIComponent(item.path)}`;
                                window.open(fullVideoUrl, '_blank');
                            };
                        } else if (item.type === 'audio') {
                            card.innerHTML = `
                                <div class="kiko-card-media-wrapper">
                                    <div class="kiko-audio-card">
                                        <div class="kiko-audio-icon">${audioSVG}</div>
                                        <div class="kiko-audio-name">${item.name}</div>
                                    </div>
                                </div>
                            `;

                            // Single click to select
                            card.onclick = () => selectMedia(item, 'audio', card);

                            // Double click to open in new tab
                            card.ondblclick = (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                const fullAudioUrl = `/kiko_local_image_loader/view?filepath=${encodeURIComponent(item.path)}`;
                                window.open(fullAudioUrl, '_blank');
                            };
                        }

                        // Check if selected
                        if (selectedPaths[item.type] === item.path) {
                            card.classList.add('kiko-selected');
                        }

                        cardHolder.appendChild(card);
                    });

                    // Apply layout after all cards are added
                    requestAnimationFrame(debouncedLayout);
                }

                // Select media
                async function selectMedia(item, type, cardElement) {
                    // Update selection
                    selectedPaths[type] = item.path;

                    // Update UI
                    cardHolder.querySelectorAll('.kiko-gallery-card').forEach(card => {
                        card.classList.remove('kiko-selected');
                    });
                    cardElement.classList.add('kiko-selected');

                    // Send to backend
                    try {
                        await api.fetchApi('/kiko_local_image_loader/set_node_selection', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                node_id: node.id,
                                path: item.path,
                                type: type
                            })
                        });

                        // Trigger node update
                        node.setDirtyCanvas(true);
                    } catch (error) {
                        console.error('Error setting selection:', error);
                    }
                }

                // Render pagination
                function renderPagination() {
                    pagination.innerHTML = '';

                    if (totalPages <= 1) return;

                    const createButton = (text, page) => {
                        const btn = document.createElement('button');
                        btn.textContent = text;
                        btn.style.cssText = 'background: #333; color: #ccc; border: 1px solid #555; padding: 1px 6px; cursor: pointer; font-size: 11px;';
                        if (page === currentPage) {
                            btn.style.background = '#555';
                        }
                        btn.onclick = () => loadImages(currentDirectory, page);
                        return btn;
                    };

                    if (currentPage > 1) {
                        pagination.appendChild(createButton('◀', currentPage - 1));
                    }

                    for (let i = 1; i <= totalPages; i++) {
                        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                            pagination.appendChild(createButton(i.toString(), i));
                        } else if (i === currentPage - 3 || i === currentPage + 3) {
                            const span = document.createElement('span');
                            span.textContent = '...';
                            span.style.padding = '0 5px';
                            pagination.appendChild(span);
                        }
                    }

                    if (currentPage < totalPages) {
                        pagination.appendChild(createButton('▶', currentPage + 1));
                    }
                }

                // Event handlers
                browseBtn.onclick = () => loadImages(pathInput.value || currentDirectory);
                refreshBtn.onclick = () => loadImages(currentDirectory, currentPage);

                pathPresets.onchange = () => {
                    if (pathPresets.value) {
                        loadImages(pathPresets.value);
                    }
                };

                hideDotFolders.onchange = () => loadImages(currentDirectory, 1);
                sortBy.onchange = () => loadImages(currentDirectory, 1);
                sortOrder.onchange = () => loadImages(currentDirectory, 1);

                // Load initial data
                loadSavedPaths();

                // Try to load last path
                api.fetchApi('/kiko_local_image_loader/get_last_path').then(async response => {
                    const data = await response.json();
                    if (data.last_path) {
                        loadImages(data.last_path);
                    }
                });

                return r;
            };
        }
    }
});
