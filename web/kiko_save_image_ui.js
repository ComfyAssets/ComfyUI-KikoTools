/**
 * KikoSaveImage UI Enhancement
 * Adds clickable image previews and format-specific UI elements
 */

import { app } from "../../scripts/app.js";

// CSS styles for enhanced image previews and web component
const KIKO_SAVE_IMAGE_STYLES = `
/* Custom Web Component Styles - Floating Draggable Window */
kiko-image-viewer {
    position: fixed;
    top: 100px;
    right: 20px;
    width: 420px;
    max-width: 90vw;
    max-height: 80vh;
    background: #2a2a2a;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    border: 1px solid #444;
    z-index: 10000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    resize: both;
    min-width: 300px;
    min-height: 200px;
    transition: background 0.3s ease, box-shadow 0.3s ease, border 0.3s ease;
}

kiko-image-viewer.rolled-up {
    background: transparent;
    box-shadow: none;
    border: none;
    overflow: visible;
    resize: none;
    min-height: auto;
}

kiko-image-viewer.dragging {
    transition: none;
    z-index: 10001;
}

kiko-image-viewer.dragging .kiko-viewer-header {
    background: linear-gradient(135deg, #388E3C, #2E7D32);
}

.kiko-viewer-container {
    padding: 12px;
    max-height: calc(80vh - 80px);
    overflow-y: auto;
    overflow-x: hidden;
    transition: max-height 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
                padding 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                opacity 0.3s ease;
}

kiko-image-viewer.rolled-up .kiko-viewer-container {
    max-height: 0;
    padding: 0 12px;
    opacity: 0;
    overflow: hidden;
}

.kiko-viewer-header {
    background: linear-gradient(135deg, #4CAF50, #45a049);
    padding: 12px 16px;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    border-bottom: 1px solid #555;
    cursor: move;
    user-select: none;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
}

.kiko-viewer-header::after {
    content: '';
    position: absolute;
    bottom: 2px;
    left: 50%;
    transform: translateX(-50%);
    width: 30px;
    height: 3px;
    background: rgba(255, 255, 255, 0.3);
    border-radius: 2px;
    opacity: 0;
    transition: opacity 0.3s ease;
}

kiko-image-viewer.rolled-up .kiko-viewer-header::after {
    opacity: 1;
}

kiko-image-viewer.rolled-up .kiko-viewer-header {
    border-bottom: none;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}

.kiko-viewer-title {
    flex: 1;
}

.kiko-viewer-controls {
    display: flex;
    gap: 8px;
    align-items: center;
}

.kiko-control-btn {
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    width: 24px;
    height: 24px;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    transition: background 0.2s ease;
}

.kiko-control-btn:hover {
    background: rgba(255,255,255,0.3);
}

.kiko-minimize-btn:hover {
    background: rgba(255,193,7,0.8);
}

.kiko-close-btn:hover {
    background: rgba(244,67,54,0.8);
}

.kiko-image-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
    margin-top: 8px;
}

.kiko-image-item {
    position: relative;
    background: #1a1a1a;
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: 2px solid transparent;
    cursor: default;
}

.kiko-image-item:hover {
    border-color: #4CAF50;
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(76, 175, 80, 0.4);
}

.kiko-image-item img {
    width: 100%;
    height: 120px;
    display: block;
    object-fit: cover;
    transition: transform 0.3s ease;
}

.kiko-image-item:hover img {
    transform: scale(1.05);
}

.kiko-image-actions {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    gap: 6px;
    opacity: 0;
    transform: translateY(-10px);
    transition: all 0.3s ease;
}

.kiko-image-item:hover .kiko-image-actions {
    opacity: 1;
    transform: translateY(0);
}

.kiko-action-btn {
    background: rgba(0,0,0,0.8);
    border: none;
    color: white;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    transition: all 0.2s ease;
    backdrop-filter: blur(10px);
}

.kiko-action-btn:hover {
    background: rgba(76, 175, 80, 0.9);
    transform: scale(1.1);
}

.kiko-action-btn.download:hover {
    background: rgba(33, 150, 243, 0.9);
}

.kiko-action-btn.copy:hover {
    background: rgba(156, 39, 176, 0.9);
}

.kiko-image-selector {
    position: absolute;
    top: 8px;
    left: 8px;
    width: 24px;
    height: 24px;
    background: rgba(0,0,0,0.8);
    border: 2px solid white;
    border-radius: 4px;
    cursor: pointer;
    opacity: 0;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
}

.kiko-image-item:hover .kiko-image-selector {
    opacity: 1;
}

.kiko-image-selector.selected {
    background: #4CAF50;
    border-color: #4CAF50;
    opacity: 1;
}

.kiko-image-selector.selected::after {
    content: '✓';
    color: white;
    font-size: 12px;
    font-weight: bold;
}

.kiko-image-info {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background: linear-gradient(transparent, rgba(0,0,0,0.9));
    color: white;
    padding: 8px 6px 4px;
    font-size: 10px;
    line-height: 1.2;
}

.kiko-image-filename {
    font-weight: bold;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.kiko-image-details {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 4px;
}

.kiko-format-badge {
    display: inline-block;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9px;
    font-weight: bold;
    text-transform: uppercase;
}

.kiko-format-png { background-color: #2196F3; }
.kiko-format-jpeg { background-color: #FF9800; }
.kiko-format-webp { background-color: #4CAF50; }

.kiko-image-stats {
    font-size: 9px;
    opacity: 0.8;
}

.kiko-click-hint {
    position: absolute;
    top: 4px;
    right: 4px;
    background: rgba(0,0,0,0.7);
    color: white;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 9px;
    opacity: 0;
    transition: opacity 0.2s ease;
}

.kiko-image-item:hover .kiko-click-hint {
    opacity: 1;
}

.kiko-bulk-btn {
    background: #444;
    border: 1px solid #666;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 10px;
    transition: all 0.2s ease;
}

.kiko-bulk-btn:hover {
    background: #4CAF50;
    border-color: #4CAF50;
    transform: translateY(-1px);
}

/* Legacy styles for fallback */
.kiko-save-image-preview {
    position: relative;
    display: inline-block;
    margin: 4px;
    border: 2px solid #333;
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    transition: all 0.2s ease;
}

.kiko-save-image-preview:hover {
    border-color: #555;
    transform: scale(1.02);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.kiko-format-indicator {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: bold;
    margin-left: 4px;
}

.kiko-quality-preview {
    font-size: 11px;
    color: #888;
    margin-top: 2px;
}
`;

