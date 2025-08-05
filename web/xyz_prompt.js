import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyAssets.XYZPrompt",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "XYZPrompt") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            // Track prompt count for each node
            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);
                
                // Initialize prompt tracking
                this.promptCount = 0;
                this.promptWidgets = [];
                
                // Store reference to include_negative and repeat_negative widgets
                this.includeNegativeWidget = this.widgets.find(w => w.name === "include_negative");
                this.repeatNegativeWidget = this.widgets.find(w => w.name === "repeat_negative");
                
                // Add callback to include_negative widget
                if (this.includeNegativeWidget) {
                    const originalCallback = this.includeNegativeWidget.callback;
                    this.includeNegativeWidget.callback = (value) => {
                        if (originalCallback) originalCallback.call(this, value);
                        this.updatePromptWidgets();
                    };
                }
                
                // Add callback to repeat_negative widget
                if (this.repeatNegativeWidget) {
                    const originalCallback = this.repeatNegativeWidget.callback;
                    this.repeatNegativeWidget.callback = (value) => {
                        if (originalCallback) originalCallback.call(this, value);
                        this.updatePromptWidgets();
                    };
                }
                
                // Add the "Add Prompt" button
                this.addPromptButton = this.addWidget(
                    "button",
                    "➕ Add Prompt",
                    null,
                    () => {
                        this.addPromptSet();
                    }
                );
                
                // Add initial prompt set
                this.addPromptSet();
                
                // Update node title
                this.updateNodeTitle();
                
                // Initial sizing
                setTimeout(() => {
                    const size = this.computeSize();
                    this.size[1] = size[1] + 60;
                    this.setDirtyCanvas(true, true);
                }, 50);
                
                return result;
            };
            
            // Add method to add a new prompt set
            nodeType.prototype.addPromptSet = function() {
                const index = this.promptCount;
                const includeNegative = this.includeNegativeWidget?.value ?? true;
                const repeatNegative = this.repeatNegativeWidget?.value ?? true;
                
                // Determine if we should show negative prompt for this index
                const showNegative = includeNegative && (!repeatNegative || index === 0);
                
                // Create positive prompt widget
                const positiveWidgetObj = ComfyWidgets.STRING(
                    this, 
                    `positive_${index}`, 
                    ["STRING", {
                        default: "",
                        multiline: true,
                        dynamicPrompts: false
                    }], 
                    app
                );
                const positiveWidget = positiveWidgetObj.widget;
                
                // Debug log
                console.log(`Created positive_${index} widget:`, positiveWidget);
                
                // Style the positive prompt
                if (positiveWidget.inputEl) {
                    positiveWidget.inputEl.placeholder = `Positive Prompt ${index + 1}`;
                    positiveWidget.inputEl.style.minHeight = "70px";
                    positiveWidget.inputEl.style.fontFamily = "monospace";
                    positiveWidget.inputEl.style.backgroundColor = "#1a3d1a"; // Slight green tint
                    positiveWidget.inputEl.style.marginBottom = "5px"; // Add spacing below
                }
                
                // Add callback to update count
                const posOriginalCallback = positiveWidget.callback;
                positiveWidget.callback = (value) => {
                    if (posOriginalCallback) posOriginalCallback.call(this, value);
                    this.updateNodeTitle();
                };
                
                let negativeWidget = null;
                if (showNegative) {
                    // Create negative prompt widget only for first prompt or when not repeating
                    negativeWidget = ComfyWidgets.STRING(
                        this, 
                        `negative_${index}`, 
                        ["STRING", {
                            default: "",
                            multiline: true,
                            dynamicPrompts: false
                        }], 
                        app
                    ).widget;
                    
                    // Style the negative prompt
                    if (negativeWidget.inputEl) {
                        negativeWidget.inputEl.placeholder = `Negative Prompt ${index + 1}`;
                        negativeWidget.inputEl.style.minHeight = "70px";
                        negativeWidget.inputEl.style.fontFamily = "monospace";
                        negativeWidget.inputEl.style.backgroundColor = "#3d1a1a"; // Slight red tint
                    }
                    
                    // Add callback to update count
                    const negOriginalCallback = negativeWidget.callback;
                    negativeWidget.callback = (value) => {
                        if (negOriginalCallback) negOriginalCallback.call(this, value);
                        this.updateNodeTitle();
                    };
                }
                
                // Create a container widget for the remove button with protected space
                const buttonContainerWidget = {
                    type: "custom",
                    name: `button_container_${index}`,
                    size: [0, 40], // Fixed 40px height for button area
                    draw: function(ctx, node, width, y, H) {
                        // Draw a subtle separator line
                        ctx.strokeStyle = "#444";
                        ctx.beginPath();
                        ctx.moveTo(15, y + 5);
                        ctx.lineTo(width - 15, y + 5);
                        ctx.stroke();
                        
                        // Optional: Draw a semi-transparent background for the button area
                        ctx.fillStyle = "rgba(0, 0, 0, 0.2)";
                        ctx.fillRect(0, y + 10, width, 30);
                    },
                    computeSize: function() { 
                        return [0, 40]; // Fixed height to protect button space
                    }
                };
                this.widgets.push(buttonContainerWidget);
                
                // Add remove button for this prompt set
                const removeButton = this.addWidget(
                    "button",
                    `🗑️ Remove Prompt ${index + 1}`,
                    null,
                    () => {
                        this.removePromptSet(index);
                    }
                );
                
                // Store widgets for this prompt set
                this.promptWidgets.push({
                    index: index,
                    positive: positiveWidget,
                    negative: negativeWidget,
                    removeButton: removeButton,
                    buttonContainer: buttonContainerWidget
                });
                
                this.promptCount++;
                
                // Move the "Add Prompt" button to the bottom
                const buttonIndex = this.widgets.indexOf(this.addPromptButton);
                if (buttonIndex > -1) {
                    this.widgets.splice(buttonIndex, 1);
                    this.widgets.push(this.addPromptButton);
                }
                
                // Resize node - force proper recalculation
                this.setDirtyCanvas(true, true);
                setTimeout(() => {
                    const size = this.computeSize();
                    this.size[1] = Math.max(size[1] + 60, this.size[1]); // Ensure enough padding
                    this.setDirtyCanvas(true, true);
                }, 10);
                
                this.updateNodeTitle();
            };
            
            // Remove a prompt set
            nodeType.prototype.removePromptSet = function(index) {
                const promptSet = this.promptWidgets.find(p => p.index === index);
                if (!promptSet) return;
                
                // Remove widgets (including button container)
                const widgets = [promptSet.positive, promptSet.negative, promptSet.buttonContainer, promptSet.removeButton].filter(w => w);
                for (const widget of widgets) {
                    const widgetIndex = this.widgets.indexOf(widget);
                    if (widgetIndex > -1) {
                        // Clean up DOM element if it exists
                        if (widget.inputEl && widget.inputEl.parentNode) {
                            widget.inputEl.parentNode.removeChild(widget.inputEl);
                        }
                        // Call onRemoved if exists
                        if (widget.onRemoved) {
                            widget.onRemoved();
                        }
                        this.widgets.splice(widgetIndex, 1);
                    }
                }
                
                // Remove from tracking
                const setIndex = this.promptWidgets.indexOf(promptSet);
                if (setIndex > -1) {
                    this.promptWidgets.splice(setIndex, 1);
                }
                
                // Resize node
                this.setDirtyCanvas(true, true);
                const size = this.computeSize();
                this.size[1] = size[1];
                
                this.updateNodeTitle();
            };
            
            // Update prompt widgets when include_negative or repeat_negative changes
            nodeType.prototype.updatePromptWidgets = function() {
                const includeNegative = this.includeNegativeWidget?.value ?? true;
                const repeatNegative = this.repeatNegativeWidget?.value ?? true;
                
                for (const promptSet of this.promptWidgets) {
                    const index = promptSet.index;
                    const shouldHaveNegative = includeNegative && (!repeatNegative || index === 0);
                    
                    if (shouldHaveNegative && !promptSet.negative) {
                        // Add negative widget
                        const index = promptSet.index;
                        const negativeWidget = ComfyWidgets.STRING(
                            this, 
                            `negative_${index}`, 
                            ["STRING", {
                                default: "",
                                multiline: true,
                                dynamicPrompts: false
                            }], 
                            app
                        ).widget;
                        
                        if (negativeWidget.inputEl) {
                            negativeWidget.inputEl.placeholder = `Negative Prompt ${index + 1}`;
                            negativeWidget.inputEl.style.minHeight = "70px";
                            negativeWidget.inputEl.style.fontFamily = "monospace";
                            negativeWidget.inputEl.style.backgroundColor = "#3d1a1a";
                        }
                        
                        const negOriginalCallback = negativeWidget.callback;
                        negativeWidget.callback = (value) => {
                            if (negOriginalCallback) negOriginalCallback.call(this, value);
                            this.updateNodeTitle();
                        };
                        
                        promptSet.negative = negativeWidget;
                        
                        // Move it after the positive widget
                        const posIndex = this.widgets.indexOf(promptSet.positive);
                        if (posIndex > -1) {
                            const widgetIndex = this.widgets.indexOf(negativeWidget);
                            if (widgetIndex > -1) {
                                this.widgets.splice(widgetIndex, 1);
                                this.widgets.splice(posIndex + 1, 0, negativeWidget);
                            }
                        }
                    } else if (!shouldHaveNegative && promptSet.negative) {
                        // Remove negative widget
                        const widget = promptSet.negative;
                        const widgetIndex = this.widgets.indexOf(widget);
                        if (widgetIndex > -1) {
                            if (widget.inputEl && widget.inputEl.parentNode) {
                                widget.inputEl.parentNode.removeChild(widget.inputEl);
                            }
                            if (widget.onRemoved) {
                                widget.onRemoved();
                            }
                            this.widgets.splice(widgetIndex, 1);
                        }
                        promptSet.negative = null;
                    }
                }
                
                // Resize node - force proper recalculation
                this.setDirtyCanvas(true, true);
                setTimeout(() => {
                    const size = this.computeSize();
                    this.size[1] = Math.max(size[1] + 60, this.size[1]); // Ensure enough padding
                    this.setDirtyCanvas(true, true);
                }, 10);
            };
            
            // Update node title with prompt count
            nodeType.prototype.updateNodeTitle = function() {
                // Count non-empty prompts
                let count = 0;
                for (const promptSet of this.promptWidgets) {
                    if (promptSet.positive && promptSet.positive.value && promptSet.positive.value.trim()) {
                        count++;
                    }
                }
                
                this.title = `XYZ Prompt (${count} prompts)`;
            };
            
            // Override serialize to save prompt data
            const onSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(info) {
                if (onSerialize) onSerialize.call(this, info);
                
                // Debug: Log widget values during serialization
                console.log("XYZ Prompt serialize - widgets:", this.widgets.map(w => ({
                    name: w.name,
                    value: w.value,
                    type: w.type
                })));
                
                // Save prompt widget data
                info.promptData = {
                    count: this.promptCount,
                    widgets: this.promptWidgets.map(p => ({
                        index: p.index,
                        hasNegative: !!p.negative
                    }))
                };
            };
            
            // Override configure to restore prompt data
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function(info) {
                // Clear existing dynamic widgets first
                if (this.promptWidgets) {
                    for (const promptSet of this.promptWidgets) {
                        const widgets = [promptSet.positive, promptSet.negative, promptSet.removeButton].filter(w => w);
                        for (const widget of widgets) {
                            const widgetIndex = this.widgets.indexOf(widget);
                            if (widgetIndex > -1) {
                                this.widgets.splice(widgetIndex, 1);
                            }
                        }
                    }
                }
                
                this.promptWidgets = [];
                this.promptCount = 0;
                
                if (onConfigure) onConfigure.call(this, info);
                
                // Restore prompt widgets
                if (info.promptData) {
                    // Remove the default prompt set if it was added
                    if (this.promptWidgets.length === 1 && info.promptData.count > 0) {
                        this.removePromptSet(0);
                    }
                    
                    // Restore saved prompt sets
                    for (let i = 0; i < info.promptData.count; i++) {
                        this.addPromptSet();
                    }
                }
                
                this.updateNodeTitle();
            };
        }
    }
});