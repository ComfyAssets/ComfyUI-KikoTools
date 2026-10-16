import { normalizeHex } from './color.js';

export function formatElapsed(ms) {
    ms = Number.isFinite(ms) ? Math.max(0, Math.floor(ms)) : 0;
    return `${String(Math.floor(ms / 60000)).padStart(2, '0')}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}:${String(ms % 1000).padStart(3, '0')}`;
}

export class WorkflowClock {
    constructor(settings, environment = globalThis) {
        this.settings = settings;
        this.environment = environment;
        this.activeNodes = new Set();
        this.isRunning = false;
        this.startTime = 0;
        this.intervalId = null;
    }

    getTimerColor() {
        return normalizeHex(this.settings.getSettingValue('kikotools.workflow_timer.color')) || '#0877bb';
    }

    renderNode(node) {
        node.timerDisplay.textContent = this.isRunning
            ? formatElapsed(this.environment.Date.now() - this.startTime)
            : node.properties.elapsed_time_str || '00:00:000';
        node.timerDisplay.style.setProperty('--ca-timer-color', this.getTimerColor());
        node.timerDisplay.classList.toggle('running', this.isRunning);
        node.timerDisplay.classList.toggle('no-glow', this.settings.getSettingValue('kikotools.workflow_timer.glow') === false);
    }

    refresh() {
        this.activeNodes.forEach(node => this.renderNode(node));
    }

    ensureInterval() {
        if (!this.isRunning || !this.activeNodes.size || this.intervalId !== null) return;
        this.intervalId = this.environment.setInterval(() => {
            const elapsed = formatElapsed(this.environment.Date.now() - this.startTime);
            this.activeNodes.forEach(node => { node.timerDisplay.textContent = elapsed; });
        }, 33);
    }

    clearInterval() {
        this.environment.clearInterval(this.intervalId);
        this.intervalId = null;
    }

    start() {
        if (this.isRunning) return;
        this.isRunning = true;
        this.startTime = this.environment.Date.now();
        this.refresh();
        this.ensureInterval();
    }

    stop() {
        if (!this.isRunning) return;
        this.isRunning = false;
        this.clearInterval();
        const elapsed = formatElapsed(this.environment.Date.now() - this.startTime);
        this.activeNodes.forEach(node => { node.properties.elapsed_time_str = elapsed; });
        this.refresh();
    }

    registerNode(node) {
        this.activeNodes.add(node);
        this.refresh();
        this.ensureInterval();
    }

    unregisterNode(node) {
        this.activeNodes.delete(node);
        if (!this.activeNodes.size) this.clearInterval();
    }
}
