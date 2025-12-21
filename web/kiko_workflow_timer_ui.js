import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { $el } from "../../scripts/ui.js";

/**
 * Sketch-style Color Picker for Settings
 */
class SketchColorPicker {
    constructor(initialColor = '#ff9966', onChange = () => {}) {
        this.color = this.hexToHsv(initialColor);
        this.hex = initialColor;
        this.onChange = onChange;
        this.isOpen = false;

        this.presetColors = [
            '#D0021B', '#F5A623', '#F8E71C', '#8B572A', '#7ED321',
            '#417505', '#BD10E0', '#9013FE', '#4A90D9', '#50E3C2',
            '#B8E986', '#000000', '#4A4A4A', '#9B9B9B', '#FFFFFF',
        ];

        this.createElements();
    }

    createElements() {
        // Swatch button
        this.swatch = document.createElement('div');
        this.swatch.style.cssText = `
            width: 50px; height: 28px; border-radius: 4px;
            background: ${this.hex}; cursor: pointer;
            box-shadow: 0 0 0 1px rgba(0,0,0,.2), inset 0 0 0 1px rgba(0,0,0,.1);
            display: inline-block;
        `;
        this.swatch.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        // Popup container
        this.popup = document.createElement('div');
        this.popup.style.cssText = `
            position: absolute; z-index: 10000;
            background: #2a2a2a; border-radius: 6px;
            box-shadow: 0 0 0 1px rgba(255,255,255,.1), 0 8px 24px rgba(0,0,0,.4);
            padding: 12px; display: none; width: 220px;
            bottom: 100%; margin-bottom: 8px; right: 0;
        `;

        // Saturation/Brightness picker
        this.satBright = document.createElement('div');
        this.satBright.style.cssText = `
            width: 196px; height: 140px; position: relative;
            border-radius: 4px; cursor: crosshair; margin-bottom: 12px;
        `;
        this.updateSatBrightBackground();

        this.satBrightPointer = document.createElement('div');
        this.satBrightPointer.style.cssText = `
            width: 14px; height: 14px; border-radius: 50%;
            border: 2px solid #fff; box-shadow: 0 0 0 1px rgba(0,0,0,.3), 0 2px 4px rgba(0,0,0,.3);
            position: absolute; transform: translate(-50%, -50%);
            pointer-events: none;
        `;
        this.satBright.appendChild(this.satBrightPointer);

        // Hue slider
        this.hueSlider = document.createElement('div');
        this.hueSlider.style.cssText = `
            width: 196px; height: 14px; border-radius: 4px;
            background: linear-gradient(to right, #f00 0%, #ff0 17%, #0f0 33%, #0ff 50%, #00f 67%, #f0f 83%, #f00 100%);
            position: relative; cursor: pointer; margin-bottom: 12px;
        `;
        this.huePointer = document.createElement('div');
        this.huePointer.style.cssText = `
            width: 8px; height: 18px; border-radius: 3px;
            background: #fff; border: 1px solid rgba(0,0,0,.3);
            position: absolute; top: -2px; transform: translateX(-50%);
            pointer-events: none; box-shadow: 0 1px 3px rgba(0,0,0,.3);
        `;
        this.hueSlider.appendChild(this.huePointer);

        // Hex input row
        this.hexRow = document.createElement('div');
        this.hexRow.style.cssText = 'display: flex; align-items: center; margin-bottom: 12px; gap: 8px;';

        this.hexInput = document.createElement('input');
        this.hexInput.type = 'text';
        this.hexInput.value = this.hex;
        this.hexInput.style.cssText = `
            flex: 1; padding: 6px 8px; border: 1px solid #444;
            border-radius: 4px; font-size: 13px; font-family: monospace;
            text-transform: uppercase; background: #1a1a1a; color: #eee;
        `;
        this.hexInput.addEventListener('change', () => this.setHex(this.hexInput.value));

        const hexLabel = document.createElement('span');
        hexLabel.textContent = 'Hex';
        hexLabel.style.cssText = 'font-size: 12px; color: #888; min-width: 28px;';

        this.hexRow.appendChild(this.hexInput);
        this.hexRow.appendChild(hexLabel);

        // Preset swatches
        this.presetsContainer = document.createElement('div');
        this.presetsContainer.style.cssText = `
            display: flex; flex-wrap: wrap; gap: 6px;
            border-top: 1px solid #444; padding-top: 12px;
        `;

        this.presetColors.forEach(color => {
            const preset = document.createElement('div');
            preset.style.cssText = `
                width: 18px; height: 18px; border-radius: 3px;
                background: ${color}; cursor: pointer;
                box-shadow: inset 0 0 0 1px rgba(0,0,0,.2);
                transition: transform 0.1s;
            `;
            preset.addEventListener('mouseenter', () => preset.style.transform = 'scale(1.15)');
            preset.addEventListener('mouseleave', () => preset.style.transform = 'scale(1)');
            preset.addEventListener('click', () => this.setHex(color));
            this.presetsContainer.appendChild(preset);
        });

        // Assemble popup
        this.popup.appendChild(this.satBright);
        this.popup.appendChild(this.hueSlider);
        this.popup.appendChild(this.hexRow);
        this.popup.appendChild(this.presetsContainer);

        // Event handlers
        this.setupDrag(this.satBright, this.handleSatBrightChange.bind(this));
        this.setupDrag(this.hueSlider, this.handleHueChange.bind(this));

        // Close on outside click
        this.closeHandler = (e) => {
            if (!this.popup.contains(e.target) && e.target !== this.swatch) {
                this.close();
            }
        };
    }