// Inject CSS styles
function injectStyles() {
    if (!document.getElementById('kiko-save-image-styles')) {
        const style = document.createElement('style');
        style.id = 'kiko-save-image-styles';
        style.textContent = KIKO_SAVE_IMAGE_STYLES;
        document.head.appendChild(style);
    }
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
function openImageInTab(imagePath, enablePopup = true) {
    console.log(`KikoSaveImage: Attempting to open image: ${imagePath}`);
    
    // Note: enablePopup parameter is kept for compatibility but not used
    // since popup now controls viewer visibility, not individual image clicks
    
    const basePath = window.location.origin;
    
    // Properly encode the filename for URL
    const encodedFilename = encodeURIComponent(imagePath);
    const fullPath = `${basePath}/api/view?filename=${encodedFilename}&type=output`;
    
    console.log(`KikoSaveImage: Opening URL: ${fullPath}`);
    
    // Extract clean filename for window name (remove timestamp and batch number)
    const cleanName = imagePath.split('_').slice(0, -2).join('_') || 'KikoSaveImage';
    
    // Try to open the image with a clean window name
    const newWindow = window.open(fullPath, cleanName.replace(/[^a-zA-Z0-9]/g, '_'));
    if (newWindow) {
        console.log('KikoSaveImage: Successfully opened new window');
    } else {
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
        this.isDragging = false;
        this.isMinimized = false;
        this.isRolledUp = false;
        this.dragOffset = { x: 0, y: 0 };
        this.lastHeaderClick = 0;
        
        // Always start at default position
    }
    
    static get observedAttributes() {
        return ['data'];
    }
    
    attributeChangedCallback(name, oldValue, newValue) {
        if (name === 'data' && newValue) {
            try {
                this.imageData = JSON.parse(newValue);
                this.autoUnrollOnNewImages();
                this.render();
            } catch (e) {
                console.error('KikoImageViewer: Failed to parse image data:', e);
            }
        }
    }
    
    setImageData(data) {
        console.log('KikoImageViewer: setImageData called with:', data);
        console.log('KikoImageViewer: First image data:', data[0]);
        this.imageData = data;
        this.autoUnrollOnNewImages();
        this.render();
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Window dragging and double-click functionality
        const header = this.querySelector('.kiko-viewer-header');
        if (header) {
            header.addEventListener('mousedown', this.startDrag.bind(this));
            header.addEventListener('dblclick', this.handleHeaderDoubleClick.bind(this));
        }
        
        // Control buttons
        const minimizeBtn = this.querySelector('.kiko-minimize-btn');
        const closeBtn = this.querySelector('.kiko-close-btn');
        
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', this.toggleMinimize.bind(this));
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', this.close.bind(this));
        }
        
        // Image selection checkboxes
        const selectors = this.querySelectorAll('.kiko-image-selector');
        selectors.forEach((selector, index) => {
            selector.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleImageSelection(index);
            });
        });
        
        // Action buttons
        const actionButtons = this.querySelectorAll('.kiko-action-btn');
        actionButtons.forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = btn.dataset.action;
                const index = parseInt(btn.dataset.index);
                this.handleActionButton(action, index);
            });
        });
        
        // Bulk action buttons
        const bulkButtons = this.querySelectorAll('.kiko-bulk-btn');
        bulkButtons.forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = btn.dataset.action;
                this.handleBulkAction(action);
            });
        });
        
        // Global mouse events for dragging
        document.addEventListener('mousemove', this.handleDrag.bind(this));
        document.addEventListener('mouseup', this.endDrag.bind(this));
    }
    
    startDrag(e) {
        // Don't start dragging if clicking on control buttons
        if (e.target.closest('.kiko-viewer-controls')) {
            return;
        }
        
        this.isDragging = true;
        const rect = this.getBoundingClientRect();
        this.dragOffset = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
        
        // Prevent text selection while dragging
        e.preventDefault();
        
        // Add dragging class for visual feedback
        this.classList.add('dragging');
    }
    
    handleDrag(e) {
        if (!this.isDragging) return;
        
        e.preventDefault();
        
        const x = e.clientX - this.dragOffset.x;
        const y = e.clientY - this.dragOffset.y;
        
        // Keep window within viewport bounds
        const maxX = window.innerWidth - this.offsetWidth;
        const maxY = window.innerHeight - this.offsetHeight;
        
        const boundedX = Math.max(0, Math.min(x, maxX));
        const boundedY = Math.max(0, Math.min(y, maxY));
        
        this.style.left = boundedX + 'px';
        this.style.top = boundedY + 'px';
        this.style.right = 'auto'; // Override CSS right positioning
    }
    
    endDrag(e) {
        if (!this.isDragging) return;
        
        this.isDragging = false;
        this.classList.remove('dragging');
    }
    
    handleHeaderDoubleClick(e) {
        // Don't toggle if clicking on control buttons
        if (e.target.closest('.kiko-viewer-controls')) {
            return;
        }
        
        this.toggleRollUp();
    }
    
    autoUnrollOnNewImages() {
        // Auto-unroll if currently rolled up and we have new image data
        if (this.isRolledUp && this.imageData && this.imageData.length > 0) {
            this.isRolledUp = false;
            this.classList.remove('rolled-up');
        }
    }
    
    toggleRollUp() {
        this.isRolledUp = !this.isRolledUp;
        
        if (this.isRolledUp) {
            this.classList.add('rolled-up');
        } else {
            this.classList.remove('rolled-up');
        }
    }
    
    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        const container = this.querySelector('.kiko-viewer-container');
        const minimizeBtn = this.querySelector('.kiko-minimize-btn');
        
        if (container && minimizeBtn) {
            if (this.isMinimized) {
                container.style.display = 'none';
                minimizeBtn.textContent = '+';
                minimizeBtn.title = 'Restore';
            } else {
                container.style.display = 'block';
                minimizeBtn.textContent = '−';
                minimizeBtn.title = 'Minimize';
            }
        }
    }
    
    close() {
        this.style.display = 'none';
    }
    
    show() {
        this.style.display = 'block';
    }
    
    toggleImageSelection(index) {
        const selector = this.querySelector(`[data-index="${index}"].kiko-image-selector`);
        if (!selector) return;
        
        if (this.selectedImages.has(index)) {
            this.selectedImages.delete(index);
            selector.classList.remove('selected');
        } else {
            this.selectedImages.add(index);
            selector.classList.add('selected');
        }
        
        this.updateBulkActionsVisibility();
        this.updateSelectedCount();
    }
    
    updateBulkActionsVisibility() {
        const bulkActions = this.querySelector('.kiko-bulk-actions');
        if (bulkActions) {
            bulkActions.style.display = this.selectedImages.size > 0 ? 'block' : 'none';
        }
    }
    
    updateSelectedCount() {
        const countSpan = this.querySelector('.selected-count');
        if (countSpan) {
            countSpan.textContent = this.selectedImages.size;
        }
    }
    
    handleActionButton(action, index) {
        const imageData = this.imageData[index];
        if (!imageData) return;
        
        switch (action) {
            case 'download':
                this.downloadImage(imageData);
                break;
        }
    }
    
    handleBulkAction(action) {
        switch (action) {
            case 'open-all':
                this.openAllImagesWithDelay();
                break;
            case 'download-all':
                this.selectedImages.forEach(index => {
                    const imageData = this.imageData[index];
                    if (imageData) {
                        this.downloadImage(imageData);
                    }
                });
                break;
            case 'select-all':
                this.imageData.forEach((_, index) => {
                    this.selectedImages.add(index);
                    const selector = this.querySelector(`[data-index="${index}"].kiko-image-selector`);
                    if (selector) {
                        selector.classList.add('selected');
                    }
                });
                this.updateBulkActionsVisibility();
                this.updateSelectedCount();
                break;
            case 'clear-selection':
                this.selectedImages.clear();
                this.querySelectorAll('.kiko-image-selector.selected').forEach(selector => {
                    selector.classList.remove('selected');
                });
                this.updateBulkActionsVisibility();
                this.updateSelectedCount();
                break;
        }
    }
    
    openAllImagesWithDelay() {
        const selectedIndices = Array.from(this.selectedImages);
        if (selectedIndices.length === 0) {
            console.log('KikoSaveImage: No images selected for opening');
            return;
        }
        
        console.log(`KikoSaveImage: Opening ${selectedIndices.length} images with delay`);
        
        // Open images with 150ms delay between each to prevent popup blocking
        selectedIndices.forEach((index, i) => {
            setTimeout(() => {
                const imageData = this.imageData[index];
                if (imageData) {
                    openImageInTab(imageData.filename);
                }
            }, i * 150);
        });
    }
    
    downloadImage(imageData) {
        const imageUrl = `${window.location.origin}/api/view?filename=${encodeURIComponent(imageData.filename)}&type=${imageData.type}`;
            
        // Create temporary link and trigger download
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = imageData.filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    
    render() {
        if (!this.imageData || this.imageData.length === 0) {
            this.innerHTML = `
                <div class="kiko-viewer-header">
                    <div class="kiko-viewer-title">No images to display</div>
                    <div class="kiko-viewer-controls">
                        <button class="kiko-control-btn kiko-close-btn" title="Close">×</button>
                    </div>
                </div>
            `;
            return;
        }
        
        const header = this.imageData.length === 1 
            ? `Saved Image (${this.imageData[0].format})`
            : `Saved Images (${this.imageData.length} files)`;
            
        const containerStyle = this.isMinimized ? 'style="display: none;"' : '';
            
        this.innerHTML = `
            <div class="kiko-viewer-header">
                <div class="kiko-viewer-title">${header}</div>
                <div class="kiko-viewer-controls">
                    <button class="kiko-control-btn kiko-minimize-btn" title="Minimize">−</button>
                    <button class="kiko-control-btn kiko-close-btn" title="Close">×</button>
                </div>
            </div>
            <div class="kiko-viewer-container" ${containerStyle}>
                <div class="kiko-image-grid">
                    ${this.imageData.map((data, index) => this.createImageItem(data, index)).join('')}
                </div>
                ${this.imageData.length > 1 ? this.createBulkActions() : ''}
            </div>
        `;
        
        // Add all event handlers
        this.addClickHandlers();
    }
    
    createBulkActions() {
        return `
            <div class="kiko-bulk-actions" style="margin-top: 12px; padding: 8px; background: #333; border-radius: 6px; display: none;">
                <div style="font-size: 11px; color: #ccc; margin-bottom: 6px;">
                    <span class="selected-count">0</span> selected
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="kiko-bulk-btn" data-action="open-all">📂 Open All</button>
                    <button class="kiko-bulk-btn" data-action="download-all">💾 Download All</button>
                    <button class="kiko-bulk-btn" data-action="select-all">☑️ Select All</button>
                    <button class="kiko-bulk-btn" data-action="clear-selection">❌ Clear</button>
                </div>
            </div>
        `;
    }
    
    createImageItem(data, index) {
        const imageUrl = `${window.location.origin}/api/view?filename=${encodeURIComponent(data.filename)}&type=${data.type}`;
            
        const formatClass = `kiko-format-${data.format.toLowerCase()}`;
        
        // Format file size
        const fileSize = data.file_size ? formatFileSize(data.file_size) : 'Unknown';
        
        // Build quality info
        let qualityInfo = '';
        if (data.format === 'PNG' && data.compress_level !== undefined) {
            qualityInfo = `C${data.compress_level}`;
        } else if ((data.format === 'JPEG' || data.format === 'WEBP') && data.quality !== undefined) {
            if (data.format === 'WEBP' && data.lossless) {
                qualityInfo = 'Lossless';
            } else {
                qualityInfo = `Q${data.quality}`;
            }
        }
        
        return `
            <div class="kiko-image-item" data-index="${index}">
                <img src="${imageUrl}" alt="${data.filename}" loading="lazy" />
                
                ${this.imageData.length > 1 ? `
                    <div class="kiko-image-selector" data-index="${index}" title="Select image"></div>
                ` : ''}
                
                <div class="kiko-image-actions">
                    <button class="kiko-action-btn download" data-action="download" data-index="${index}" title="Download">💾</button>
                </div>
                
                <div class="kiko-image-info">
                    <div class="kiko-image-filename" title="${data.filename}">
                        ${data.filename}
                    </div>
                    <div class="kiko-image-details">
                        <div class="kiko-image-stats">
                            <span class="kiko-format-badge ${formatClass}">${data.format}</span>
                            ${data.dimensions || 'Unknown'} • ${fileSize}
                            ${qualityInfo ? ` • ${qualityInfo}` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    addClickHandlers() {
        const items = this.querySelectorAll('.kiko-image-item');
        items.forEach((item, index) => {
            const data = this.imageData[index];
            if (data) {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log(`KikoImageViewer: Clicking image ${index}: ${data.filename}`);
                    openImageInTab(data.filename);
                });
            }
        });
    }
}

// Register the custom element
if (!customElements.get('kiko-image-viewer')) {
    customElements.define('kiko-image-viewer', KikoImageViewer);
}

// Create enhanced image preview element
function createImagePreview(imageData) {
    const container = document.createElement('div');
    container.className = 'kiko-save-image-preview';
    
    // Create image element
    const img = document.createElement('img');
    const imagePath = `/api/view?filename=${imageData.filename}&type=${imageData.type}`;
    img.src = imagePath;
    img.alt = imageData.filename;
    
    // Create info overlay
    const info = document.createElement('div');
    info.className = 'kiko-save-image-info';
    
    const formatSpan = document.createElement('span');
    formatSpan.className = 'kiko-save-image-format';
    formatSpan.textContent = imageData.format || 'PNG';
    
    const sizeSpan = document.createElement('span');
    sizeSpan.className = 'kiko-save-image-size';
    sizeSpan.textContent = ` • ${imageData.dimensions || 'Unknown'}`;
    
    const fileSizeSpan = document.createElement('span');
    fileSizeSpan.className = 'kiko-save-image-size';
    fileSizeSpan.textContent = ` • ${formatFileSize(imageData.file_size || 0)}`;
    
    info.appendChild(formatSpan);
    info.appendChild(sizeSpan);
    info.appendChild(fileSizeSpan);
    
    // Add quality info for JPEG/WebP
    if (imageData.quality && (imageData.format === 'JPEG' || imageData.format === 'WEBP')) {
        const qualitySpan = document.createElement('span');
        qualitySpan.className = 'kiko-save-image-quality';
        let qualityText = ` • Q${imageData.quality}`;
        if (imageData.format === 'WEBP' && imageData.lossless) {
            qualityText = ' • Lossless';
        }
        qualitySpan.textContent = qualityText;
        info.appendChild(qualitySpan);
    } else if (imageData.compress_level !== undefined && imageData.format === 'PNG') {
        const compressSpan = document.createElement('span');
        compressSpan.className = 'kiko-save-image-quality';
        compressSpan.textContent = ` • C${imageData.compress_level}`;
        info.appendChild(compressSpan);
    }
    
    container.appendChild(img);
    container.appendChild(info);
    
    // Add click handler to open in new tab
    container.addEventListener('click', () => {
        openImageInTab(imageData.filename);
    });
    
    return container;
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
                // Call original onNodeCreated
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Add format indicator to format widget
                const formatWidget = this.widgets?.find(w => w.name === "format");
                if (formatWidget) {
                    const { indicator, updateIndicator } = addFormatIndicator(this, formatWidget);
                    
                    // Store update function for later use
                    this.updateFormatIndicator = updateIndicator;
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
                }
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
                console.log('KikoSaveImage: onExecuted called with message:', message);
                
                // Skip the original ComfyUI preview system
                // Don't call originalOnExecuted to prevent default image display
                
                // Use our custom web component instead
                if (message && message.kiko_enhanced && message.kiko_enhanced.length > 0) {
                    console.log('KikoSaveImage: Creating custom image viewer');
                    this.createCustomImageViewer(message.kiko_enhanced);
                } else {
                    console.log('KikoSaveImage: No enhanced data found, falling back to standard preview');
                    // Fall back to standard behavior if no enhanced data
                    if (originalOnExecuted) {
                        originalOnExecuted.apply(this, arguments);
                    }
                }
            };
            
            // Add method to create custom image viewer
            nodeType.prototype.createCustomImageViewer = function(imageData) {
                console.log('KikoSaveImage: Creating custom viewer for', imageData.length, 'images');
                
                // Check if popup is enabled for any image (use first image's popup setting)
                const popupEnabled = imageData.length > 0 ? imageData[0].popup : true;
                console.log('KikoSaveImage: Popup enabled:', popupEnabled);
                
                if (!popupEnabled) {
                    console.log('KikoSaveImage: Popup disabled, not showing custom viewer');
                    return;
                }
                
                // Check if viewer already exists
                let existingViewer = document.querySelector('kiko-image-viewer');
                if (existingViewer) {
                    // Update existing viewer with new data
                    existingViewer.setImageData(imageData);
                    existingViewer.show(); // Make sure it's visible
                    console.log('KikoSaveImage: Updated existing viewer');
                    return;
                }
                
                // Create toggle button in node if it doesn't exist
                if (!this.kikoToggleButton) {
                    this.createToggleButton();
                }
                
                // Create new viewer - always visible on workflow execution
                const viewer = document.createElement('kiko-image-viewer');
                viewer.setImageData(imageData);
                
                // Store reference for toggle button
                this.kikoViewer = viewer;
                
                // Update toggle button text
                if (this.kikoToggleButton) {
                    this.kikoToggleButton.textContent = '👁️ Hide Images';
                }
                
                // Append to body (floating window) - always visible
                document.body.appendChild(viewer);
                
                console.log('KikoSaveImage: Custom viewer created successfully');
            };
            
            // Add method to create toggle button
            nodeType.prototype.createToggleButton = function() {
                // Find the node element to add button to
                let nodeElement = null;
                
                if (this.domElement) {
                    nodeElement = this.domElement;
                } else if (this.widgets && this.widgets[0] && this.widgets[0].element) {
                    nodeElement = this.widgets[0].element.closest('.litegraph-node');
                } else {
                    // Find by node title
                    const allNodes = document.querySelectorAll('.litegraph-node');
                    for (const node of allNodes) {
                        if (node.textContent && node.textContent.includes('Kiko Save Image')) {
                            nodeElement = node;
                            break;
                        }
                    }
                }
                
                if (!nodeElement) return;
                
                // Create toggle button
                const toggleButton = document.createElement('button');
                toggleButton.textContent = '👁️ Show Images';
                toggleButton.className = 'kiko-toggle-viewer-btn';
                toggleButton.style.cssText = `
                    margin: 4px;
                    padding: 4px 8px;
                    background: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 11px;
                    font-family: inherit;
                `;
                
                toggleButton.addEventListener('click', () => {
                    if (this.kikoViewer) {
                        const isHidden = this.kikoViewer.style.display === 'none';
                        if (isHidden) {
                            this.kikoViewer.show();
                            toggleButton.textContent = '👁️ Hide Images';
                        } else {
                            this.kikoViewer.close();
                            toggleButton.textContent = '👁️ Show Images';
                        }
                    }
                });
                
                // Add hover effects
                toggleButton.addEventListener('mouseenter', () => {
                    toggleButton.style.background = '#45a049';
                });
                toggleButton.addEventListener('mouseleave', () => {
                    toggleButton.style.background = '#4CAF50';
                });
                
                nodeElement.appendChild(toggleButton);
                this.kikoToggleButton = toggleButton;
                
                console.log('KikoSaveImage: Toggle button created');
            };
            
            // Legacy method kept for compatibility (not used with web component)
            nodeType.prototype.enhanceImagePreviews = function(imageData) {
                console.log('KikoSaveImage: Legacy enhanceImagePreviews called (should use web component instead)');
            };
        }
    }
});

// Export helper functions to global scope for debugging
window.kikoSaveImageTest = function() {
    console.log('KikoSaveImage: Testing click functionality...');
    
    // Find all images in the document
    const allImages = document.querySelectorAll('img');
    console.log(`Found ${allImages.length} images in document`);
    
    // Try to find images that look like our saved images
    allImages.forEach((img, index) => {
        console.log(`Image ${index}: src = ${img.src}`);
        
        // Add test click handler to all images
        img.style.border = '2px solid red';
        img.style.cursor = 'pointer';
        img.title = 'TEST: Click to open in new tab';
        
        // Remove old handlers and add new one
        const newImg = img.cloneNode(true);
        img.parentNode.replaceChild(newImg, img);
        
        newImg.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('TEST CLICK WORKED!', newImg.src);
            window.open(newImg.src, '_blank');
        }, true);
    });
    
    console.log('KikoSaveImage: Test setup complete. All images should now be clickable with red borders.');
};

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
        btn.style.background = '#4CAF50';
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

console.log('🎉 KikoSaveImage: Extension loaded!');
console.log('💡 Helper functions available:');
console.log('   📞 kikoResetViewer() - Remove existing viewer windows');
console.log('   🚀 kikoForceViewer() - Show demo viewer');
console.log('   🧪 kikoSaveImageTest() - Test image click functionality');