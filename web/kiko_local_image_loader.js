import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";
import { createScope } from "./ui/core.js";
import { createImageBrowser } from "./views/image-browser.js";

// Escape a value for safe interpolation into HTML text or attribute contexts
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Build a readable error message from a non-OK fetch response
async function describeHttpError(response) {
    let detail = '';
    try {
        const body = await response.json();
        detail = body?.error || body?.message || '';
    } catch (e) {
        // Non-JSON body; fall back to the status code
    }
    if (response.status === 403) {
        return detail || 'Access denied: path is outside the allowed folders';
    }
    if (response.status === 400) {
        return detail || 'Invalid path or request';
    }
    return detail || `Request failed (HTTP ${response.status})`;
}

app.registerExtension({
    name: "KikoTools.LocalImageLoader",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "KikoLocalImageLoader") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated?.apply(this, arguments);

                const scope = createScope();
                const uniqueId = `kiko-gallery-${Math.random().toString(36).substring(2, 9)}`;
                const galleryContainer = createImageBrowser(uniqueId, app.ui.settings, scope);
                galleryContainer.id = uniqueId;

                const folderSVG = `<svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><path d="M928 320H488L416 232c-15.1-18.9-38.3-29.9-63.1-29.9H128c-35.3 0-64 28.7-64 64v512c0 35.3 28.7 64 64 64h800c35.3 0 64-28.7 64-64V384c0-35.3-28.7-64-64-64z" fill="#F4D03F"></path></svg>`;
                const videoSVG = `<svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><path d="M895.9 203.4H128.1c-35.3 0-64 28.7-64 64v489.2c0 35.3 28.7 64 64 64h767.8c35.3 0 64-28.7 64-64V267.4c0-35.3-28.7-64-64-64zM384 691.2V332.8L668.1 512 384 691.2z" fill="#AED6F1"></path></svg>`;
                const audioSVG = `<svg viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><path d="M768 256H256c-35.3 0-64 28.7-64 64v384c0 35.3 28.7 64 64 64h512c35.3 0 64-28.7 64-64V320c0-35.3-28.7-64-64-64zM512 665.6c-84.8 0-153.6-68.8-153.6-153.6S427.2 358.4 512 358.4s153.6 68.8 153.6 153.6-68.8 153.6-153.6 153.6z" fill="#A9DFBF"></path><path d="M512 409.6c-56.5 0-102.4 45.9-102.4 102.4s45.9 102.4 102.4 102.4 102.4-45.9 102.4-102.4-45.9-102.4-102.4-102.4z" fill="#A9DFBF"></path></svg>`;

                // Add the widget to the node
                this.galleryWidget = this.addDOMWidget("kiko_local_image_gallery", "div", galleryContainer, {
                    serialize: false,
                    hideOnZoom: false,
                    getMinHeight: () => 350,
                });

                // Set initial size for the node
                this.size = [800, 900];
                this.setSize(this.size);

                // Initialize gallery functionality
                const node = this;
                const fetchApi = (path, options = {}) => api.fetchApi(path, { ...options, signal: scope.signal });
                let loadVersion = 0;
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

                const debounce = scope.debounce;
                const originalOnRemoved = this.onRemoved;
                this.onRemoved = function () {
                    scope.dispose();
                    return originalOnRemoved?.apply(this, arguments);
                };
                scope.cleanup(() => { galleryContainer.remove(); });
                scope.listen(container.querySelector('.ca-file-filter'), 'input', renderGallery);

                const showStatus = (message) => {
                    if (scope.signal.aborted) return;
                    statusMessage.style.display = 'block';
                    statusMessage.dataset.state = 'error';
                    statusMessage.textContent = message;
                };

                // Autocomplete functionality
                let autocompleteSelectedIndex = -1;
                let autocompleteSuggestions = [];
                const smallFolderSVG = `<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" width="16" height="16"><path d="M928 320H488L416 232c-15.1-18.9-38.3-29.9-63.1-29.9H128c-35.3 0-64 28.7-64 64v512c0 35.3 28.7 64 64 64h800c35.3 0 64-28.7 64-64V384c0-35.3-28.7-64-64-64z" fill="#F4D03F"></path></svg>`;

                async function fetchDirectorySuggestions(path) {
                    try {
                        const response = await fetchApi(`/kiko_local_image_loader/list_directories?path=${encodeURIComponent(path)}`);
                        if (!response.ok) {
                            // Disallowed or invalid paths simply yield no suggestions
                            return [];
                        }
                        const data = await response.json();
                        return data.directories || [];
                    } catch (error) {
                        if (!scope.signal.aborted) console.error('Error fetching directories:', error);
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
                            <div class="kiko-autocomplete-item" data-index="${index}" data-path="${escapeHtml(path)}">
                                <div class="folder-icon">${smallFolderSVG}</div>
                                <div class="path-text">
                                    <span class="folder-name">${escapeHtml(folderName)}</span>
                                    ${parentPath ? `<span class="parent-path"> — ${escapeHtml(parentPath)}</span>` : ''}
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

                let suggestionVersion = 0;
                const debouncedAutocomplete = debounce(async (value) => {
                    const version = ++suggestionVersion;
                    const suggestions = await fetchDirectorySuggestions(value);
                    if (!scope.signal.aborted && version === suggestionVersion && pathInput.value === value && document.activeElement === pathInput) renderAutocompleteSuggestions(suggestions);
                }, 150);
                const delayedHideAutocomplete = debounce(hideAutocomplete, 150);

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
                    delayedHideAutocomplete();
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
                        const response = await fetchApi('/kiko_local_image_loader/get_saved_paths');
                        if (!response.ok) {
                            throw new Error(await describeHttpError(response));
                        }
                        const data = await response.json();
                        if (scope.signal.aborted) return;

                        pathPresets.innerHTML = '<option value="">-- Saved Paths --</option>';
                        data.saved_paths?.forEach(path => {
                            const option = document.createElement('option');
                            option.value = path;
                            option.textContent = path.split('/').pop() || path;
                            option.title = path;
                            pathPresets.appendChild(option);
                        });
                    } catch (error) {
                        if (!scope.signal.aborted) console.error('Error loading saved paths:', error);
                    }
                }

                // Add a directory to the saved paths (the backend only serves
                // media inside saved paths + ComfyUI input/output).
                // Returns true on success.
                async function addSavedPath(directory) {
                    try {
                        const response = await fetchApi('/kiko_local_image_loader/get_saved_paths');
                        if (!response.ok) {
                            throw new Error(await describeHttpError(response));
                        }
                        const data = await response.json();
                        const savedPaths = data.saved_paths || [];

                        if (!savedPaths.includes(directory)) {
                            const saveResponse = await fetchApi('/kiko_local_image_loader/save_paths', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ paths: [...savedPaths, directory] })
                            });
                            if (!saveResponse.ok) {
                                throw new Error(await describeHttpError(saveResponse));
                            }
                            await loadSavedPaths();
                        }
                        return true;
                    } catch (error) {
                        if (scope.signal.aborted) return false;
                        console.error('Error saving path:', error);
                        showStatus(`Error saving path: ${error.message}`);
                        return false;
                    }
                }

                // Save current path
                savePathBtn.onclick = async () => {
                    if (!currentDirectory) return;
                    await addSavedPath(currentDirectory);
                };

                // Delete selected saved path
                deletePathBtn.onclick = async () => {
                    const selectedPath = pathPresets.value;
                    if (!selectedPath) return;

                    try {
                        const response = await fetchApi('/kiko_local_image_loader/get_saved_paths');
                        if (!response.ok) {
                            throw new Error(await describeHttpError(response));
                        }
                        const data = await response.json();
                        const savedPaths = data.saved_paths || [];

                        const updatedPaths = savedPaths.filter(p => p !== selectedPath);
                        if (updatedPaths.length !== savedPaths.length) {
                            const saveResponse = await fetchApi('/kiko_local_image_loader/save_paths', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ paths: updatedPaths })
                            });
                            if (!saveResponse.ok) {
                                throw new Error(await describeHttpError(saveResponse));
                            }
                            await loadSavedPaths();
                        }
                    } catch (error) {
                        if (scope.signal.aborted) return;
                        console.error('Error deleting path:', error);
                        showStatus(`Error deleting path: ${error.message}`);
                    }
                };

                // Navigate to parent directory
                upFolderBtn.onclick = () => {
                    if (parentDirectory) {
                        loadImages(parentDirectory);
                    }
                };

                // Called when the user browses to a folder that isn't a saved
                // path yet (backend answered 403). statusMessage is visible.
                // Adding a folder is an explicit click (never automatic), and the
                // full path is shown so the user sees exactly what they expose.
                // The server rejects "/" and the home folder itself.
                function handleFolderNotAllowed(directory, page) {
                    statusMessage.textContent = 'This folder is not in your saved paths: ';
                    const pathLabel = document.createElement('code');
                    pathLabel.textContent = directory;
                    const addBtn = document.createElement('button');
                    addBtn.textContent = 'Add folder & open';
                    addBtn.type = 'button';
                    addBtn.className = 'ca-primary';
                    statusMessage.dataset.state = 'error';
                    addBtn.onclick = async () => {
                        addBtn.disabled = true;
                        // On failure addSavedPath shows the server's reason
                        if (await addSavedPath(directory)) {
                            loadImages(directory, page);
                        }
                    };
                    statusMessage.append(pathLabel, addBtn);
                }

                // Load images from directory
                async function loadImages(directory, page = 1) {
                    if (!directory || scope.signal.aborted) return;
                    const version = ++loadVersion;
                    statusMessage.dataset.state = 'loading';

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
                        const response = await fetchApi(`/kiko_local_image_loader/images?${params}`);
                        if (scope.signal.aborted || version !== loadVersion) return;
                        if (response.status === 403) {
                            handleFolderNotAllowed(directory, page);
                            return;
                        }
                        if (!response.ok) {
                            const message = await describeHttpError(response);
                            if (version === loadVersion) showStatus(message);
                            return;
                        }
                        const data = await response.json();

                        if (scope.signal.aborted || version !== loadVersion) return;
                        if (data.error) {
                            showStatus(data.error);
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
                        if (scope.signal.aborted || version !== loadVersion) return;
                        console.error('Error loading images:', error);
                        showStatus('Error loading directory');
                    }
                }

                // Render gallery cards
                function renderGallery() {
                    cardHolder.innerHTML = '';

                    // Create items array with parent folder at the beginning if it exists
                    const query = container.querySelector('.ca-file-filter').value.toLowerCase();
                    const visibleItems = currentItems.filter(item => item.name.toLowerCase().includes(query));
                    if (visibleItems.length === 0) {
                        const empty = document.createElement('div');
                        empty.className = 'ca-empty';
                        empty.textContent = query ? 'No matching items on this page' : 'No items found';
                        cardHolder.append(empty);
                    }
                    const itemsToRender = parentDirectory
                        ? [{ type: 'parent_dir', name: '..', path: parentDirectory }, ...visibleItems]
                        : visibleItems;

                    itemsToRender.forEach((item, index) => {
                        const card = document.createElement('button');
                        card.type = 'button';
                        card.setAttribute('aria-label', item.type === 'dir' || item.type === 'parent_dir' ? `Open folder ${item.name}` : `Select ${item.type} ${item.name}`);
                        if (!['dir', 'parent_dir'].includes(item.type)) card.setAttribute('aria-pressed', String(selectedPaths[item.type] === item.path));
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
                                        <div class="kiko-folder-name">${escapeHtml(item.name)}</div>
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
                                    <img src="${escapeHtml(thumbnailUrl)}" alt="${escapeHtml(item.name)}" />
                                </div>
                                <div class="kiko-card-info-panel">${escapeHtml(item.name)}</div>
                            `;

                            // Trigger layout when image loads

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
                                    <img src="${escapeHtml(thumbnailUrl)}" alt="${escapeHtml(item.name)}" />
                                    <div class="kiko-video-card-overlay">${videoSVG}</div>
                                </div>
                                <div class="kiko-card-info-panel">${escapeHtml(item.name)}</div>
                            `;


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
                                        <div class="kiko-audio-name">${escapeHtml(item.name)}</div>
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

                    container.querySelector('[data-file-count]').textContent = `${visibleItems.length} of ${currentItems.length} items`;

                }

                // Select media
                async function selectMedia(item, type, cardElement) {
                    // Update selection
                    const previousPath = selectedPaths[type];
                    selectedPaths[type] = item.path;

                    // Update UI
                    cardHolder.querySelectorAll('.kiko-gallery-card').forEach(card => {
                        card.classList.remove('kiko-selected');
                        if (card.hasAttribute('aria-pressed')) card.setAttribute('aria-pressed', 'false');
                    });
                    cardElement.classList.add('kiko-selected');
                    cardElement.setAttribute('aria-pressed', 'true');

                    // Send to backend
                    try {
                        const response = await fetchApi('/kiko_local_image_loader/set_node_selection', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                node_id: node.id,
                                path: item.path,
                                type: type
                            })
                        });
                        if (!response.ok) {
                            selectedPaths[type] = previousPath;
                            renderGallery();
                            showStatus(`Selection rejected: ${await describeHttpError(response)}`);
                            return;
                        }

                        if (scope.signal.aborted) return;
                        container.querySelector('[data-selection]').textContent = item.name;
                        node.setDirtyCanvas(true);
                    } catch (error) {
                        if (scope.signal.aborted) return;
                        selectedPaths[type] = previousPath;
                        renderGallery();
                        console.error('Error setting selection:', error);
                        showStatus('Error setting selection');
                    }
                }

                // Render pagination
                function renderPagination() {
                    pagination.innerHTML = '';

                    if (totalPages <= 1) return;

                    const createButton = (text, page) => {
                        const btn = document.createElement('button');
                        btn.textContent = text;
                        btn.type = 'button';
                        if (page === currentPage) {
                            btn.setAttribute('aria-current', 'page');
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
                fetchApi('/kiko_local_image_loader/get_last_path').then(async response => {
                    if (!response.ok) return;
                    const data = await response.json();
                    if (data.last_path && loadVersion === 0 && !scope.signal.aborted) {
                        loadImages(data.last_path);
                    }
                }).catch(error => {
                    if (!scope.signal.aborted) console.error('Error loading last path:', error);
                });

                return r;
            };
        }
    }
});
