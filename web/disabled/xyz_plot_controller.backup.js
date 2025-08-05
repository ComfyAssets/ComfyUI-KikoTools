import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Counter for unique widget names
let widgetCounter = 0;

// Helper text for different parameter types
const PARAM_HELP = {
    cfg_scale: "Enter values separated by commas: 5, 7.5, 10\nOr use range: 5:15:2.5",
    steps: "Enter values separated by commas: 20, 30, 40\nOr use range: 10:50:10",
    seed: "Enter values separated by commas: 42, 123, 456\nOr use range: 0:1000:100",
    denoise: "Enter values separated by commas: 0.3, 0.5, 0.7\nOr use range: 0.2:1.0:0.2",
    clip_skip: "Enter values separated by commas: 1, 2\nCommon values for SDXL",
    prompt: "Enter prompts separated by new lines:\nbeautiful sunset\nmystical forest\nfuturistic city"
};

app.registerExtension({
    name: "ComfyAssets.XYZPlotController",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "XYZPlotController") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                const node = this;
                
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Enable widget serialization
                this.serialize_widgets = true;
                
                // Track widget visibility
                this.hiddenWidgets = new Set();
                
                // Override widget value methods to handle our custom widgets
                const origComputeSize = this.computeSize;
                this.computeSize = function() {
                    const size = origComputeSize ? origComputeSize.call(this) : [200, 100];
                    // Don't auto-resize based on widgets
                    return [this.size[0] || size[0], this.size[1] || size[1]];
                };
                
                // Override setWidgetValue to protect our custom widgets
                const origSetWidgetValue = this.setWidgetValue;
                this.setWidgetValue = function(index, value) {
                    const widget = this.widgets[index];
                    if (widget && widget.type === "xyz_dynamic_widget") {
                        // Only set if value is not null/undefined
                        if (value !== null && value !== undefined) {
                            widget.value = value;
                        }
                        return;
                    }
                    if (origSetWidgetValue) {
                        origSetWidgetValue.call(this, index, value);
                    }
                };
                
                // Override getWidgetValue
                const origGetWidgetValue = this.getWidgetValue;
                this.getWidgetValue = function(index) {
                    const widget = this.widgets[index];
                    if (widget && widget.type === "xyz_dynamic_widget") {
                        return widget.value;
                    }
                    return origGetWidgetValue ? origGetWidgetValue.call(this, index) : undefined;
                };
                
                // Initialize storage for dynamic widgets if not already done
                if (!node.dynamicWidgets) {
                    node.dynamicWidgets = {
                        x: [],
                        y: [],
                        z: []
                    };
                }
                
                // Store references to add buttons
                if (!node.addButtons) {
                    node.addButtons = {};
                }
                
                // Store references to text widgets
                if (!node.textWidgets) {
                    node.textWidgets = {};
                }
                
                // Store last mouse event for context menu positioning
                node.lastMouseEvent = null;
                
                // Setup axis type callbacks
                ["x_type", "y_type", "z_type"].forEach(widgetName => {
                    const widget = node.widgets.find(w => w.name === widgetName);
                    if (widget) {
                        // Set default value to 'none'
                        widget.value = "none";
                        const originalCallback = widget.callback;
                        widget.callback = function(value) {
                            if (originalCallback) originalCallback.call(this, value);
                            updateAxisWidgets(node, widgetName.split("_")[0], value);
                            updateNodeTitle(node);
                        };
                    }
                });
                
                // Add header widget for each axis
                node.headerWidgets = {};
                
                // Initial setup - only run if not already configured
                setTimeout(() => {
                    // Check if we're in initial creation (not restoration)
                    if (!node._configured) {
                        ["x", "y", "z"].forEach(axis => {
                            const typeWidget = node.widgets.find(w => w.name === `${axis}_type`);
                            if (typeWidget) {
                                updateAxisWidgets(node, axis, typeWidget.value);
                            }
                        });
                        updateNodeTitle(node);
                    } else {
                    }
                }, 100);
            };
            
            // Override onSerialize to ensure our custom widgets are saved
            const origOnSerialize = nodeType.prototype.onSerialize;
            nodeType.prototype.onSerialize = function(info) {
                    name: w.name,
                    type: w.type,
                    value: w.value
                })));
                
                // Let original serialization run first
                if (origOnSerialize) {
                    origOnSerialize.call(this, info);
                }
                
                // Log what ComfyUI serialized
                
                // Fix empty text widget values by getting them directly from the widgets
                if (info.widgets_values && this.widgets) {
                    for (let i = 0; i < this.widgets.length && i < info.widgets_values.length; i++) {
                        const widget = this.widgets[i];
                        const serializedValue = info.widgets_values[i];
                        
                        // If the serialized value is empty/null but the widget has a value, use the widget's value
                        if ((serializedValue === '' || serializedValue === null || serializedValue === undefined) && 
                            widget && widget.value !== '' && widget.value !== null && widget.value !== undefined) {
                            info.widgets_values[i] = widget.value;
                        }
                        
                        // Also handle the case where the widget has an inputEl with a value
                        if (widget && widget.inputEl && widget.inputEl.value && 
                            (serializedValue === '' || serializedValue === null || serializedValue === undefined)) {
                            info.widgets_values[i] = widget.inputEl.value;
                        }
                    }
                }
                
            };
            
            // Override mouse events to track position
            const onMouseDown = nodeType.prototype.onMouseDown;
            nodeType.prototype.onMouseDown = function(e, localPos, graphCanvas) {
                this.lastMouseEvent = e;
                return onMouseDown ? onMouseDown.apply(this, arguments) : undefined;
            };
            
            const onMouseUp = nodeType.prototype.onMouseUp;
            nodeType.prototype.onMouseUp = function(e, localPos, graphCanvas) {
                if (e.button === 2) { // Right click
                    this.lastMouseEvent = e;
                }
                return onMouseUp ? onMouseUp.apply(this, arguments) : undefined;
            };
            
            // Override configuration to restore dynamic widgets
            const onConfigure = nodeType.prototype.onConfigure;
            nodeType.prototype.onConfigure = function(info) {
                
                // Mark as configured to prevent initial setup from running
                this._configured = true;
                
                // Store the widgets_values before anything modifies them
                const savedWidgetValues = [...(info.widgets_values || [])];
                
                // Clear dynamic widget tracking for fresh restoration
                if (!this.hiddenWidgets) {
                    this.hiddenWidgets = new Set();
                }
                this.dynamicWidgets = { x: [], y: [], z: [] };
                this.addButtons = {};
                this.textWidgets = {};
                
                // Let ComfyUI restore base widgets first
                if (onConfigure) {
                    onConfigure.call(this, info);
                }
                
                    name: w.name, 
                    type: w.type,
                    value: w.value
                })));
                
                // Remove any existing dynamic widgets that might have been restored incorrectly
                if (this.widgets) {
                    // Remove widgets in reverse order to avoid index issues
                    for (let i = this.widgets.length - 1; i >= 0; i--) {
                        const widget = this.widgets[i];
                        if (widget && (widget.type === "xyz_dynamic_widget" || 
                            widget.name?.includes("Add ") || 
                            widget.name?.includes("_numeric") || 
                            widget.name?.includes("_prompt"))) {
                            this.widgets.splice(i, 1);
                            if (widget.onRemove) {
                                widget.onRemove();
                            }
                        }
                    }
                }
                
                // Restore dynamic widgets from saved values
                // Use our saved copy instead of info.widgets_values which might have been modified
                const widgetValues = savedWidgetValues;
                
                // Log each widget value for debugging
                widgetValues.forEach((val, idx) => {
                });
                
                // Group saved widget values by axis (using the stored _axis property)
                const widgetsByAxis = { x: [], y: [], z: [] };
                
                for (const widgetValue of widgetValues) {
                    if (widgetValue && typeof widgetValue === 'object' && 
                        'on' in widgetValue && 'value' in widgetValue && widgetValue.value) {
                        
                        // Use the stored axis info if available
                        if (widgetValue._axis && widgetsByAxis[widgetValue._axis]) {
                            widgetsByAxis[widgetValue._axis].push(widgetValue);
                        } else {
                            // Fallback: try to guess which axis based on current configuration
                            for (const axis of ['x', 'y', 'z']) {
                                const typeWidget = this.widgets.find(w => w.name === `${axis}_type`);
                                if (typeWidget && canAddDynamicWidget(typeWidget.value)) {
                                    widgetsByAxis[axis].push(widgetValue);
                                    break;
                                }
                            }
                        }
                    }
                }
                
                // First setup axis type callbacks again since we removed all widgets
                ["x_type", "y_type", "z_type"].forEach(widgetName => {
                    const widget = this.widgets.find(w => w.name === widgetName);
                    if (widget) {
                        const originalCallback = widget.callback;
                        widget.callback = function(value) {
                            if (originalCallback) originalCallback.call(this, value);
                            updateAxisWidgets(node, widgetName.split("_")[0], value);
                            updateNodeTitle(node);
                        };
                    }
                });
                
                // Now create widgets for each axis based on restored type values
                for (const axis of ['x', 'y', 'z']) {
                    const typeWidget = this.widgets.find(w => w.name === `${axis}_type`);
                    const axisType = typeWidget?.value;
                    
                    if (axisType && axisType !== "none") {
                        // First update axis widgets to create add buttons and text widgets
                        // Pass true to skip clearing dynamic widgets during restoration
                        updateAxisWidgets(this, axis, axisType, true);
                        
                        // Then restore dynamic widgets if applicable
                        if (canAddDynamicWidget(axisType)) {
                            const savedWidgets = widgetsByAxis[axis];
                            
                            for (const savedValue of savedWidgets) {
                                // Pass the item name, not the full value object
                                const itemName = savedValue.value || "";
                                const widget = createDynamicWidget(this, axis, axisType, itemName);
                                if (widget) {
                                    // Now restore the full value including on/off state and strength
                                    // Use Object.assign to ensure the value is properly set
                                    const fullValue = Object.assign({}, savedValue, {
                                        _axis: axis,
                                        _type: axisType
                                    });
                                    widget.value = fullValue;
                                }
                            }
                        }
                    }
                }
                
                // Manually restore all widget values from saved widget values
                // This is needed because ComfyUI creates the widgets but doesn't always restore their values properly
                for (let i = 0; i < this.widgets.length && i < savedWidgetValues.length; i++) {
                    const widget = this.widgets[i];
                    const savedValue = savedWidgetValues[i];
                    
                    
                    // Skip if no saved value
                    if (savedValue === null || savedValue === undefined) {
                        continue;
                    }
                    
                    // For string values (text widgets)
                    if (widget && typeof savedValue === 'string' && savedValue !== '') {
                        // Check various widget types that might contain text
                        if (widget.type === "text" || widget.type === "string" || widget.type === "customtext" || 
                            widget.name?.includes("numeric") || widget.name?.includes("prompt")) {
                            widget.value = savedValue;
                            
                            // Also update the input element if it exists
                            if (widget.inputEl) {
                                widget.inputEl.value = savedValue;
                            }
                            // Check for callback to trigger updates
                            if (widget.callback) {
                                widget.callback(savedValue);
                            }
                        }
                    }
                }
                
                updateNodeTitle(this);
                
                // Log final state
                
                // Add a slight delay to check if values are being cleared after configure
                setTimeout(() => {
                        name: w.name, 
                        type: w.type, 
                        value: w.type === "xyz_dynamic_widget" ? w.value : w.value
                    })));
                    
                    // Final attempt to restore text widget values if they're still empty
                    for (let i = 0; i < this.widgets.length && i < savedWidgetValues.length; i++) {
                        const widget = this.widgets[i];
                        const savedValue = savedWidgetValues[i];
                        
                        if (widget && typeof savedValue === 'string' && savedValue !== '' && 
                            (!widget.value || widget.value === '')) {
                            widget.value = savedValue;
                            if (widget.inputEl) {
                                widget.inputEl.value = savedValue;
                            }
                        }
                    }
                }, 100);
            };
            
            // Override onExecuted to see if something is clearing values there
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                if (onExecuted) {
                    onExecuted.call(this, message);
                }
            };
        }
    }
});

