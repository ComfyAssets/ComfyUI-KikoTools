import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyAssets.DisplayText",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DisplayText") {
            function populate(text) {
                // Remove existing widgets
                if (this.widgets) {
                    const toRemove = [];
                    for (let i = 0; i < this.widgets.length; i++) {
                        if (this.widgets[i].name?.startsWith("text_")) {
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
                    
                    // Store reference for copy button
                    posWidget._copyText = positiveText;
                    posWidget._node = this;
                    
                    // Add copy button for positive prompt after DOM is ready
                    if (posWidget.inputEl && posWidget.inputEl.parentNode) {
                        requestAnimationFrame(() => {
                            if (posWidget.inputEl && posWidget.inputEl.parentNode) {
                                const posCopyBtn = document.createElement("button");
                                posCopyBtn.textContent = "📋 Copy Positive";
                                posCopyBtn.style.cssText = "margin: 5px; padding: 5px 10px; background: #4a4a4a; color: white; border: 1px solid #666; cursor: pointer; border-radius: 3px;";
                                posCopyBtn.onclick = () => {
                                    navigator.clipboard.writeText(posWidget._copyText).then(() => {
                                        posCopyBtn.textContent = "✓ Copied!";
                                        setTimeout(() => {
                                            posCopyBtn.textContent = "📋 Copy Positive";
                                        }, 1500);
                                    });
                                };
                                posWidget.inputEl.parentNode.appendChild(posCopyBtn);
                            }
                        });
                    }
                    
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
                    
                    // Store reference for copy button
                    negWidget._copyText = negativeText;
                    negWidget._node = this;
                    
                    // Add copy button for negative prompt after DOM is ready
                    if (negWidget.inputEl && negWidget.inputEl.parentNode) {
                        requestAnimationFrame(() => {
                            if (negWidget.inputEl && negWidget.inputEl.parentNode) {
                                const negCopyBtn = document.createElement("button");
                                negCopyBtn.textContent = "📋 Copy Negative";
                                negCopyBtn.style.cssText = "margin: 5px; padding: 5px 10px; background: #4a4a4a; color: white; border: 1px solid #666; cursor: pointer; border-radius: 3px;";
                                negCopyBtn.onclick = () => {
                                    navigator.clipboard.writeText(negWidget._copyText).then(() => {
                                        negCopyBtn.textContent = "✓ Copied!";
                                        setTimeout(() => {
                                            negCopyBtn.textContent = "📋 Copy Negative";
                                        }, 1500);
                                    });
                                };
                                negWidget.inputEl.parentNode.appendChild(negCopyBtn);
                            }
                        });
                    }
                    
                } else {
                    // Single text display with ComfyUI's standard STRING widget
                    const w = ComfyWidgets["STRING"](this, "text_display", ["STRING", { multiline: true }], app).widget;
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.9;
                    w.value = text;
                    
                    // Store reference for copy button
                    w._copyText = text;
                    w._node = this;
                    
                    // Add copy button after DOM is ready
                    if (w.inputEl && w.inputEl.parentNode) {
                        requestAnimationFrame(() => {
                            if (w.inputEl && w.inputEl.parentNode) {
                                const copyBtn = document.createElement("button");
                                copyBtn.textContent = "📋 Copy";
                                copyBtn.style.cssText = "margin: 5px; padding: 5px 10px; background: #4a4a4a; color: white; border: 1px solid #666; cursor: pointer; border-radius: 3px;";
                                copyBtn.onclick = () => {
                                    navigator.clipboard.writeText(w._copyText).then(() => {
                                        copyBtn.textContent = "✓ Copied!";
                                        setTimeout(() => {
                                            copyBtn.textContent = "📋 Copy";
                                        }, 1500);
                                    });
                                };
                                w.inputEl.parentNode.appendChild(copyBtn);
                            }
                        });
                    }
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