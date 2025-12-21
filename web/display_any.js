import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyAssets.DisplayAny",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DisplayAny") {
            function populate(text) {
                // Remove existing display widgets
                if (this.widgets) {
                    const toRemove = [];
                    for (let i = 0; i < this.widgets.length; i++) {
                        if (this.widgets[i].name?.startsWith("display_") || this.widgets[i].name === "copy_value") {
                            this.widgets[i].onRemove?.();
                            toRemove.push(i);
                        }
                    }
                    // Remove in reverse order to maintain indices
                    for (let i = toRemove.length - 1; i >= 0; i--) {
                        this.widgets.splice(toRemove[i], 1);
                    }
                }

                // Split text into multiple widgets if it's too long or has multiple lines
                const lines = text ? text.split('\n') : [''];
                const maxLinesPerWidget = 20;
                const chunks = [];

                for (let i = 0; i < lines.length; i += maxLinesPerWidget) {
                    chunks.push(lines.slice(i, i + maxLinesPerWidget).join('\n'));
                }

                // Create a widget for each chunk
                chunks.forEach((chunk, index) => {
                    const w = ComfyWidgets["STRING"](this, `display_${index}`, ["STRING", { multiline: true }], app).widget;
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.8;
                    w.inputEl.style.fontFamily = "monospace";
                    w.value = chunk;
                });

                // Add copy button widget
                const copyWidget = {
                    type: "button",
                    name: "copy_value",
                    text: "📋 Copy Value",
                    callback: () => {
                        navigator.clipboard.writeText(text || '').then(() => {
                            copyWidget.text = "✓ Copied!";
                            this.setDirtyCanvas(true);
                            setTimeout(() => {
                                copyWidget.text = "📋 Copy Value";
                                this.setDirtyCanvas(true);
                            }, 1500);
                        }).catch(err => {
                            console.error('Failed to copy:', err);
                        });
                    }
                };
                this.addCustomWidget(copyWidget);

                requestAnimationFrame(() => {
                    const sz = this.computeSize();
                    if (sz[0] < this.size[0]) {
                        sz[0] = this.size[0];
                    }
                    if (sz[1] < this.size[1]) {
                        sz[1] = this.size[1];
                    }
                    this.onResize?.(sz);
                    app.graph.setDirtyCanvas(true, false);
                });
            }

            // When the node is executed we will be sent the display text
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);

                console.log("DisplayAny onExecuted message:", message);

                if (message?.text && message.text.length > 0) {
                    const displayText = message.text[0];
                    console.log("DisplayAny displayText:", displayText);
                    populate.call(this, displayText);
                } else {
                    console.log("DisplayAny no text in message");
                }
            };

            const VALUES = Symbol();
            const configure = nodeType.prototype.configure;
            nodeType.prototype.configure = function () {
                this[VALUES] = arguments[0]?.widgets_values;
                return configure?.apply(this, arguments);
            };

            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function () {
                onConfigure?.apply(this, arguments);
                const widgets_values = this[VALUES];
                if (widgets_values?.length) {
                    requestAnimationFrame(() => {
                        const startIdx = widgets_values.length > 1 && this.inputs?.[0]?.widget ? 1 : 0;
                        if (widgets_values[startIdx]) {
                            populate.call(this, widgets_values[startIdx]);
                        }
                    });
                }
            };

            // Initialize on node creation
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                onNodeCreated?.apply(this, arguments);

                // Set minimum size - make it wider for better JSON display
                this.size[0] = Math.max(this.size[0], 450);
                this.size[1] = Math.max(this.size[1], 250);

                // Add placeholder text
                populate.call(this, "Value will appear here...");
            };
        }
    }
});