    setupDrag(element, handler) {
        const onMove = (e) => {
            e.preventDefault();
            const rect = element.getBoundingClientRect();
            const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
            const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
            handler(x, y);
        };

        const onUp = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
        };

        // Click and drag behavior
        element.addEventListener('mousedown', (e) => {
            e.preventDefault();
            onMove(e);
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
        });

        // Hover preview - color follows mouse pointer
        element.addEventListener('mousemove', (e) => {
            if (e.buttons === 0) { // Only on hover, not during drag
                const rect = element.getBoundingClientRect();
                const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
                handler(x, y);
            }
        });
    }

    handleSatBrightChange(x, y) {
        this.color.s = x * 100;
        this.color.v = (1 - y) * 100;
        this.updateFromHsv();
    }

    handleHueChange(x) {
        this.color.h = x * 360;
        this.updateFromHsv();
    }

    updateFromHsv() {
        this.hex = this.hsvToHex(this.color.h, this.color.s, this.color.v);
        this.updateUI();
        this.onChange(this.hex);
    }

    updateUI() {
        this.swatch.style.background = this.hex;
        this.updateSatBrightBackground();
        this.satBrightPointer.style.left = `${this.color.s}%`;
        this.satBrightPointer.style.top = `${100 - this.color.v}%`;
        this.huePointer.style.left = `${(this.color.h / 360) * 100}%`;
        this.hexInput.value = this.hex.toUpperCase();
    }

    updateSatBrightBackground() {
        const hueColor = this.hsvToHex(this.color.h, 100, 100);
        this.satBright.style.background = `
            linear-gradient(to top, #000, transparent),
            linear-gradient(to right, #fff, ${hueColor})
        `;
    }

    setHex(hex) {
        if (!/^#?[0-9A-Fa-f]{6}$/.test(hex)) return;
        if (!hex.startsWith('#')) hex = '#' + hex;
        this.hex = hex;
        this.color = this.hexToHsv(hex);
        this.updateUI();
        this.onChange(this.hex);
    }

    toggle() { this.isOpen ? this.close() : this.open(); }

    open() {
        this.isOpen = true;
        this.popup.style.display = 'block';
        this.updateUI();
        setTimeout(() => document.addEventListener('click', this.closeHandler), 0);
    }

    close() {
        this.isOpen = false;
        this.popup.style.display = 'none';
        document.removeEventListener('click', this.closeHandler);
    }

    getElement() {
        const container = document.createElement('div');
        container.style.cssText = 'position: relative; display: inline-block;';
        container.appendChild(this.swatch);
        container.appendChild(this.popup);
        return container;
    }

    hexToHsv(hex) {
        const r = parseInt(hex.slice(1, 3), 16) / 255;
        const g = parseInt(hex.slice(3, 5), 16) / 255;
        const b = parseInt(hex.slice(5, 7), 16) / 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        const v = max * 100, d = max - min;
        const s = max === 0 ? 0 : (d / max) * 100;
        let h = 0;
        if (d !== 0) {
            switch (max) {
                case r: h = ((g - b) / d + (g < b ? 6 : 0)) * 60; break;
                case g: h = ((b - r) / d + 2) * 60; break;
                case b: h = ((r - g) / d + 4) * 60; break;
            }
        }
        return { h, s, v };
    }

    hsvToHex(h, s, v) {
        s /= 100; v /= 100;
        const c = v * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = v - c;
        let r = 0, g = 0, b = 0;
        if (h < 60) { r = c; g = x; }
        else if (h < 120) { r = x; g = c; }
        else if (h < 180) { g = c; b = x; }
        else if (h < 240) { g = x; b = c; }
        else if (h < 300) { r = x; b = c; }
        else { r = c; b = x; }
        const toHex = (n) => Math.round((n + m) * 255).toString(16).padStart(2, '0');
        return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    }
}