// Update widgets for an axis based on selected type
function updateAxisWidgets(node, axis, type, skipClearDynamic = false) {
    // During restoration, we don't want to remove anything
    if (!skipClearDynamic) {
        // Hide all widgets for this axis first
        const widgetPrefixes = [`${axis}_numeric`, `${axis}_prompt`, `➕ Add`];
        
        // Hide text widgets and buttons for this axis
        node.widgets?.forEach(widget => {
            if (widget.name && widgetPrefixes.some(prefix => widget.name.includes(prefix) || 
                (widget.name.includes(axis) && (widget.name.includes('numeric') || widget.name.includes('prompt'))))) {
                widget.hidden = true;
                widget.computeSize = () => [0, 0];
                node.hiddenWidgets?.add(widget.name);
            }
        });
        
        // Remove existing add button
        if (node.addButtons[axis]) {
            const index = node.widgets.indexOf(node.addButtons[axis]);
            if (index > -1) {
                node.widgets.splice(index, 1);
            }
            node.addButtons[axis] = null;
        }
        
        // Clear dynamic widgets for this axis
        if (node.dynamicWidgets[axis]) {
            while (node.dynamicWidgets[axis].length > 0) {
                const widget = node.dynamicWidgets[axis].pop();
                const index = node.widgets.indexOf(widget);
                if (index > -1) {
                    node.widgets.splice(index, 1);
                }
            }
        }
    }
    
    if (type === "none") {
        // Don't resize - respect user's manual sizing
        return;
    }
    
    // Add widgets based on type
    if (canAddDynamicWidget(type)) {
        // Add button for dynamic widget types if it doesn't exist
        if (!node.addButtons[axis]) {
            const buttonLabel = `➕ Add ${type.charAt(0).toUpperCase() + type.slice(1, -1)}`;
            const button = node.addWidget("button", buttonLabel, null, (value, canvas, node, pos, event) => {
                showResourceChooser(node, axis, type, event || window.event);
                return true;
            });
            node.addButtons[axis] = button;
        }
    } else if (["cfg_scale", "steps", "seed", "denoise", "clip_skip"].includes(type)) {
        // Check if text widget already exists
        const widgetName = `${axis}_numeric`;
        let existingWidget = node.widgets?.find(w => w.name === widgetName);
        
        if (!existingWidget) {
            // Only create new widget if it doesn't exist
            const textWidget = ComfyWidgets.STRING(node, widgetName, ["STRING", {
                default: "",
                multiline: true,
                placeholder: PARAM_HELP[type] || "Enter values"
            }]);
            textWidget.widget.inputEl.style.fontFamily = "monospace";
            textWidget.widget.inputEl.rows = 3;
            node.textWidgets[axis] = textWidget.widget;
            
            // Add input listener for live updates
            textWidget.widget.inputEl.addEventListener("input", () => {
                updateNodeTitle(node);
            });
        } else {
            // Widget already exists, just track it and unhide it
            node.textWidgets[axis] = existingWidget;
            existingWidget.hidden = false;
            existingWidget.computeSize = () => [node.size[0] - 20, LiteGraph.NODE_WIDGET_HEIGHT];
            node.hiddenWidgets?.delete(existingWidget.name);
            
            // Re-add input listener in case it was lost
            if (existingWidget.inputEl && !existingWidget._hasUpdateListener) {
                existingWidget.inputEl.addEventListener("input", () => {
                    updateNodeTitle(node);
                });
                existingWidget._hasUpdateListener = true;
            }
        }
    } else if (type === "prompt") {
        // Check if prompt widget already exists
        const widgetName = `${axis}_prompt`;
        let existingWidget = node.widgets?.find(w => w.name === widgetName);
        
        if (!existingWidget) {
            // Only create new widget if it doesn't exist
            const textWidget = ComfyWidgets.STRING(node, widgetName, ["STRING", {
                default: "",
                multiline: true,
                placeholder: PARAM_HELP.prompt
            }]);
            textWidget.widget.inputEl.style.fontFamily = "monospace";
            textWidget.widget.inputEl.rows = 4;
            node.textWidgets[axis] = textWidget.widget;
            
            // Add input listener for live updates
            textWidget.widget.inputEl.addEventListener("input", () => {
                updateNodeTitle(node);
            });
        } else {
            // Widget already exists, just track it and unhide it
            node.textWidgets[axis] = existingWidget;
            existingWidget.hidden = false;
            existingWidget.computeSize = () => [node.size[0] - 20, LiteGraph.NODE_WIDGET_HEIGHT];
            node.hiddenWidgets?.delete(existingWidget.name);
            
            // Re-add input listener in case it was lost
            if (existingWidget.inputEl && !existingWidget._hasUpdateListener) {
                existingWidget.inputEl.addEventListener("input", () => {
                    updateNodeTitle(node);
                });
                existingWidget._hasUpdateListener = true;
            }
        }
    }
    
    // Don't auto-resize - respect user's manual sizing
}

