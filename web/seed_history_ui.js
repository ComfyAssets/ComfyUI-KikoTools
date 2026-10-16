import { app } from '../../scripts/app.js';
import { createScope, mountTheme } from './ui/core.js';
import { createSeedHistoryView } from './views/seed-history.js';

const storageKey = 'comfyui_kikotools_seed_history';

function seedValue(value) {
    if (typeof value !== 'number' && (typeof value !== 'string' || !value.trim())) return null;
    const seed = Number(value);
    return Number.isInteger(seed) && seed >= 0 && seed <= 0xFFFFFFFF ? seed : null;
}

function historyValue(value) {
    if (!Array.isArray(value)) return [];
    const seeds = new Set();
    return value.flatMap(item => {
        const seed = seedValue(item?.seed);
        if (seed === null || seeds.has(seed)) return [];
        seeds.add(seed);
        return [{ ...item, seed, timestamp: Number.isFinite(item.timestamp) ? item.timestamp : Date.now() }];
    }).slice(0, 10);
}

app.registerExtension({
    name: 'comfyassets.SeedHistory',
    async setup() {
        window.seedHistoryNodes = window.seedHistoryNodes || [];
    },
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== 'SeedHistory') return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            this.seedScope = createScope();
            this.seedHistory = this.loadSeedHistory();
            this.hideTimer = null;
            this.seedSetupTimer = null;
            this.seedValueWatcher = null;
            this.mouseOverHistory = false;
            window.seedHistoryNodes = window.seedHistoryNodes || [];
            window.seedHistoryNodes.push(this);
            this.buildSeedInterface();
            this.seedWidget = this.addDOMWidget('seed_history_ui', 'div', this.seedView.element, {
                serialize: false, hideOnZoom: false,
                getMinHeight: () => 200,
            });
            if (!this.hasBeenResized) this.setSize([320, 420]);
            const originalResize = this.onResize;
            this.onResize = function () {
                this.hasBeenResized = true;
                return originalResize?.apply(this, arguments);
            };
            this.seedSetupTimer = setTimeout(() => {
                this.seedSetupTimer = null;
                this.setupSeedWidgetCallbacks();
            }, 100);
            const originalOnWidgetChange = this.onWidgetChange;
            this.onWidgetChange = function (name, value, oldValue) {
                if (name === 'seed' && value !== oldValue) this.addSeedToHistory(value);
                return originalOnWidgetChange?.apply(this, arguments);
            };
            const originalSerialize = this.serialize;
            this.serialize = function () {
                const data = originalSerialize?.apply(this, arguments) || {};
                data.hasBeenResized = this.hasBeenResized;
                data.seedHistory = this.seedHistory;
                return data;
            };
            const originalConfigure = this.configure;
            this.configure = function (data) {
                const result = originalConfigure?.apply(this, arguments);
                if (data.hasBeenResized !== undefined) this.hasBeenResized = data.hasBeenResized;
                if (data.seedHistory !== undefined) {
                    this.seedHistory = historyValue(data.seedHistory);
                    this.refreshHistoryDisplay();
                }
                return result;
            };
            this.seedScope.cleanup(() => {
                clearTimeout(this.seedSetupTimer);
                clearInterval(this.seedValueWatcher);
                this.seedSetupTimer = null;
                this.seedValueWatcher = null;
                this.cancelAutoHide();
                this.lastAddedSeed = null;
                window.seedHistoryNodes = window.seedHistoryNodes.filter(node => node !== this);
                this.seedView.element.remove();
            });
            const originalOnRemoved = this.onRemoved;
            this.onRemoved = function () {
                this.seedScope.dispose();
                return originalOnRemoved?.apply(this, arguments);
            };
            this.setDirtyCanvas(true, true);
            return result;
        };

        nodeType.prototype.setupSeedWidgetCallbacks = function () {
            if (this.seedScope.signal.aborted || this.seedValueWatcher !== null) return;
            const seedWidget = this.widgets?.find(widget => widget.name === 'seed');
            if (!seedWidget) {
                this.seedSetupTimer = setTimeout(() => {
                    this.seedSetupTimer = null;
                    this.setupSeedWidgetCallbacks();
                }, 500);
                return;
            }
            this.lastSeedValue = seedWidget.value;
            this.seedValueWatcher = setInterval(() => {
                if (seedWidget.value !== this.lastSeedValue) {
                    this.lastSeedValue = seedWidget.value;
                    this.addSeedToHistory(seedWidget.value);
                }
            }, 1000);
        };

        nodeType.prototype.buildSeedInterface = function () {
            this.seedView = createSeedHistoryView(this.seedScope, {
                generate: () => this.generateRandomSeed(),
                clear: () => this.clearSeedHistory(),
                select: index => this.useSeedFromHistory(this.seedHistory[index], index),
                expand: expanded => expanded ? this.showHistorySection() : this.hideHistorySection(true),
            });
            const { element, list, disclosure } = this.seedView;
            this.historyDisplay = list;
            this.restoreButton = disclosure;
            mountTheme(element, app.ui.settings, this.seedScope);
            this.seedScope.listen(list, 'mouseenter', () => {
                this.mouseOverHistory = true;
                this.cancelAutoHide();
            });
            this.seedScope.listen(list, 'mouseleave', () => {
                this.mouseOverHistory = false;
                this.startAutoHide();
            });
            this.seedScope.listen(list, 'focusin', () => this.cancelAutoHide());
            this.seedScope.listen(list, 'focusout', () => this.startAutoHide());
            this.refreshHistoryDisplay();
        };

        nodeType.prototype.loadSeedHistory = function () {
            try { return historyValue(JSON.parse(localStorage.getItem(storageKey))); }
            catch { return []; }
        };
        nodeType.prototype.saveSeedHistory = function () {
            try { localStorage.setItem(storageKey, JSON.stringify(this.seedHistory)); }
            catch { /* History remains available in the workflow if browser storage is unavailable. */ }
        };
        nodeType.prototype.addSeedToHistory = function (value) {
            const seed = seedValue(value);
            if (seed === null || this.seedScope.signal.aborted) return;
            const now = Date.now();
            if (this.lastAddedSeed?.seed === seed && now - this.lastAddedSeed.timestamp < 500) return;
            this.lastAddedSeed = { seed, timestamp: now };
            this.seedHistory = [{ seed, timestamp: now, dateString: new Date(now).toLocaleString() },
                ...this.seedHistory.filter(item => item.seed !== seed)].slice(0, 10);
            this.saveSeedHistory();
            this.refreshHistoryDisplay();
        };
        nodeType.prototype.generateRandomSeed = function () {
            const seed = Math.floor(Math.random() * 0xFFFFFFFF);
            const widget = this.widgets?.find(widget => widget.name === 'seed');
            if (widget) {
                widget.value = seed;
                widget.callback?.(seed, app.canvas, this, [0, 0], null);
                this.lastSeedValue = widget.value;
            }
            this.addSeedToHistory(seed);
            this.setDirtyCanvas(true, true);
            this.showMessage(`Generated: ${seed}`, 'success');
        };
        nodeType.prototype.useSeedFromHistory = function (item, index) {
            const widget = this.widgets?.find(widget => widget.name === 'seed');
            if (widget) {
                widget.value = item.seed;
                widget.callback?.(item.seed, app.canvas, this, [0, 0], null);
                this.lastSeedValue = widget.value;
            }
            this.highlightHistoryEntry(index);
            this.setDirtyCanvas(true, true);
            this.startAutoHide();
            this.showMessage(`Loaded: ${item.seed}`);
        };
        nodeType.prototype.clearSeedHistory = function () {
            this.seedHistory = [];
            this.lastAddedSeed = null;
            this.lastSeedValue = this.widgets?.find(widget => widget.name === 'seed')?.value;
            this.saveSeedHistory();
            this.showHistorySection();
            this.refreshHistoryDisplay();
            this.showMessage('History cleared');
        };
        nodeType.prototype.refreshHistoryDisplay = function () {
            if (!this.seedView) return;
            const selected = seedValue(this.widgets?.find(widget => widget.name === 'seed')?.value);
            this.seedView.render(this.seedHistory, selected, timestamp => this.formatTimeAgo(timestamp));
            this.startAutoHide();
        };
        nodeType.prototype.highlightHistoryEntry = function (index) {
            this.historyDisplay.querySelectorAll('button[data-seed-index]').forEach((entry, i) => {
                entry.setAttribute('aria-pressed', String(i === index));
            });
        };
        nodeType.prototype.startAutoHide = function () {
            this.cancelAutoHide();
            if (!this.seedScope.signal.aborted && !this.mouseOverHistory && this.seedHistory.length && !this.historyDisplay.hidden) {
                this.hideTimer = setTimeout(() => {
                    this.hideTimer = null;
                    this.hideHistorySection();
                }, 2500);
            }
        };
        nodeType.prototype.cancelAutoHide = function () {
            clearTimeout(this.hideTimer);
            this.hideTimer = null;
        };
        nodeType.prototype.hideHistorySection = function (explicit = false) {
            if (this.seedScope.signal.aborted || (!explicit && (this.mouseOverHistory || this.historyDisplay.contains(document.activeElement)))) return;
            this.cancelAutoHide();
            this.seedView.expand(false);
        };
        nodeType.prototype.showHistorySection = function () {
            this.seedView.expand(true);
            this.startAutoHide();
        };
        nodeType.prototype.formatTimeAgo = function (timestamp) {
            const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
            if (seconds >= 86400) return `${Math.floor(seconds / 86400)}d ago`;
            if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ago`;
            if (seconds >= 60) return `${Math.floor(seconds / 60)}m ago`;
            return `${seconds}s ago`;
        };
        nodeType.prototype.showMessage = function (message, type = 'info') {
            this.seedView.status.textContent = message;
            this.seedView.status.dataset.kind = type;
        };
    },
});