/**
 * Global Timer Manager
 */
const KikoGlobalTimer = {
    startTime: 0,
    intervalId: null,
    isRunning: false,
    activeNodes: new Set(),

    formatTime(ms) {
        if (ms < 0) ms = 0;
        const minutes = String(Math.floor(ms / 60000)).padStart(2, '0');
        const seconds = String(Math.floor((ms % 60000) / 1000)).padStart(2, '0');
        const milliseconds = String(ms % 1000).padStart(3, '0');
        return `${minutes}:${seconds}:${milliseconds}`;
    },

    getTimerColor() {
        return app.ui.settings.getSettingValue("kikotools.workflow_timer.color") || '#ff9966';
    },

    isGlowEnabled() {
        const val = app.ui.settings.getSettingValue("kikotools.workflow_timer.glow");
        return val !== undefined ? val : true;
    },

    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.startTime = Date.now();

        const timerColor = this.getTimerColor();
        this.activeNodes.forEach(node => {
            if (node.timerDisplay) {
                node.timerDisplay.style.color = timerColor;
                node.timerDisplay.classList.add('running');
            }
        });

        this.intervalId = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const timeString = this.formatTime(elapsed);
            this.activeNodes.forEach(node => {
                if (node.timerDisplay) {
                    node.timerDisplay.textContent = timeString;
                }
            });
        }, 33);
    },

    stop() {
        if (!this.isRunning) return;
        this.isRunning = false;
        clearInterval(this.intervalId);

        const finalTime = Date.now() - this.startTime;
        const finalTimeString = this.formatTime(finalTime);
        const timerColor = this.getTimerColor();

        this.activeNodes.forEach(node => {
            if (node.timerDisplay) {
                node.timerDisplay.textContent = finalTimeString;
                node.timerDisplay.style.color = timerColor;
                node.timerDisplay.classList.remove('running');
            }
            node.properties.elapsed_time_str = finalTimeString;
        });
    },

    updateColor(color) {
        if (this.isRunning) return;
        this.activeNodes.forEach(node => {
            if (node.timerDisplay) {
                node.timerDisplay.style.color = color;
            }
        });
    },

    updateGlow(enabled) {
        this.activeNodes.forEach(node => {
            if (node.timerDisplay) {
                node.timerDisplay.classList.toggle('no-glow', !enabled);
            }
        });
    },

    registerNode(node) { this.activeNodes.add(node); },
    unregisterNode(node) { this.activeNodes.delete(node); },
};

/**
 * ComfyUI Extension for KikoWorkflow Timer
 */