// Check if a type can have dynamic widgets
function canAddDynamicWidget(type) {
    return ["models", "vaes", "loras", "samplers", "schedulers"].includes(type);
}

// Show resource chooser based on type
function showResourceChooser(node, axis, type, event) {
    // Get available options based on type
    let options = [];
    let title = "Choose a " + type.slice(0, -1); // Remove 's' for singular
    
    // Try to get options from existing nodes or use defaults
    if (type === "models") {
        // Try to find a checkpoint loader node to get model list
        const checkpointNode = app.graph._nodes.find(n => n.type === "CheckpointLoaderSimple");
        if (checkpointNode && checkpointNode.widgets) {
            const modelWidget = checkpointNode.widgets.find(w => w.type === "combo");
            if (modelWidget && modelWidget.options && modelWidget.options.values) {
                options = [...modelWidget.options.values];
            }
        }
        if (options.length === 0) {
            options = ["No models found"];
        }
    } else if (type === "vaes") {
        options = [];
        // Try to find a VAE loader node
        const vaeNode = app.graph._nodes.find(n => n.type === "VAELoader");
        if (vaeNode && vaeNode.widgets) {
            const vaeWidget = vaeNode.widgets.find(w => w.type === "combo");
            if (vaeWidget && vaeWidget.options && vaeWidget.options.values) {
                options = [...vaeWidget.options.values];
            }
        }
        if (options.length === 0) {
            options = ["Automatic"];
        }
    } else if (type === "loras") {
        options = [];
        // Try multiple ways to find LoRA options
        
        // Method 1: Look for any LoraLoader node
        const loraNodes = app.graph._nodes.filter(n => 
            n.type === "LoraLoader" || 
            n.type === "Power Lora Loader (rgthree)" ||
            n.type?.includes("Lora") ||
            n.type?.includes("lora")
        );
        
        for (const node of loraNodes) {
            if (node.widgets) {
                const loraWidget = node.widgets.find(w => 
                    (w.type === "combo" && (w.name === "lora_name" || w.name?.includes("lora"))) ||
                    (w.options?.values && Array.isArray(w.options.values) && w.options.values.length > 0)
                );
                if (loraWidget && loraWidget.options && loraWidget.options.values) {
                    options = [...loraWidget.options.values];
                    break;
                }
            }
        }
        
        // Method 2: Check if we can get from node definitions
        if (options.length === 0) {
            try {
                const nodeData = LiteGraph.registered_node_types["LoraLoader"];
                if (nodeData && nodeData.nodeData && nodeData.nodeData.input) {
                    const loraInput = nodeData.nodeData.input.required?.lora_name;
                    if (loraInput && Array.isArray(loraInput[0])) {
                        options = [...loraInput[0]];
                    }
                }
            } catch (e) {
            }
        }
        
        // If still no options, show a message
        if (options.length === 0) {
            options = ["No LoRAs found - Add a LoraLoader node first"];
        } else {
        }
    } else if (type === "samplers") {
        // Try to find a KSampler node
        const samplerNode = app.graph._nodes.find(n => n.type === "KSampler");
        if (samplerNode && samplerNode.widgets) {
            const samplerWidget = samplerNode.widgets.find(w => w.name === "sampler");
            if (samplerWidget && samplerWidget.options && samplerWidget.options.values) {
                options = [...samplerWidget.options.values];
            } else {
                options = ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", 
                          "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", 
                          "dpmpp_sde", "dpmpp_2m", "dpmpp_2m_sde", "ddim", "uni_pc"];
            }
        } else {
            options = ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", 
                      "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", 
                      "dpmpp_sde", "dpmpp_2m", "dpmpp_2m_sde", "ddim", "uni_pc"];
        }
    } else if (type === "schedulers") {
        // Try to find a KSampler node
        const samplerNode = app.graph._nodes.find(n => n.type === "KSampler");
        if (samplerNode && samplerNode.widgets) {
            const schedulerWidget = samplerNode.widgets.find(w => w.name === "scheduler");
            if (schedulerWidget && schedulerWidget.options && schedulerWidget.options.values) {
                options = [...schedulerWidget.options.values];
            } else {
                options = ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"];
            }
        } else {
            options = ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"];
        }
    }
    
    // Show context menu for selection
    const canvas = app.canvas;
    if (!event) {
        event = canvas.last_mouse_event || new MouseEvent('click', {
            clientX: canvas.mouse[0],
            clientY: canvas.mouse[1]
        });
    }
    
    new LiteGraph.ContextMenu(options, {
        event: event,
        title: title,
        scale: Math.max(1, canvas.ds?.scale || 1),
        callback: (value) => {
            if (value && value !== "None" && !value.includes("No") && !value.includes("found")) {
                createDynamicWidget(node, axis, type, value);
                updateNodeTitle(node);
            }
        }
    });
}

