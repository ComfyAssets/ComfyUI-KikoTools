/**
 * KikoSaveImage UI Enhancement
 * Adds clickable image previews and format-specific UI elements
 */

import { app } from "../../scripts/app.js";
import { createButton, createScope, mountTheme } from "./ui/core.js";
import { mountFloatingWindow } from "./ui/floating-window.js";

function injectStyles() {
    const url = new URL('./ui/window.css', import.meta.url).href;
    if ([...document.querySelectorAll('link[rel="stylesheet"]')].some(link => link.href === url)) return;
    const link = document.createElement('link');
    Object.assign(link, { rel: 'stylesheet', href: url });
    document.head.append(link);
}

// Build a ComfyUI /api/view URL with every parameter encoded
function buildViewUrl(filename, subfolder, type) {
    const params = new URLSearchParams({ filename: filename ?? '' });
    if (subfolder && subfolder.trim()) {
        params.set('subfolder', subfolder);
    }
    params.set('type', type || 'output');
    return `${window.location.origin}/api/view?${params.toString()}`;
}

// Format file size for display
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Open image in new tab
function openImageInTab(imagePath, subfolder = '', enablePopup = true, type = 'output') {
    // Note: enablePopup parameter is kept for compatibility but not used
    // since popup now controls viewer visibility, not individual image clicks

    const fullPath = buildViewUrl(imagePath, subfolder, type);

    // Extract clean filename for window name (remove timestamp and batch number)
    const cleanName = imagePath.split('_').slice(0, -2).join('_') || 'KikoSaveImage';

    // Try to open the image with a clean window name
    const newWindow = window.open(fullPath, cleanName.replace(/[^a-zA-Z0-9]/g, '_'));
    if (!newWindow) {
        console.error('KikoSaveImage: Failed to open new window - popup blocked?');
        // Fallback: copy URL to clipboard and alert user
        navigator.clipboard.writeText(fullPath).then(() => {
            alert('Popup blocked! Image URL copied to clipboard: ' + fullPath);
        }).catch(() => {
            alert('Popup blocked! Please copy this URL manually: ' + fullPath);
        });
    }
}

// Define custom web component for image viewer
class KikoImageViewer extends HTMLElement {
    constructor() {
        super();
        this.imageData = [];
        this.selectedImages = new Set();
        this.isMinimized = false;
        this.isRolledUp = false;
        this.openTimers = new Set();
        this.viewerId = `kiko-viewer-${Math.random().toString(36).slice(2)}`;
    }

    static get observedAttributes() { return ['data']; }

    connectedCallback() {
        this.classList.add('ca-tools', 'ca-floating-window');
        this.setAttribute('role', 'dialog');
        this.setAttribute('aria-label', 'Saved images');
        this.activate();
    }

    disconnectedCallback() {
        this.scope?.dispose();
        this.cancelOpens();
    }

