import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { createScope, mountTheme } from './ui/core.js';
import { createColorPicker } from './ui/color-picker.js';
import { WorkflowClock } from './ui/workflow-clock.js';

const clock = new WorkflowClock(app.ui.settings);
let colorPicker;

app.registerExtension({
    name: 'ComfyAssets.KikoWorkflowTimer',
    async init() {
        app.ui.settings.addSetting({
            id: 'kikotools.workflow_timer.color',
            name: '🫶 Workflow Timer: Color',
            type: (name, setter, value) => {
                if (!colorPicker || colorPicker.scope?.signal.aborted) {
                    colorPicker = createColorPicker(value, setter, app.ui.settings, 'Timer color');
                }
                colorPicker.onChange = setter;
                return colorPicker;
            },
            defaultValue: '#0877bb',
            tooltip: 'Color of the workflow timer display',
            onChange: () => clock.refresh(),
        });
        app.ui.settings.addSetting({
            id: 'kikotools.workflow_timer.glow',
            name: '🫶 Workflow Timer: Enable Glow',
            type: 'boolean',
            defaultValue: true,
            tooltip: 'Enable the pulsing glow unless reduced motion is preferred',
            onChange: () => clock.refresh(),
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== 'KikoWorkflowTimer') return;
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            this.timerScope = createScope();
            this.properties = this.properties || {};
            const container = document.createElement('div');
            container.className = 'ca-tools ca-workflow-timer kiko-timer-container';
            const header = document.createElement('header');
            header.className = 'ca-timer-header';
            const title = document.createElement('h3');
            title.textContent = 'Workflow Timer';
            const brand = document.createElement('span');
            brand.textContent = 'ComfyAssets';
            header.append(title, brand);
            this.timerDisplay = document.createElement('div');
            this.timerDisplay.className = 'kiko-timer-display';
            this.timerDisplay.setAttribute('role', 'timer');
            this.timerDisplay.setAttribute('aria-label', 'Elapsed workflow time');
            this.timerDisplay.setAttribute('aria-live', 'off');
            container.append(header, this.timerDisplay);
            mountTheme(container, app.ui.settings, this.timerScope);
            this.addDOMWidget('kikoTimer', 'Kiko Timer', container, {
                serialize: false, hideOnZoom: false, getMinHeight: () => 90,
            });
            this.setSize([340, 180]);
            clock.registerNode(this);
            this.timerScope.cleanup(() => {
                clock.unregisterNode(this);
                container.remove();
            });
            return result;
        };
        const onRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            this.timerScope.dispose();
            return onRemoved?.apply(this, arguments);
        };
        const onSerialize = nodeType.prototype.onSerialize;
        nodeType.prototype.onSerialize = function (data) {
            const result = onSerialize?.apply(this, arguments);
            data.properties = { ...data.properties, elapsed_time_str: this.properties.elapsed_time_str };
            return result;
        };
        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (data) {
            const result = onConfigure?.apply(this, arguments);
            this.properties = { ...(this.properties || {}), ...(data?.properties || {}) };
            if (this.timerDisplay) clock.renderNode(this);
            return result;
        };
    },

    setup() {
        api.addEventListener('execution_start', () => clock.start());
        api.addEventListener('executing', ({ detail }) => { if (detail === null) clock.stop(); });
        for (const event of ['execution_error', 'execution_interrupted']) api.addEventListener(event, () => clock.stop());
    },
});