// Create a dynamic widget for the given axis and type with selected value
function createDynamicWidget(node, axis, type, selectedValue) {
    widgetCounter++;
    const widgetName = `${axis}_${type}_${widgetCounter}`;
    
    // Create a custom widget that ComfyUI will properly serialize
    class XYZDynamicWidget {
        constructor(name, value) {
            this.name = name;
            this._value = value;
            this.type = "xyz_dynamic_widget";
            this.y = 0;
            this.options = {};
        }
        
        // Use getter/setter to ensure value persistence
        get value() {
            return this._value;
        }
        
        set value(v) {
            this._value = v;
        }
        
        draw(ctx, node, width, y) {
            // Will be replaced
        }
        
        mouse(event, pos, node) {
            // Will be replaced
            return false;
        }
        
        computeSize() {
            return [node.size[0], LiteGraph.NODE_WIDGET_HEIGHT];
        }
        
        serialize() {
            return this._value;
        }
        
        serializeValue(node, index) {
            // Return a deep copy to prevent modification
            return this._value ? { ...this._value } : null;
        }
        
        onRemove() {}
    }
    
    const widget = new XYZDynamicWidget(widgetName, null);
    
    // Add widget to node
    if (!node.widgets) {
        node.widgets = [];
    }
    node.widgets.push(widget);
    
    // Store value with on/off state and strength for loras
    // Add axis and type info to help with restoration
    if (type === "loras") {
        widget.value = { 
            on: true, 
            value: selectedValue, 
            strength: 1.0,
            _axis: axis,  // Store axis info
            _type: type   // Store type info
        };
    } else {
        widget.value = { 
            on: true, 
            value: selectedValue,
            _axis: axis,  // Store axis info
            _type: type   // Store type info
        };
    }
    
    // Widget is already added to node in the constructor above
    
    // Track mouse movement for strength adjustment
    widget.mouseState = {
        dragging: false,
        startX: 0,
        startValue: 0,
        lastClickTime: 0
    };
    
    // Custom draw function to show toggle and value with strength for loras
    widget.draw = function(ctx, node, width, y) {
        const margin = 10;
        const innerMargin = 3;
        const height = LiteGraph.NODE_WIDGET_HEIGHT;
        const midY = y + height / 2;
        let posX = margin;
        
        ctx.save();
        
        // Draw background rounded rectangle
        ctx.fillStyle = "rgba(0,0,0,0.2)";
        ctx.beginPath();
        ctx.roundRect(posX, y + 2, width - margin * 2, height - 4, [height * 0.5]);
        ctx.fill();
        
        // Draw toggle - Power Lora Loader style
        const toggleRadius = height * 0.36;
        const toggleBgWidth = height * 1.5;
        
        // Toggle background
        ctx.beginPath();
        ctx.roundRect(posX + 4, y + 4, toggleBgWidth - 8, height - 8, [height * 0.5]);
        ctx.globalAlpha = app.canvas.editor_alpha * 0.25;
        ctx.fillStyle = "rgba(255,255,255,0.45)";
        ctx.fill();
        ctx.globalAlpha = app.canvas.editor_alpha;
        
        // Toggle circle
        const toggleX = widget.value.on ? posX + height : posX + height * 0.5;
        ctx.fillStyle = widget.value.on ? "#89B" : "#888";
        ctx.beginPath();
        ctx.arc(toggleX, midY, toggleRadius, 0, Math.PI * 2);
        ctx.fill();
        
        widget.toggleBounds = [posX, toggleBgWidth];
        posX += toggleBgWidth + innerMargin;
        
        // Apply opacity if disabled
        if (!widget.value.on) {
            ctx.globalAlpha = app.canvas.editor_alpha * 0.4;
        }
        
        // Draw strength controls for loras
        let strengthX = width - margin - innerMargin;
        if (type === "loras" && widget.value.strength !== undefined) {
            // Draw strength value and controls
            const arrowWidth = 9;
            const numberWidth = 32;
            
            // Right arrow ▶
            ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
            ctx.beginPath();
            const rightArrowX = strengthX - arrowWidth;
            ctx.moveTo(rightArrowX + arrowWidth, midY);
            ctx.lineTo(rightArrowX, midY - 5);
            ctx.lineTo(rightArrowX, midY + 5);
            ctx.closePath();
            ctx.fill();
            widget.incBounds = [rightArrowX, arrowWidth];
            
            // Strength value
            strengthX = rightArrowX - innerMargin - numberWidth;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(widget.value.strength.toFixed(2), strengthX + numberWidth/2, midY);
            widget.valBounds = [strengthX, numberWidth];
            
            // Left arrow ◀
            strengthX = strengthX - innerMargin - arrowWidth;
            ctx.beginPath();
            ctx.moveTo(strengthX, midY);
            ctx.lineTo(strengthX + arrowWidth, midY - 5);
            ctx.lineTo(strengthX + arrowWidth, midY + 5);
            ctx.closePath();
            ctx.fill();
            widget.decBounds = [strengthX, arrowWidth];
            
            strengthX -= innerMargin;
        }
        
        // Draw the value text and track its bounds for right-click
        const textWidth = strengthX - posX - innerMargin;
        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        
        // Fit text to available space
        let text = widget.value.value || "";
        ctx.font = "12px Arial";
        const metrics = ctx.measureText(text);
        if (metrics.width > textWidth) {
            // Truncate with ellipsis
            while (text.length > 0 && ctx.measureText(text + "...").width > textWidth) {
                text = text.substring(0, text.length - 1);
            }
            text += "...";
        }
        ctx.fillText(text, posX, midY);
        
        // Store the lora name bounds for right-click detection
        widget.loraBounds = [posX, textWidth];
        
        ctx.restore();
    };
    
    // Handle mouse events - pos is relative to widget
    widget.mouse = function(event, pos, node) {
        const height = LiteGraph.NODE_WIDGET_HEIGHT;
        
        if (event.type === "mousedown" || event.type === "pointerdown") {
            // Check toggle bounds
            if (widget.toggleBounds && pos[0] >= widget.toggleBounds[0] && 
                pos[0] <= widget.toggleBounds[0] + widget.toggleBounds[1]) {
                widget.value.on = !widget.value.on;
                updateNodeTitle(node);
                node.setDirtyCanvas(true, true);
                return true;
            }
            
            // Check strength controls for loras
            if (type === "loras" && widget.value.strength !== undefined) {
                // Decrease button
                if (widget.decBounds && pos[0] >= widget.decBounds[0] && 
                    pos[0] <= widget.decBounds[0] + widget.decBounds[1]) {
                    widget.value.strength = Math.max(-3, widget.value.strength - 0.1);
                    widget.value.strength = Math.round(widget.value.strength * 10) / 10;
                    updateNodeTitle(node);
                    node.setDirtyCanvas(true, true);
                    return true;
                }
                
                // Increase button
                if (widget.incBounds && pos[0] >= widget.incBounds[0] && 
                    pos[0] <= widget.incBounds[0] + widget.incBounds[1]) {
                    widget.value.strength = Math.min(3, widget.value.strength + 0.1);
                    widget.value.strength = Math.round(widget.value.strength * 10) / 10;
                    updateNodeTitle(node);
                    node.setDirtyCanvas(true, true);
                    return true;
                }
                
                // Double-click or drag on value
                if (widget.valBounds && pos[0] >= widget.valBounds[0] && 
                    pos[0] <= widget.valBounds[0] + widget.valBounds[1]) {
                    
                    // Check for double-click
                    const currentTime = Date.now();
                    if (currentTime - widget.mouseState.lastClickTime < 300) {
                        // Double-click detected - show input dialog
                        const currentValue = widget.value.strength;
                        app.canvas.prompt("Value", currentValue.toFixed(2), (v) => {
                            const value = Number(v);
                            if (!isNaN(value)) {
                                widget.value.strength = Math.max(-3, Math.min(3, value));
                                updateNodeTitle(node);
                                node.setDirtyCanvas(true, true);
                            }
                        }, event);
                        widget.mouseState.lastClickTime = 0; // Reset to prevent triple-click
                    } else {
                        // Single click - start dragging
                        widget.mouseState.dragging = true;
                        widget.mouseState.startX = pos[0];
                        widget.mouseState.startValue = widget.value.strength;
                        widget.mouseState.lastClickTime = currentTime;
                    }
                    return true;
                }
            }
        } else if ((event.type === "mousemove" || event.type === "pointermove") && widget.mouseState.dragging) {
            // Drag to adjust strength
            const delta = (pos[0] - widget.mouseState.startX) / 50;
            widget.value.strength = Math.max(-3, Math.min(3, widget.mouseState.startValue + delta));
            widget.value.strength = Math.round(widget.value.strength * 100) / 100;
            updateNodeTitle(node);
            node.setDirtyCanvas(true, true);
            return true;
        } else if (event.type === "mouseup" || event.type === "pointerup") {
            widget.mouseState.dragging = false;
        }
        
        return false;
    };
    
    // Override getSlotInPosition to handle widget clicks only on lora name area
    const originalGetSlotInPosition = node.getSlotInPosition;
    if (!node._xyzGetSlotInPositionPatched) {
        node._xyzGetSlotInPositionPatched = true;
        node.getSlotInPosition = function(x, y) {
            const slot = originalGetSlotInPosition ? originalGetSlotInPosition.call(this, x, y) : null;
            if (!slot) {
                // Check if we clicked on a dynamic widget's lora name area
                const localX = x - this.pos[0];
                const localY = y - this.pos[1];
                
                for (const w of this.widgets || []) {
                    if (w.type === "xyz_dynamic_widget" && w.y && localY > w.y && localY < w.y + LiteGraph.NODE_WIDGET_HEIGHT) {
                        // Check if click is within lora name bounds
                        if (w.loraBounds && localX >= w.loraBounds[0] && localX <= w.loraBounds[0] + w.loraBounds[1]) {
                            return { widget: w, output: { type: "XYZ_DYNAMIC_WIDGET" } };
                        }
                    }
                }
            }
            return slot;
        };
    }
    
    // Override getSlotMenuOptions for right-click menu
    const originalGetSlotMenuOptions = node.getSlotMenuOptions;
    if (!node._xyzGetSlotMenuOptionsPatched) {
        node._xyzGetSlotMenuOptionsPatched = true;
        node.getSlotMenuOptions = function(slot) {
            if (slot?.output?.type === "XYZ_DYNAMIC_WIDGET" && slot.widget?.type === "xyz_dynamic_widget") {
                const widget = slot.widget;
                const parts = widget.name.split("_");
                const axis = parts[0];
                const type = parts[1];
                // Find widget in dynamicWidgets array
                const widgetIndex = this.dynamicWidgets[axis] ? this.dynamicWidgets[axis].indexOf(widget) : -1;
                if (widgetIndex === -1) {
                    console.warn(`[XYZ Plot] Widget not found in dynamicWidgets[${axis}]`);
                }
                
                // Check if we can move up/down
                const canMoveUp = widgetIndex > 0;
                const canMoveDown = widgetIndex >= 0 && this.dynamicWidgets[axis] && widgetIndex < this.dynamicWidgets[axis].length - 1;
                
                const menuItems = [];
                
                // Show Info for loras
                if (type === "loras") {
                    menuItems.push({
                        content: `ℹ️ Show Info`,
                        disabled: true,  // For now, until we implement lora info dialog
                        callback: () => {
                            // TODO: Implement lora info dialog
                        }
                    });
                    menuItems.push(null); // separator
                }
                
                // Toggle on/off
                menuItems.push({
                    content: `${widget.value.on ? "⚫" : "🟢"} Toggle ${widget.value.on ? "Off" : "On"}`,
                    callback: () => {
                        widget.value.on = !widget.value.on;
                        updateNodeTitle(node);
                        node.setDirtyCanvas(true, true);
                    }
                });
                
                // Move up
                menuItems.push({
                    content: `⬆️ Move Up`,
                    disabled: !canMoveUp,
                    callback: () => {
                        if (canMoveUp) {
                            // Swap in dynamic widgets array
                            const temp = this.dynamicWidgets[axis][widgetIndex];
                            this.dynamicWidgets[axis][widgetIndex] = this.dynamicWidgets[axis][widgetIndex - 1];
                            this.dynamicWidgets[axis][widgetIndex - 1] = temp;
                            
                            // Find positions in main widgets array
                            const currentIndex = this.widgets.indexOf(widget);
                            const prevWidget = this.dynamicWidgets[axis][widgetIndex];
                            const prevIndex = this.widgets.indexOf(prevWidget);
                            
                            // Swap in main widgets array
                            if (currentIndex > -1 && prevIndex > -1) {
                                this.widgets.splice(currentIndex, 1);
                                this.widgets.splice(prevIndex, 0, widget);
                            }
                            
                            this.setDirtyCanvas(true, true);
                        }
                    }
                });
                
                // Move down
                menuItems.push({
                    content: `⬇️ Move Down`,
                    disabled: !canMoveDown,
                    callback: () => {
                        if (canMoveDown) {
                            // Swap in dynamic widgets array
                            const temp = this.dynamicWidgets[axis][widgetIndex];
                            this.dynamicWidgets[axis][widgetIndex] = this.dynamicWidgets[axis][widgetIndex + 1];
                            this.dynamicWidgets[axis][widgetIndex + 1] = temp;
                            
                            // Find positions in main widgets array
                            const currentIndex = this.widgets.indexOf(widget);
                            const nextWidget = this.dynamicWidgets[axis][widgetIndex];
                            const nextIndex = this.widgets.indexOf(nextWidget);
                            
                            // Swap in main widgets array
                            if (currentIndex > -1 && nextIndex > -1) {
                                this.widgets.splice(currentIndex, 1);
                                this.widgets.splice(nextIndex + 1, 0, widget);
                            }
                            
                            this.setDirtyCanvas(true, true);
                        }
                    }
                });
                
                // Remove
                menuItems.push({
                    content: `🗑️ Remove`,
                    callback: () => {
                        // Remove from dynamic widgets
                        const idx = this.dynamicWidgets[axis] ? this.dynamicWidgets[axis].indexOf(widget) : -1;
                        if (idx > -1) {
                            this.dynamicWidgets[axis].splice(idx, 1);
                        }
                        
                        // Remove from main widgets
                        const widgetIdx = this.widgets.indexOf(widget);
                        if (widgetIdx > -1) {
                            this.widgets.splice(widgetIdx, 1);
                        }
                        
                        updateNodeTitle(this);
                        this.setDirtyCanvas(true, true);
                    }
                });
                
                // Show the context menu
                // We need to use the canvas mouse event that has proper coordinates
                const canvasEvent = app.canvas.last_mouse_event || window.event;
                if (!canvasEvent) {
                    // Create a synthetic event at the node position if we don't have a real event
                    const nodePos = node.pos || [100, 100];
                    const widgetY = slot.widget.y || 0;
                    canvasEvent = new MouseEvent('contextmenu', {
                        clientX: nodePos[0] + 100,
                        clientY: nodePos[1] + widgetY + 20,
                        bubbles: true
                    });
                }
                
                new LiteGraph.ContextMenu(menuItems, {
                    title: type === "loras" ? "LORA WIDGET" : type.toUpperCase().slice(0, -1) + " WIDGET",
                    event: canvasEvent,
                    parentMenu: null
                });
                
                return null; // Prevent default menu
            }
            
            // Call original if not our widget
            return originalGetSlotMenuOptions ? originalGetSlotMenuOptions.call(this, slot) : null;
        };
    }
    
    // Add to dynamic widgets array - IMPORTANT for tracking
    if (!node.dynamicWidgets) {
        console.warn(`[XYZ Plot] dynamicWidgets was null, reinitializing`);
        node.dynamicWidgets = { x: [], y: [], z: [] };
    }
    if (!node.dynamicWidgets[axis]) {
        node.dynamicWidgets[axis] = [];
    }
    node.dynamicWidgets[axis].push(widget);
    
    // Position widget after add button
    if (node.addButtons[axis]) {
        const buttonIndex = node.widgets.indexOf(node.addButtons[axis]);
        if (buttonIndex > -1) {
            node.widgets.splice(node.widgets.indexOf(widget), 1);
            node.widgets.splice(buttonIndex + 1, 0, widget);
        }
    }
    
    // Don't auto-resize - respect user's manual sizing
    return widget;
}