    activate() {
        if (this.scope && !this.scope.signal.aborted) return;
        this.scope = createScope();
        mountTheme(this, app.ui.settings, this.scope);
        this.windowController = mountFloatingWindow(this, this.scope, () => this.close());
        this.scope.listen(this, 'click', event => {
            const button = event.target.closest('button[data-action]');
            if (!button) return;
            event.stopPropagation();
            const action = button.dataset.action;
            if (action === 'close') this.close();
            else if (action === 'minimize') this.toggleMinimize();
            else if (button.hasAttribute('data-index')) this.handleActionButton(action, Number(button.dataset.index));
            else this.handleBulkAction(action);
        });
        this.scope.listen(this, 'change', event => {
            if (event.target.matches('input[data-index]')) this.toggleImageSelection(Number(event.target.dataset.index));
        });
        this.scope.listen(this, 'dblclick', event => {
            if (event.target.closest('[data-window-move]')) this.toggleRollUp();
        });
        this.scope.cleanup(() => this.cancelOpens());
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name !== 'data' || !newValue || oldValue === newValue) return;
        try { this.setImageData(JSON.parse(newValue)); }
        catch (error) { console.error('KikoImageViewer: Invalid image data', error); }
    }

    setImageData(data) {
        if (!Array.isArray(data)) return;
        this.cancelOpens();
        this.imageData = data;
        this.classList.toggle('ca-single-image', data.length === 1);
        this.selectedImages.clear();
        this.isMinimized = false;
        this.isRolledUp = false;
        this.classList.remove('ca-minimized', 'rolled-up');
        this.render();
    }

    cancelOpens() {
        this.openTimers.forEach(timer => clearTimeout(timer));
        this.openTimers.clear();
    }

    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        this.isRolledUp = this.isMinimized;
        this.classList.toggle('ca-minimized', this.isMinimized);
        this.classList.toggle('rolled-up', this.isMinimized);
        this.querySelector('.kiko-viewer-container').hidden = this.isMinimized;
        this.querySelector('[data-window-resize]').hidden = this.isMinimized;
        this.querySelector('.ca-window-status').hidden = this.isMinimized;
        const button = this.querySelector('.kiko-minimize-btn');
        button.textContent = this.isMinimized ? '+' : '−';
        button.title = this.isMinimized ? 'Restore' : 'Minimize';
        button.setAttribute('aria-label', `${button.title} image viewer`);
        button.setAttribute('aria-expanded', String(!this.isMinimized));
        this.windowController?.fit();
    }

    toggleRollUp() { this.toggleMinimize(); }

    close() {
        const restoreFocus = this.contains(document.activeElement);
        this.hidden = true;
        this.scope?.dispose();
        this.ownerNode?.updateViewerButton();
        if (restoreFocus && this.returnFocus?.isConnected) this.returnFocus.focus();
    }

    show(focus = false) {
        if (focus && !this.contains(document.activeElement)) this.returnFocus = document.activeElement;
        this.hidden = false;
        if (this.isConnected) this.activate();
        this.windowController?.fit();
        this.ownerNode?.updateViewerButton();
        if (focus) this.querySelector('[data-window-move]')?.focus();
    }

    toggleImageSelection(index) {
        const checkbox = this.querySelector(`input[data-index="${index}"]`);
        if (!checkbox) return;
        if (checkbox.checked) this.selectedImages.add(index);
        else this.selectedImages.delete(index);
        this.updateSelection();
    }

    updateSelection() {
        this.querySelectorAll('input[data-index]').forEach(input => { input.checked = this.selectedImages.has(Number(input.dataset.index)); });
        const count = this.querySelector('.selected-count');
        if (count) count.textContent = this.selectedImages.size;
        this.querySelectorAll('[data-action="open-all"], [data-action="download-all"], [data-action="clear-selection"]').forEach(button => { button.disabled = this.selectedImages.size === 0; });
    }

    handleActionButton(action, index) {
        const image = this.imageData[index];
        if (!image) return;
        if (action === 'download') this.downloadImage(image);
        else if (action === 'open') openImageInTab(image.filename, image.subfolder || '', true, image.type);
    }

    handleBulkAction(action) {
        if (action === 'select-all') this.imageData.forEach((_, index) => this.selectedImages.add(index));
        else if (action === 'clear-selection') this.selectedImages.clear();
        else if (action === 'open-all') this.openAllImagesWithDelay();
        else if (action === 'download-all') this.selectedImages.forEach(index => this.downloadImage(this.imageData[index]));
        this.updateSelection();
    }

    openAllImagesWithDelay() {
        this.cancelOpens();
        [...this.selectedImages].forEach((index, offset) => {
            const image = this.imageData[index];
            const timer = setTimeout(() => {
                this.openTimers.delete(timer);
                openImageInTab(image.filename, image.subfolder || '', true, image.type);
            }, offset * 150);
            this.openTimers.add(timer);
        });
    }

    downloadImage(image) {
        const link = document.createElement('a');
        link.href = buildViewUrl(image.filename, image.subfolder, image.type);
        link.download = image.filename;
        document.body.append(link);
        link.click();
        link.remove();
    }

    render() {
        this.innerHTML = '<header class="ca-window-header kiko-viewer-header"><div class="kiko-viewer-controls"></div></header><div class="kiko-viewer-container"><div class="kiko-image-grid"></div></div><footer class="ca-window-status"></footer>';
        const header = this.querySelector('header');
        const move = createButton(this.imageData.length === 1 ? 'Saved image' : `Saved images · ${this.imageData.length}`, 'ca-window-handle');
        move.setAttribute('data-window-move', '');
        move.setAttribute('aria-label', 'Move image viewer with arrow keys');
        move.title = 'Drag to move · Double-click to minimize';
        header.prepend(move);
        const brand = document.createElement('span');
        brand.className = 'ca-window-brand';
        brand.textContent = 'ComfyAssets';
        move.after(brand);
        const controls = this.querySelector('.kiko-viewer-controls');
        const minimize = createButton('−', 'kiko-control-btn kiko-minimize-btn');
        minimize.dataset.action = 'minimize';
        minimize.title = 'Minimize';
        minimize.setAttribute('aria-label', 'Minimize image viewer');
        minimize.setAttribute('aria-expanded', 'true');
        const close = createButton('×', 'kiko-control-btn kiko-close-btn ca-danger');
        close.dataset.action = 'close';
        close.title = 'Close';
        close.setAttribute('aria-label', 'Close image viewer');
        controls.append(minimize, close);
        this.querySelector('.kiko-image-grid').append(...this.imageData.map((image, index) => this.createImageItem(image, index)));
        if (this.imageData.length > 1) this.createBulkActions();
        const resize = createButton('◢', 'ca-window-resize');
        resize.setAttribute('data-window-resize', '');
        resize.setAttribute('aria-label', 'Resize image viewer with arrow keys');
        this.append(resize);
        this.querySelector('footer').textContent = this.imageData.length ? `${this.imageData.length} saved ${this.imageData.length === 1 ? 'image' : 'images'} · Click a preview to open` : 'No images to display';
        this.updateSelection();
    }

    createBulkActions() {
        const toolbar = document.createElement('div');
        toolbar.className = 'kiko-bulk-actions';
        toolbar.innerHTML = '<span class="selected-count">0</span> selected<div class="kiko-bulk-buttons"></div>';
        for (const [action, text] of [['select-all', 'Select all'], ['clear-selection', 'Clear selection'], ['open-all', 'Open selected'], ['download-all', 'Download selected']]) {
            const button = createButton(text, `kiko-bulk-btn${action === 'download-all' ? ' ca-primary' : ''}`);
            button.dataset.action = action;
            toolbar.querySelector('div').append(button);
        }
        this.querySelector('.kiko-viewer-container').append(toolbar);
    }

    createImageItem(image, index) {
        const item = document.createElement('div');
        item.className = 'kiko-image-item';
        const open = createButton('', 'kiko-image-open');
        open.dataset.action = 'open';
        open.dataset.index = index;
        open.setAttribute('aria-label', `Open image ${index + 1}: ${image.filename}`);
        const img = document.createElement('img');
        Object.assign(img, { src: buildViewUrl(image.filename, image.subfolder, image.type), alt: image.filename, loading: 'lazy' });
        open.append(img);
        const actions = document.createElement('div');
        actions.className = 'kiko-image-actions';
        if (this.imageData.length > 1) {
            const label = document.createElement('label');
            label.className = 'kiko-image-selector';
            const checkbox = document.createElement('input');
            Object.assign(checkbox, { type: 'checkbox', id: `${this.viewerId}-select-${index}` });
            checkbox.dataset.index = index;
            checkbox.setAttribute('aria-label', `Select image ${index + 1}: ${image.filename}`);
            label.htmlFor = checkbox.id;
            label.append(checkbox, document.createTextNode('Select'));
            actions.append(label);
        }
        const download = createButton('↓ Download', 'kiko-action-btn ca-primary');
        download.dataset.action = 'download';
        download.dataset.index = index;
        download.title = 'Download';
        download.setAttribute('aria-label', `Download image ${index + 1}: ${image.filename}`);
        actions.append(download);
        const info = document.createElement('div');
        info.className = 'kiko-image-info';
        const filename = document.createElement('div');
        filename.className = 'kiko-image-filename';
        filename.textContent = image.filename;
        const stats = document.createElement('div');
        stats.className = 'kiko-image-stats';
        let quality = '';
        if (image.format === 'PNG' && image.compress_level !== undefined) quality = ` · C${image.compress_level}`;
        else if (image.format === 'WEBP' && image.lossless) quality = ' · Lossless';
        else if (image.quality !== undefined) quality = ` · Q${image.quality}`;
        stats.textContent = `${image.format || 'PNG'} · ${image.dimensions || 'Unknown'} · ${formatFileSize(image.file_size || 0)}${quality}`;
        info.append(filename, stats);
        item.append(open, actions, info);
        return item;
    }
}

