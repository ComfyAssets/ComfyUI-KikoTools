import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Adds follow execution feature when enabled in settings
// Adds menu options to toggle follow execution and go to executing node

let followExecution = false;
let isEnabled = false;

const checkEnabled = () => {
    const setting = app.ui.settings.getSettingValue("kikotools.follow_execution.enabled");
    isEnabled = setting !== undefined ? setting : false;
    if (!isEnabled && followExecution) {
        followExecution = false;
    }
};

const checkAutoStart = () => {
    const autoStart = app.ui.settings.getSettingValue("kikotools.follow_execution.auto_start");
    if (autoStart && isEnabled) {
        followExecution = true;
    }
};

const centerNode = (id) => {
    checkEnabled();
    if (!followExecution || !id || !isEnabled) return;
    const node = app.graph.getNodeById(id);
    if (!node) return;
    app.canvas.centerOnNode(node);
};

const onExecuting = ({ detail }) => centerNode(detail);
const onExecutionStart = () => {
    checkEnabled();
    checkAutoStart();
};

app.registerExtension({
    name: "kikotools.followExecution",
    async init() {
        // Register settings in ComfyUI's settings panel
        app.ui.settings.addSetting({
            id: "kikotools.follow_execution.enabled",
            name: "🫶 Follow Execution: Enable",
            type: "boolean",
            defaultValue: false,
            tooltip: "Enable follow execution feature in canvas right-click menu",
            onChange: checkEnabled,
        });

        app.ui.settings.addSetting({
            id: "kikotools.follow_execution.show_goto_node",
            name: "🫶 Follow Execution: Show 'Go to node' menu",
            type: "boolean",
            defaultValue: true,
            tooltip: "Show 'Go to node' submenu in canvas menu",
        });

        app.ui.settings.addSetting({
            id: "kikotools.follow_execution.auto_start",
            name: "🫶 Follow Execution: Auto-start",
            type: "boolean",
            defaultValue: false,
            tooltip: "Automatically start following execution when workflow starts",
        });
    },

    async setup() {
        checkEnabled();
        checkAutoStart();

        // Listen for execution events
        api.addEventListener("executing", onExecuting);

        // Listen for execution start to handle auto-start
        api.addEventListener("execution_start", onExecutionStart);
    },

    // New API: return items to append to canvas right-click menu
    getCanvasMenuItems() {
        checkEnabled();
        if (!isEnabled) return [];

        const items = [
            null, // separator
            {
                content: followExecution ? "🫶 Stop following execution" : "🫶 Follow execution",
                callback: () => {
                    checkEnabled();
                    if (!isEnabled) return;
                    followExecution = !followExecution;
                    if (followExecution) {
                        centerNode(app.runningNodeId);
                    }
                },
            },
        ];

        // Add go to executing node option if a node is currently executing
        if (app.runningNodeId) {
            items.push({
                content: "🫶 Show executing node",
                callback: () => {
                    const node = app.graph.getNodeById(app.runningNodeId);
                    if (node) app.canvas.centerOnNode(node);
                },
            });
        }

        // Add go to node by type submenu
        const showGoToNode = app.ui.settings.getSettingValue("kikotools.follow_execution.show_goto_node");
        if (showGoToNode !== false) {
            const nodes = app.graph._nodes;
            const types = nodes.reduce((p, n) => {
                if (n.type in p) {
                    p[n.type].push(n);
                } else {
                    p[n.type] = [n];
                }
                return p;
            }, Object.create(null));

            items.push({
                content: "🫶 Go to node",
                submenu: {
                    options: Object.keys(types)
                        .sort()
                        .map((t) => ({
                            content: t,
                            submenu: {
                                options: types[t]
                                    .sort((a, b) => a.pos[0] - b.pos[0])
                                    .map((n) => ({
                                        content: `${n.getTitle()} - #${n.id} (${Math.round(n.pos[0])}, ${Math.round(n.pos[1])})`,
                                        callback: () => {
                                            app.canvas.centerOnNode(n);
                                        },
                                    })),
                            },
                        })),
                },
            });
        }

        return items;
    },
});
