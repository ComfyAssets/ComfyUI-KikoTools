import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyAssets.DisplayText",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DisplayText") {
            function populate(text) {
                // Remove existing widgets
                if (this.widgets) {
                    const toRemove = [];
                    for (let i = 0; i < this.widgets.length; i++) {
                        if (this.widgets[i].name?.startsWith("text_") || this.widgets[i].name?.startsWith("copy_")) {
                            this.widgets[i].onRemove?.();
                            toRemove.push(i);
                        }
                    }
                    // Remove in reverse order to maintain indices
                    for (let i = toRemove.length - 1; i >= 0; i--) {
                        this.widgets.splice(toRemove[i], 1);
                    }
                }

                // Parse the text to detect positive/negative prompt format
                const posMatch = text.match(/Positive prompt:\s*([\s\S]*?)(?=Negative prompt:|$)/i);
                const negMatch = text.match(/Negative prompt:\s*([\s\S]*?)(?=\*\*|$)/i);

                if (posMatch && negMatch) {
                    // Extract prompt content
                    let positiveText = posMatch[1].trim();
                    let negativeText = negMatch[1].trim();

                    // Remove any trailing ** markers
                    const posEndIndex = positiveText.indexOf('**');
                    if (posEndIndex > 0) {
                        positiveText = positiveText.substring(0, posEndIndex).trim();
                    }

                    const negEndIndex = negativeText.indexOf('**');
                    if (negEndIndex > 0) {
                        negativeText = negativeText.substring(0, negEndIndex).trim();
                    }

                    // Create header widget for positive prompt
                    const posHeader = ComfyWidgets["STRING"](this, "text_pos_header", ["STRING", { multiline: false }], app).widget;
                    posHeader.inputEl.readOnly = true;
                    posHeader.inputEl.style.opacity = 0.7;
                    posHeader.inputEl.style.backgroundColor = "#2a4a2a";
                    posHeader.inputEl.style.color = "#8f8";
                    posHeader.inputEl.style.fontWeight = "bold";
                    posHeader.value = "✓ Positive Prompt";

                    // Create positive prompt widget
                    const posWidget = ComfyWidgets["STRING"](this, "text_positive", ["STRING", { multiline: true }], app).widget;
                    posWidget.inputEl.readOnly = true;
                    posWidget.inputEl.style.opacity = 0.9;
                    posWidget.value = positiveText;

                    // Create copy button widget for positive prompt
                    const posCopyWidget = {
                        type: "button",
                        name: "copy_positive",
                        text: "📋 Copy Positive",
                        callback: () => {
                            navigator.clipboard.writeText(positiveText).then(() => {
                                posCopyWidget.text = "✓ Copied!";
                                this.setDirtyCanvas(true);
                                setTimeout(() => {
                                    posCopyWidget.text = "📋 Copy Positive";
                                    this.setDirtyCanvas(true);
                                }, 1500);
                            }).catch(err => {
                                console.error('Failed to copy:', err);
                            });
                        }
                    };
                    this.addCustomWidget(posCopyWidget);

                    // Create header widget for negative prompt
                    const negHeader = ComfyWidgets["STRING"](this, "text_neg_header", ["STRING", { multiline: false }], app).widget;
                    negHeader.inputEl.readOnly = true;
                    negHeader.inputEl.style.opacity = 0.7;
                    negHeader.inputEl.style.backgroundColor = "#4a2a2a";
                    negHeader.inputEl.style.color = "#f88";
                    negHeader.inputEl.style.fontWeight = "bold";
                    negHeader.value = "✗ Negative Prompt";

                    // Create negative prompt widget
                    const negWidget = ComfyWidgets["STRING"](this, "text_negative", ["STRING", { multiline: true }], app).widget;
                    negWidget.inputEl.readOnly = true;
                    negWidget.inputEl.style.opacity = 0.9;
                    negWidget.value = negativeText;

                    // Create copy button widget for negative prompt
                    const negCopyWidget = {
                        type: "button",
                        name: "copy_negative",
                        text: "📋 Copy Negative",
                        callback: () => {
                            navigator.clipboard.writeText(negativeText).then(() => {
                                negCopyWidget.text = "✓ Copied!";
                                this.setDirtyCanvas(true);
                                setTimeout(() => {
                                    negCopyWidget.text = "📋 Copy Negative";
                                    this.setDirtyCanvas(true);
                                }, 1500);
                            }).catch(err => {
                                console.error('Failed to copy:', err);
                            });
                        }
                    };
                    this.addCustomWidget(negCopyWidget);

                } else {
                    // Single text display with ComfyUI's standard STRING widget
                    const w = ComfyWidgets["STRING"](this, "text_display", ["STRING", { multiline: true }], app).widget;
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.9;
                    w.value = text;

                    // Create copy button widget
                    const copyWidget = {
                        type: "button",
                        name: "copy_text",
                        text: "📋 Copy",
                        callback: () => {
                            navigator.clipboard.writeText(text).then(() => {
                                copyWidget.text = "✓ Copied!";
                                this.setDirtyCanvas(true);
                                setTimeout(() => {
                                    copyWidget.text = "📋 Copy";
                                    this.setDirtyCanvas(true);
                                }, 1500);
                            }).catch(err => {
                                console.error('Failed to copy:', err);
                            });
                        }
                    };
                    this.addCustomWidget(copyWidget);
                }

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

            // When the node is executed we will be sent the input text
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);
                if (message?.text) {
                    populate.call(this, message.text[0]);
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

                // Set default size
                this.size[0] = Math.max(this.size[0], 400);
                this.size[1] = Math.max(this.size[1], 300);

                // Add placeholder text
                populate.call(this, "Text will appear here after execution...");
            };
        }
    }
});