// Register the custom element
if (!customElements.get('kiko-image-viewer')) {
    customElements.define('kiko-image-viewer', KikoImageViewer);
}

// Add format indicator to widget
function addFormatIndicator(node, widget) {
    const indicator = document.createElement('span');
    indicator.className = 'kiko-format-indicator';

    const updateIndicator = (format) => {
        indicator.textContent = format;
        indicator.className = `kiko-format-indicator kiko-format-${format.toLowerCase()}`;
    };

    // Update indicator when format changes
    updateIndicator(widget.value);

    // Find widget element and append indicator
    const widgetElement = widget.element || widget.domWidget;
    if (widgetElement && widgetElement.parentNode) {
        widgetElement.parentNode.appendChild(indicator);
    }

    return { indicator, updateIndicator };
}

// Register ComfyUI extension
app.registerExtension({
    name: "comfyassets.KikoSaveImage",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "KikoSaveImage") {
            // Inject styles when node is registered
            injectStyles();

            // Store original onNodeCreated
            const onNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);

                this.kikoViewerScope = createScope();
                this.createToggleButton();

                // Add format indicator to format widget
                const formatWidget = this.widgets?.find(w => w.name === "format");
                if (formatWidget) {
                    const { indicator, updateIndicator } = addFormatIndicator(this, formatWidget);

                    // Store update function for later use
                    this.updateFormatIndicator = updateIndicator;
                    this.kikoViewerScope.cleanup(() => indicator.remove());
                }

                // Add quality preview for quality widget
                const qualityWidget = this.widgets?.find(w => w.name === "quality");
                if (qualityWidget) {
                    const preview = document.createElement('div');
                    preview.className = 'kiko-quality-preview';
                    preview.textContent = `Quality: ${qualityWidget.value}%`;

                    const widgetElement = qualityWidget.element || qualityWidget.domWidget;
                    if (widgetElement && widgetElement.parentNode) {
                        widgetElement.parentNode.appendChild(preview);
                    }

                    // Store preview element for updates
                    this.qualityPreview = preview;
                    this.kikoViewerScope.cleanup(() => preview.remove());
                }
                return result;
            };

            // Override onWidgetChange to update indicators
            const originalOnWidgetChange = nodeType.prototype.onWidgetChange;
            nodeType.prototype.onWidgetChange = function(name, value, oldValue, widget) {
                // Update format indicator
                if (name === "format" && this.updateFormatIndicator) {
                    this.updateFormatIndicator(value);
                }

                // Update quality preview
                if (name === "quality" && this.qualityPreview) {
                    this.qualityPreview.textContent = `Quality: ${value}%`;
                }

                // Call original handler
                if (originalOnWidgetChange) {
                    return originalOnWidgetChange.call(this, name, value, oldValue, widget);
                }
            };

            // Replace the standard image viewer with our custom web component
            const originalOnExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                // Skip the original ComfyUI preview system
                // Don't call originalOnExecuted to prevent default image display

                // Use our custom web component instead
                if (message && message.kiko_enhanced && message.kiko_enhanced.length > 0) {
                    this.createCustomImageViewer(message.kiko_enhanced);
                } else {
                    // Fall back to standard behavior if no enhanced data
                    if (originalOnExecuted) {
                        originalOnExecuted.apply(this, arguments);
                    }
                }
            };

            const originalOnRemoved = nodeType.prototype.onRemoved;
            nodeType.prototype.onRemoved = function () {
                this.kikoViewerScope?.dispose();
                if (this.kikoViewer?.ownerNode === this) this.kikoViewer.remove();
                this.kikoViewer = null;
                return originalOnRemoved?.apply(this, arguments);
            };

            nodeType.prototype.updateViewerButton = function () {
                if (!this.kikoToggleButton) return;
                const visible = this.kikoViewer?.isConnected && this.kikoViewer.ownerNode === this && !this.kikoViewer.hidden;
                this.kikoToggleButton.disabled = !this.kikoLastImages?.length;
                this.kikoToggleButton.textContent = visible ? 'Hide images' : 'Show images';
                this.kikoToggleButton.setAttribute('aria-expanded', String(Boolean(visible)));
            };

            nodeType.prototype.createCustomImageViewer = function (imageData) {
                if (!Array.isArray(imageData) || !imageData.length) return;
                this.kikoLastImages = imageData;
                this.updateViewerButton();
                if (!imageData[0].popup) return;
                let viewer = document.querySelector('kiko-image-viewer');
                const previousOwner = viewer?.ownerNode;
                if (!viewer) viewer = document.createElement('kiko-image-viewer');
                viewer.ownerNode = this;
                this.kikoViewer = viewer;
                viewer.setImageData(imageData);
                if (!viewer.isConnected) document.body.append(viewer);
                viewer.show();
                previousOwner?.updateViewerButton();
                this.updateViewerButton();
            };

            nodeType.prototype.createToggleButton = function () {
                const container = document.createElement('div');
                container.className = 'ca-tools ca-viewer-launcher';
                const button = createButton('Show images', 'ca-primary kiko-toggle-viewer-btn');
                button.disabled = true;
                button.setAttribute('aria-expanded', 'false');
                container.append(button);
                mountTheme(container, app.ui.settings, this.kikoViewerScope);
                this.addDOMWidget('kiko_saved_image_controls', 'div', container, {
                    serialize: false, hideOnZoom: false,
                    getMinHeight: () => 38, getMaxHeight: () => 38,
                });
                this.kikoToggleButton = button;
                this.kikoViewerScope.cleanup(() => container.remove());
                this.kikoViewerScope.listen(button, 'click', () => {
                    if (!this.kikoLastImages?.length) return;
                    if (this.kikoViewer?.ownerNode === this && this.kikoViewer.isConnected && !this.kikoViewer.hidden) this.kikoViewer.close();
                    else {
                        this.createCustomImageViewer(this.kikoLastImages.map(image => ({ ...image, popup: true })));
                        this.kikoViewer.show(true);
                    }
                });
            };

            // Legacy method kept for compatibility (not used with web component)
            nodeType.prototype.enhanceImagePreviews = function(imageData) {
                // No-op: superseded by the kiko-image-viewer web component
            };
        }
    }
});

// 🎉 RESET VIEWER WINDOWS 🎉
window.kikoResetViewer = function() {
    console.log('🎉 Resetting KikoSaveImage viewer windows...');

    // Remove any existing viewers
    const existingViewers = document.querySelectorAll('kiko-image-viewer');
    existingViewers.forEach(viewer => viewer.remove());

    // Reset toggle buttons
    const toggleButtons = document.querySelectorAll('.kiko-toggle-viewer-btn');
    toggleButtons.forEach(btn => {
        btn.textContent = '👁️ Show Images';

    });

    console.log('✨ Reset complete! Run your workflow to create a new viewer!');
};

// 🚀 FORCE SHOW VIEWER WITH DEMO DATA 🚀
window.kikoForceViewer = function() {
    console.log('🚀 Force showing KikoSaveImage viewer...');

    // Look for existing viewer
    let viewer = document.querySelector('kiko-image-viewer');
    if (viewer) {
        viewer.show();
        console.log('✨ Found and showed existing viewer!');
        return;
    }

    console.log('⚠️ No existing viewer found. Run your KikoSaveImage workflow to create a real viewer with actual images!');
    alert('⚠️ No viewer found! Run your KikoSaveImage workflow to create a viewer with real images.');
};