// Update node title with image count
function updateNodeTitle(node) {
    const counts = { x: 0, y: 0, z: 0 };
    
    ["x", "y", "z"].forEach(axis => {
        const typeWidget = node.widgets.find(w => w.name === `${axis}_type`);
        if (!typeWidget || typeWidget.value === "none") {
            counts[axis] = 1;
            return;
        }
        
        const type = typeWidget.value;
        
        if (canAddDynamicWidget(type)) {
            // Count enabled dynamic widgets
            counts[axis] = node.dynamicWidgets[axis]
                .filter(w => {
                    if (typeof w.value === 'object' && w.value) {
                        return w.value.on;
                    }
                    return false;
                })
                .length;
        } else if (["cfg_scale", "steps", "seed", "denoise", "clip_skip"].includes(type)) {
            // Count numeric values
            const textWidget = node.textWidgets[axis];
            if (textWidget && textWidget.value) {
                const values = textWidget.value.trim();
                if (values.includes(':')) {
                    const parts = values.split(':');
                    if (parts.length >= 2) {
                        const start = parseFloat(parts[0]);
                        const stop = parseFloat(parts[1]);
                        const step = parts[2] ? parseFloat(parts[2]) : 1;
                        counts[axis] = Math.floor((stop - start) / step) + 1;
                    }
                } else {
                    counts[axis] = values.split(',').filter(v => v.trim()).length;
                }
            }
        } else if (type === "prompt") {
            // Count prompts
            const textWidget = node.textWidgets[axis];
            if (textWidget && textWidget.value) {
                counts[axis] = textWidget.value.split('\n').filter(p => p.trim()).length;
            }
        }
        
        counts[axis] = Math.max(1, counts[axis]);
    });
    
    const totalImages = counts.x * counts.y * counts.z;
    node.title = `XYZ Plot Controller (${totalImages} images)`;
    
    if (totalImages > 100) {
        node.title += " ⚠️";
    }
}