const KikoWorkflowTimerExtension = {
    name: "ComfyAssets.KikoWorkflowTimer",

    async init() {
        // Color picker setting with custom render
        app.ui.settings.addSetting({
            id: "kikotools.workflow_timer.color",
            name: "🫶 Workflow Timer: Color",
            type: (name, setter, value) => {
                const container = $el("div", {
                    style: { display: "flex", alignItems: "center", gap: "10px" }
                });

                const picker = new SketchColorPicker(value || '#ff9966', (newColor) => {
                    setter(newColor);
                    KikoGlobalTimer.updateColor(newColor);
                });

                container.appendChild(picker.getElement());

                // Also show hex value as text
                const hexDisplay = $el("span", {
                    textContent: value || '#ff9966',
                    style: { color: "#888", fontFamily: "monospace", fontSize: "12px" }
                });
                container.appendChild(hexDisplay);

                // Update hex display when color changes
                const origOnChange = picker.onChange;
                picker.onChange = (newColor) => {
                    origOnChange(newColor);
                    hexDisplay.textContent = newColor.toUpperCase();
                };

                return container;
            },
            defaultValue: "#ff9966",
            tooltip: "Color of the timer display when not running",
        });

        // Glow toggle
        app.ui.settings.addSetting({
            id: "kikotools.workflow_timer.glow",
            name: "🫶 Workflow Timer: Enable Glow",
            type: "boolean",
            defaultValue: true,
            tooltip: "Enable pulsing glow effect on the timer",
            onChange: (value) => {
                KikoGlobalTimer.updateGlow(value);
            },
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "KikoWorkflowTimer") {
            const origOnNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                origOnNodeCreated?.apply(this, arguments);

                this.bgcolor = "#1a1a2e";
                this.color = "#16213e";
                this.title = "Workflow Timer";
                this.properties = this.properties || {};
                this.size = [300, 100];

                const container = document.createElement("div");
                container.className = "kiko-timer-container";

                this.timerDisplay = document.createElement("div");
                this.timerDisplay.className = "kiko-timer-display";
                this.timerDisplay.textContent = this.properties.elapsed_time_str || "00:00:000";

                const timerColor = KikoGlobalTimer.getTimerColor();
                this.timerDisplay.style.color = timerColor;

                if (!KikoGlobalTimer.isGlowEnabled()) {
                    this.timerDisplay.classList.add('no-glow');
                }

                container.appendChild(this.timerDisplay);
                this.addDOMWidget("kikoTimer", "Kiko Timer", container, { serialize: false });

                KikoGlobalTimer.registerNode(this);
            };

            nodeType.prototype.onRemoved = function() {
                KikoGlobalTimer.unregisterNode(this);
            };

            const origOnSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(o) {
                origOnSerialize?.apply(this, arguments);
                o.properties = this.properties;
            };

            const origOnConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function(info) {
                origOnConfigure?.apply(this, arguments);
                this.properties = info.properties || {};

                if (this.timerDisplay) {
                    this.timerDisplay.textContent = this.properties.elapsed_time_str || "00:00:000";
                    const timerColor = KikoGlobalTimer.getTimerColor();
                    this.timerDisplay.style.color = timerColor;

                    if (!KikoGlobalTimer.isGlowEnabled()) {
                        this.timerDisplay.classList.add('no-glow');
                    }
                }
            };
        }
    },

    setup() {
        const style = document.createElement("style");
        style.textContent = `
            @keyframes kiko-timer-pulse {
                0%, 100% { text-shadow: 0 0 15px currentColor; opacity: 0.9; }
                50% { text-shadow: 0 0 25px currentColor; opacity: 1; }
            }

            @keyframes kiko-timer-running-pulse {
                0%, 100% { text-shadow: 0 0 15px currentColor; opacity: 0.9; }
                50% { text-shadow: 0 0 25px currentColor; opacity: 1; }
            }

            .kiko-timer-container {
                width: 100%; height: 100%;
                position: relative; display: flex;
                align-items: center; justify-content: center;
            }

            .kiko-timer-display {
                text-align: center; width: 100%; height: 100%;
                position: absolute; top: 0; left: 0;
                background: transparent; border: none;
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
                box-sizing: border-box; outline: none; margin: 0;
                overflow: hidden; display: flex;
                justify-content: center; align-items: center;
                font-size: 42px;
                animation: kiko-timer-pulse 4s infinite ease-in-out;
                transition: color 0.3s ease-in-out;
                font-variant-numeric: tabular-nums;
                letter-spacing: 0.08em;
                white-space: nowrap; font-weight: 600;
            }

            .kiko-timer-display.no-glow {
                animation: none;
                text-shadow: none;
            }

            .kiko-timer-display.running {
                animation: kiko-timer-running-pulse 2s infinite ease-in-out;
            }

            .kiko-timer-display.running.no-glow {
                animation: none;
                text-shadow: none;
            }
        `;
        document.head.appendChild(style);

        api.addEventListener("execution_start", () => KikoGlobalTimer.start());
        api.addEventListener("executing", ({ detail }) => {
            if (detail === null) KikoGlobalTimer.stop();
        });
        api.addEventListener("execution_error", () => KikoGlobalTimer.stop());
        api.addEventListener("execution_interrupted", () => KikoGlobalTimer.stop());
    }
};

app.registerExtension(KikoWorkflowTimerExtension);
