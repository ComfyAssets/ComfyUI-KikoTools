import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Adds follow execution feature when enabled in settings
// Adds menu options to toggle follow execution and go to executing node

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
        let followExecution = false;
        let isEnabled = false;

        // Check if the feature is enabled in settings
        const checkEnabled = () => {
            const setting = app.ui.settings.getSettingValue("kikotools.follow_execution.enabled");
            isEnabled = setting !== undefined ? setting : false;

            // If disabled, turn off follow execution
            if (!isEnabled && followExecution) {
                followExecution = false;
            }
        };

        // Check for auto-start setting
        const checkAutoStart = () => {
            const autoStart = app.ui.settings.getSettingValue("kikotools.follow_execution.auto_start");
            if (autoStart && isEnabled) {
                followExecution = true;
            }
        };

        // Initialize settings on startup
        checkEnabled();
        checkAutoStart();

        // Center on the executing node
        const centerNode = (id) => {
            if (!followExecution || !id || !isEnabled) return;
            const node = app.graph.getNodeById(id);
            if (!node) return;
            app.canvas.centerOnNode(node);
        };

        // Listen for execution events
        api.addEventListener("executing", ({ detail }) => centerNode(detail));

        // Listen for execution start to handle auto-start
        api.addEventListener("execution_start", () => {
            checkEnabled();
            checkAutoStart();
        });

        // Extend canvas menu options
        const orig = LGraphCanvas.prototype.getCanvasMenuOptions;
        LGraphCanvas.prototype.getCanvasMenuOptions = function () {
            const options = orig.apply(this, arguments);

            // Check if feature is enabled before adding menu items
            checkEnabled();
            if (!isEnabled) return options;

            // Add separator
            options.push(null);

            // Add follow execution toggle
            options.push({
                content: followExecution ? "🫶 Stop following execution" : "🫶 Follow execution",
                callback: () => {
                    followExecution = !followExecution;
                    if (followExecution) {
                        centerNode(app.runningNodeId);
                    }
                },
            });

            // Add go to executing node option if a node is currently executing
            if (app.runningNodeId) {
                options.push({
                    content: "🫶 Show executing node",
                    callback: () => {
                        const node = app.graph.getNodeById(app.runningNodeId);
                        if (!node) return;
                        app.canvas.centerOnNode(node);
                    },
                });
            }

            // Add go to node by type submenu
            const showGoToNode = app.ui.settings.getSettingValue("kikotools.follow_execution.show_goto_node");
            if (showGoToNode !== false) {  // Default to true if not set
                const nodes = app.graph._nodes;
                const types = nodes.reduce((p, n) => {
                    if (n.type in p) {
                        p[n.type].push(n);
                    } else {
                        p[n.type] = [n];
                    }
                    return p;
                }, {});

                options.push({
                    content: "🫶 Go to node",
                    has_submenu: true,
                    submenu: {
                        options: Object.keys(types)
                            .sort()
                            .map((t) => ({
                                content: t,
                                has_submenu: true,
                                submenu: {
                                    options: types[t]
                                        .sort((a, b) => {
                                            return a.pos[0] - b.pos[0];
                                        })
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

            return options;
        };
    },
});
