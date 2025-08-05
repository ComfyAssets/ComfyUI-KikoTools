import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";
import { api } from "../../scripts/api.js";

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

// Helper function to check if we're in low quality mode
function isLowQuality() {
    const canvas = app.canvas;
    return ((canvas.ds?.scale) || 1) <= 0.5;
}

// Optimized toggle drawing function
function drawTogglePart(ctx, options) {
    const lowQuality = isLowQuality();
    ctx.save();
    
    const { posX, posY, height, value } = options;
    const toggleRadius = height * 0.36;
    const toggleBgWidth = height * 1.5;
    
    if (!lowQuality) {
        ctx.beginPath();
        ctx.roundRect(posX + 4, posY + 4, toggleBgWidth - 8, height - 8, [height * 0.5]);
        ctx.globalAlpha = app.canvas.editor_alpha * 0.25;
        ctx.fillStyle = "rgba(255,255,255,0.45)";
        ctx.fill();
        ctx.globalAlpha = app.canvas.editor_alpha;
    }
    
    ctx.fillStyle = value ? "#89B" : "#888";
    const toggleX = lowQuality || !value
        ? posX + height * 0.5
        : posX + height;
    
    ctx.beginPath();
    ctx.arc(toggleX, posY + height * 0.5, toggleRadius, 0, Math.PI * 2);
    ctx.fill();
    
    ctx.restore();
    return [posX, toggleBgWidth];
}

// Custom dynamic widget class with RGThree-style UI
class XYZDynamicWidget {
    constructor(name, value) {
        this.name = name;
        this._value = value;
        this.type = "xyz_dynamic_widget";
        this.y = 0;
        this.options = {};
        
        // Mouse state for drag operations
        this.mouseState = {
            dragging: false,
            startX: 0,
            startValue: 0,
            lastClickTime: 0
        };
    }
    
    get value() {
        return this._value;
    }
    
    set value(v) {
        this._value = v;
    }
    
    serializeValue(node, index) {
        return this._value ? { ...this._value } : null;
    }
    
    draw(ctx, node, width, y) {
        const margin = 10;
        const innerMargin = 3;
        const height = LiteGraph.NODE_WIDGET_HEIGHT;
        const midY = y + height / 2;
        const lowQuality = isLowQuality();
        let posX = margin;
        
        ctx.save();
        
        // Background - skip complex drawing in low quality
        if (!lowQuality) {
            ctx.fillStyle = "rgba(0,0,0,0.2)";
            ctx.beginPath();
            ctx.roundRect(posX, y + 2, width - margin * 2, height - 4, [height * 0.5]);
            ctx.fill();
        }
        
        // Draw toggle with optimized function
        this.toggleBounds = drawTogglePart(ctx, { posX, posY: y, height, value: this.value.on });
        posX += this.toggleBounds[1] + innerMargin;
        
        // Skip text drawing in low quality mode
        if (lowQuality) {
            ctx.restore();
            return;
        }
        
        // Apply opacity if disabled
        if (!this.value.on) {
            ctx.globalAlpha = app.canvas.editor_alpha * 0.4;
        }
        
        // Draw name/value - for dropdown types, show the selected value
        const displayText = this.value.value || this.value.name || "None";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
        
        // Fit text if too long
        const maxTextWidth = width - posX - margin;
        const textWidth = ctx.measureText(displayText).width;
        if (textWidth > maxTextWidth) {
            // Use ellipsis for long text
            let truncated = displayText;
            while (truncated.length > 0 && ctx.measureText(truncated + "…").width > maxTextWidth) {
                truncated = truncated.slice(0, -1);
            }
            ctx.fillText(truncated + "…", posX, midY);
            this.nameBounds = [posX, ctx.measureText(truncated + "…").width];
        } else {
            ctx.fillText(displayText, posX, midY);
            this.nameBounds = [posX, textWidth];
        }
        
        ctx.restore();
    }
    
    mouse(event, pos, node) {
        const margin = 10;
        const localX = pos[0] - margin;
        
        if (event.type === "mousedown") {
            // Toggle click
            if (localX >= this.toggleBounds[0] && 
                localX <= this.toggleBounds[0] + this.toggleBounds[1]) {
                this.value.on = !this.value.on;
                node.setDirtyCanvas(true, true);
                updateNodeTitle(node);
                return true;
            }
            
            // Click on name/value to show dropdown
            if (this.nameBounds && localX >= this.nameBounds[0] && 
                localX <= this.nameBounds[0] + this.nameBounds[1]) {
                // Show dropdown menu for selection
                if (this.value.options && this.value.options.length > 0) {
                    const menu = new LiteGraph.ContextMenu(
                        this.value.options,
                        {
                            event: event,
                            callback: (value) => {
                                this.value.value = value;
                                node.setDirtyCanvas(true, true);
                            }
                        }
                    );
                    return true;
                }
            }
        }
        
        return false;
    }
    
    computeSize(width) {
        return [width || 300, LiteGraph.NODE_WIDGET_HEIGHT];
    }
}

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
                
                // Initialize storage for dynamic widgets
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
                
                // Setup axis type callbacks
                ["x_type", "y_type", "z_type"].forEach(widgetName => {
                    const widget = node.widgets.find(w => w.name === widgetName);
                    if (widget) {
                        const originalCallback = widget.callback;
                        widget.callback = function(value) {
                            if (originalCallback) originalCallback.call(this, value);
                            updateAxisWidgets(node, widgetName.split("_")[0], value);
                            updateNodeTitle(node);
                        };
                    }
                });
                
                // Pre-fetch common options to cache them
                setTimeout(() => {
                    getSamplers();
                    getSchedulers();
                }, 100);
                
                // Override configuration for proper restoration
                const onConfigure = nodeType.prototype.onConfigure;
                nodeType.prototype.onConfigure = function(info) {
                    this._configured = true;
                    
                    // Save widget values before ComfyUI modifies them
                    const savedWidgetValues = [...(info.widgets_values || [])];
                    
                    // Clear for fresh restoration
                    if (!this.hiddenWidgets) {
                        this.hiddenWidgets = new Set();
                    }
                    this.dynamicWidgets = { x: [], y: [], z: [] };
                    this.addButtons = {};
                    this.textWidgets = {};
                    
                    // Let ComfyUI restore base widgets
                    if (onConfigure) {
                        onConfigure.call(this, info);
                    }
                    
                    // Restore dynamic widgets
                    let widgetIndex = this.widgets.length;
                    for (let i = widgetIndex; i < savedWidgetValues.length; i++) {
                        const value = savedWidgetValues[i];
                        if (value && typeof value === 'object' && value._axis) {
                            const widget = new XYZDynamicWidget(
                                `dynamic_${widgetCounter++}`,
                                value
                            );
                            this.addCustomWidget(widget);
                            
                            if (this.dynamicWidgets[value._axis]) {
                                this.dynamicWidgets[value._axis].push(widget);
                            }
                        }
                    }
                    
                    // Restore text widget values
                    for (let i = 0; i < this.widgets.length && i < savedWidgetValues.length; i++) {
                        const widget = this.widgets[i];
                        const savedValue = savedWidgetValues[i];
                        
                        if (widget && typeof savedValue === 'string' && savedValue !== '') {
                            widget.value = savedValue;
                            if (widget.inputEl) {
                                widget.inputEl.value = savedValue;
                            }
                        }
                    }
                    
                    // Update UI based on restored state
                    for (const axis of ['x', 'y', 'z']) {
                        const typeWidget = this.widgets.find(w => w.name === `${axis}_type`);
                        if (typeWidget) {
                            updateAxisWidgets(this, axis, typeWidget.value, true);
                        }
                    }
                    
                    updateNodeTitle(this);
                };
                
                // Override serialization to fix widget value persistence
                const origOnSerialize = nodeType.prototype.onSerialize;
                nodeType.prototype.onSerialize = function(info) {
                    if (origOnSerialize) {
                        origOnSerialize.call(this, info);
                    }
                    
                    // Fix empty text widget values
                    if (info.widgets_values && this.widgets) {
                        for (let i = 0; i < this.widgets.length && i < info.widgets_values.length; i++) {
                            const widget = this.widgets[i];
                            const serializedValue = info.widgets_values[i];
                            
                            if ((serializedValue === '' || serializedValue === null) && 
                                widget && widget.value !== '' && widget.value !== null) {
                                info.widgets_values[i] = widget.value;
                            }
                            
                            if (widget && widget.inputEl && widget.inputEl.value && 
                                (serializedValue === '' || serializedValue === null)) {
                                info.widgets_values[i] = widget.inputEl.value;
                            }
                        }
                    }
                };
                
                // Implement right-click context menu
                implementContextMenu(node);
                
                // Override getExtraMenuOptions to handle execution
                const origGetExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
                nodeType.prototype.getExtraMenuOptions = function(_, options) {
                    if (origGetExtraMenuOptions) {
                        origGetExtraMenuOptions.call(this, _, options);
                    }
                    
                    // Prepare widget values for execution
                    const executeCallback = () => {
                        // Format dynamic widget values for Python backend
                        const values = {};
                        
                        for (const axis of ['x', 'y', 'z']) {
                            // Add dynamic widgets
                            const widgets = this.dynamicWidgets[axis];
                            widgets.forEach((widget, index) => {
                                const key = `${axis}_${widget.value._type}_${index}`;
                                values[key] = {
                                    on: widget.value.on,
                                    value: widget.value.value
                                };
                            });
                            
                            // Add text widget values
                            const typeWidget = this.widgets.find(w => w.name === `${axis}_type`);
                            if (typeWidget && needsTextWidget(typeWidget.value)) {
                                const textWidget = this.textWidgets[axis];
                                if (textWidget) {
                                    if (typeWidget.value === "prompt") {
                                        values[`${axis}_prompt`] = textWidget.value || "";
                                    } else {
                                        values[`${axis}_numeric`] = textWidget.value || "";
                                    }
                                }
                            }
                        }
                        
                        // Add to widgets_values for proper serialization
                        if (this.widgets_values) {
                            Object.assign(this.widgets_values, values);
                        }
                    };
                    
                    // Hook into execution
                    if (this.mode === 0) { // Only in active mode
                        executeCallback();
                    }
                };
            };
        }
    }
});

// Helper function to update widgets based on axis type
function updateAxisWidgets(node, axis, type, skipClear = false) {
    if (!skipClear) {
        // Hide text widgets and buttons for this axis (but not the type dropdown!)
        node.widgets?.forEach(widget => {
            if (widget.name?.includes(`${axis}_`) && widget.name !== `${axis}_type`) {
                // Only hide if it's a text widget or add button
                if (widget.type === "text" || widget.type === "button" || widget.name.includes("_select")) {
                    widget.hidden = true;
                    widget.computeSize = () => [0, 0];
                    node.hiddenWidgets?.add(widget.name);
                }
            }
        });
        
        // Clear dynamic widgets
        if (node.dynamicWidgets[axis]) {
            while (node.dynamicWidgets[axis].length > 0) {
                const widget = node.dynamicWidgets[axis].pop();
                const index = node.widgets.indexOf(widget);
                if (index > -1) {
                    node.widgets.splice(index, 1);
                }
            }
        }
        
        // Remove add button
        if (node.addButtons[axis]) {
            const index = node.widgets.indexOf(node.addButtons[axis]);
            if (index > -1) {
                node.widgets.splice(index, 1);
            }
            node.addButtons[axis] = null;
        }
    }
    
    // If type is "none", don't add any widgets
    if (type === "none") {
        return;
    }
    
    // Add widgets based on type
    if (needsTextWidget(type)) {
        const widgetName = `${axis}_${type}`;
        let existingWidget = node.widgets?.find(w => w.name === widgetName);
        
        if (!existingWidget) {
            const textWidget = ComfyWidgets.STRING(node, widgetName, ["STRING", {
                default: "",
                multiline: type === "prompt",
                placeholder: PARAM_HELP[type] || ""
            }]);
            node.textWidgets[axis] = textWidget.widget;
            
            // Set placeholder
            if (textWidget.widget.inputEl && PARAM_HELP[type]) {
                textWidget.widget.inputEl.placeholder = PARAM_HELP[type];
            }
        } else {
            existingWidget.hidden = false;
            existingWidget.computeSize = () => [node.size[0] - 20, 
                type === "prompt" ? LiteGraph.NODE_WIDGET_HEIGHT * 3 : LiteGraph.NODE_WIDGET_HEIGHT];
            node.hiddenWidgets?.delete(existingWidget.name);
            node.textWidgets[axis] = existingWidget;
        }
    } else if (needsDropdownWidget(type)) {
        // Add button for dynamic widgets
        if (!node.addButtons[axis]) {
            const buttonLabel = `➕ Add ${type.charAt(0).toUpperCase() + type.slice(1, -1)}`;
            const button = node.addWidget("button", buttonLabel, null, (value, canvas, node, pos, event) => {
                // Store event for context menu positioning
                window.lastButtonEvent = event || window.event;
                addDynamicWidget(node, axis, type);
            });
            node.addButtons[axis] = button;
        }
    }
}

// Helper function to check if type needs text widget
function needsTextWidget(type) {
    return ["cfg_scale", "steps", "seed", "denoise", "clip_skip", "prompt"].includes(type);
}

// Helper function to check if type needs dropdown widgets
function needsDropdownWidget(type) {
    return ["models", "vaes", "loras", "samplers", "schedulers"].includes(type);
}

// Cache for options to avoid repeated API calls
const optionsCache = {
    models: null,
    vaes: null,
    loras: null,
    samplers: null,
    schedulers: null
};

// Helper function to add dynamic widget
async function addDynamicWidget(node, axis, type) {
    // Get available options based on type - use cache if available
    let options = optionsCache[type];
    
    if (!options) {
        if (type === "models") {
            options = await getCheckpoints();
        } else if (type === "vaes") {
            options = await getVAEs();
        } else if (type === "loras") {
            options = await getLoRAs();
        } else if (type === "samplers") {
            options = await getSamplers();
        } else if (type === "schedulers") {
            options = await getSchedulers();
        }
        
        // Cache the results
        optionsCache[type] = options;
    }
    
    // Show selection dialog
    if (!options || options.length === 0) {
        alert(`No ${type} found`);
        return;
    }
    
    // Create context menu for selection
    const menu = new LiteGraph.ContextMenu(
        options,
        {
            event: window.lastButtonEvent || window.event,
            callback: (selectedValue) => {
                // Create dynamic widget with selected value
                const widget = new XYZDynamicWidget(
                    `${axis}_${type}_${widgetCounter++}`,
                    {
                        on: true,
                        value: selectedValue,
                        options: options,
                        _axis: axis,
                        _type: type
                    }
                );
                
                node.addCustomWidget(widget);
                node.dynamicWidgets[axis].push(widget);
                
                updateNodeTitle(node);
            }
        }
    );
}

// Helper function to update node title with count
function updateNodeTitle(node) {
    let xCount = 1, yCount = 1, zCount = 1;
    
    // Count values for each axis
    for (const axis of ['x', 'y', 'z']) {
        const typeWidget = node.widgets.find(w => w.name === `${axis}_type`);
        if (typeWidget && typeWidget.value !== "none") {
            const type = typeWidget.value;
            
            if (needsTextWidget(type)) {
                const textWidget = node.textWidgets[axis];
                if (textWidget && textWidget.value) {
                    const values = parseAxisValues(textWidget.value, type);
                    if (axis === 'x') xCount = values.length;
                    else if (axis === 'y') yCount = values.length;
                    else if (axis === 'z') zCount = values.length;
                }
            } else if (needsDropdownWidget(type)) {
                const enabledWidgets = node.dynamicWidgets[axis].filter(w => w.value.on);
                if (axis === 'x') xCount = Math.max(1, enabledWidgets.length);
                else if (axis === 'y') yCount = Math.max(1, enabledWidgets.length);
                else if (axis === 'z') zCount = Math.max(1, enabledWidgets.length);
            }
        }
    }
    
    const total = xCount * yCount * zCount;
    node.title = `XYZ Plot Controller (${total} images)`;
}

// Helper function to parse axis values
function parseAxisValues(text, type) {
    if (!text) return [];
    
    if (type === "prompt") {
        return text.split('\n').filter(line => line.trim());
    } else {
        // Handle comma-separated and range syntax
        const values = [];
        const parts = text.split(',').map(s => s.trim());
        
        for (const part of parts) {
            if (part.includes(':')) {
                // Range syntax: start:end:step
                const [start, end, step] = part.split(':').map(s => parseFloat(s));
                if (!isNaN(start) && !isNaN(end) && !isNaN(step) && step > 0) {
                    for (let v = start; v <= end; v += step) {
                        values.push(v);
                    }
                }
            } else {
                const val = parseFloat(part);
                if (!isNaN(val)) {
                    values.push(val);
                }
            }
        }
        
        return values;
    }
}

// Helper function to implement context menu
function implementContextMenu(node) {
    const originalGetSlotInPosition = node.getSlotInPosition;
    node.getSlotInPosition = function(x, y) {
        const slot = originalGetSlotInPosition ? originalGetSlotInPosition.call(this, x, y) : null;
        if (!slot) {
            const localX = x - this.pos[0];
            const localY = y - this.pos[1];
            
            for (const w of this.widgets || []) {
                if (w.type === "xyz_dynamic_widget" && w.y && 
                    localY > w.y && localY < w.y + LiteGraph.NODE_WIDGET_HEIGHT) {
                    if (w.nameBounds && localX >= w.nameBounds[0] && 
                        localX <= w.nameBounds[0] + w.nameBounds[1]) {
                        return { widget: w, output: { type: "XYZ_WIDGET" } };
                    }
                }
            }
        }
        return slot;
    };
    
    const originalGetSlotMenuOptions = node.getSlotMenuOptions;
    node.getSlotMenuOptions = function(slot) {
        if (slot?.output?.type === "XYZ_WIDGET") {
            const widget = slot.widget;
            const axis = widget.value._axis;
            const array = this.dynamicWidgets[axis];
            const currentIndex = array.indexOf(widget);
            
            const menuItems = [
                {
                    content: `${widget.value.on ? "⚫" : "🟢"} Toggle ${widget.value.on ? "Off" : "On"}`,
                    callback: () => {
                        widget.value.on = !widget.value.on;
                        this.setDirtyCanvas(true, true);
                        updateNodeTitle(this);
                    }
                },
                {
                    content: `⬆️ Move Up`,
                    disabled: currentIndex === 0,
                    callback: () => {
                        if (currentIndex > 0) {
                            [array[currentIndex - 1], array[currentIndex]] = 
                            [array[currentIndex], array[currentIndex - 1]];
                            
                            const widgetIndex = this.widgets.indexOf(widget);
                            const prevWidget = array[currentIndex];
                            const prevIndex = this.widgets.indexOf(prevWidget);
                            
                            if (widgetIndex > -1 && prevIndex > -1) {
                                [this.widgets[prevIndex], this.widgets[widgetIndex]] = 
                                [this.widgets[widgetIndex], this.widgets[prevIndex]];
                            }
                            
                            this.setDirtyCanvas(true, true);
                        }
                    }
                },
                {
                    content: `⬇️ Move Down`,
                    disabled: currentIndex === array.length - 1,
                    callback: () => {
                        if (currentIndex < array.length - 1) {
                            [array[currentIndex], array[currentIndex + 1]] = 
                            [array[currentIndex + 1], array[currentIndex]];
                            
                            const widgetIndex = this.widgets.indexOf(widget);
                            const nextWidget = array[currentIndex];
                            const nextIndex = this.widgets.indexOf(nextWidget);
                            
                            if (widgetIndex > -1 && nextIndex > -1) {
                                [this.widgets[widgetIndex], this.widgets[nextIndex]] = 
                                [this.widgets[nextIndex], this.widgets[widgetIndex]];
                            }
                            
                            this.setDirtyCanvas(true, true);
                        }
                    }
                },
                null, // Separator
                {
                    content: `🗑️ Remove`,
                    callback: () => {
                        // Remove from array
                        const index = array.indexOf(widget);
                        if (index > -1) {
                            array.splice(index, 1);
                        }
                        
                        // Remove widget
                        const wIndex = this.widgets.indexOf(widget);
                        if (wIndex > -1) {
                            this.widgets.splice(wIndex, 1);
                        }
                        
                        this.setDirtyCanvas(true, true);
                        updateNodeTitle(this);
                    }
                }
            ];
            
            new LiteGraph.ContextMenu(menuItems, {
                title: "WIDGET OPTIONS",
                event: app.canvas.last_mouse_event || window.event
            });
            
            return null;
        }
        
        return originalGetSlotMenuOptions ? originalGetSlotMenuOptions.call(this, slot) : null;
    };
}

// API helper functions
async function getCheckpoints() {
    try {
        // Get checkpoints from CheckpointLoaderSimple node definition
        const nodeData = await api.getNodeDefs();
        if (nodeData.CheckpointLoaderSimple && 
            nodeData.CheckpointLoaderSimple.input.required.ckpt_name) {
            return nodeData.CheckpointLoaderSimple.input.required.ckpt_name[0];
        }
    } catch (e) {
        console.error("Error getting checkpoints:", e);
    }
    return ["None"];
}

async function getVAEs() {
    try {
        // Get VAEs from VAELoader node definition
        const nodeData = await api.getNodeDefs();
        if (nodeData.VAELoader && 
            nodeData.VAELoader.input.required.vae_name) {
            return ["Automatic", ...nodeData.VAELoader.input.required.vae_name[0]];
        }
    } catch (e) {
        console.error("Error getting VAEs:", e);
    }
    return ["Automatic"];
}

async function getLoRAs() {
    try {
        // Get LoRAs from LoraLoader node definition
        const nodeData = await api.getNodeDefs();
        if (nodeData.LoraLoader && 
            nodeData.LoraLoader.input.required.lora_name) {
            return ["None", ...nodeData.LoraLoader.input.required.lora_name[0]];
        }
    } catch (e) {
        console.error("Error getting LoRAs:", e);
    }
    return ["None"];
}

async function getSamplers() {
    // Get samplers from KSampler node definition
    try {
        const nodeData = await api.getNodeDefs();
        if (nodeData.KSampler && nodeData.KSampler.input.required.sampler_name) {
            return nodeData.KSampler.input.required.sampler_name[0];
        }
    } catch {}
    return ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_sde", "dpmpp_2m", "dpmpp_3m_sde"];
}

async function getSchedulers() {
    // Get schedulers from KSampler node definition
    try {
        const nodeData = await api.getNodeDefs();
        if (nodeData.KSampler && nodeData.KSampler.input.required.scheduler) {
            return nodeData.KSampler.input.required.scheduler[0];
        }
    } catch {}
    return ["normal", "karras", "exponential", "simple", "ddim_uniform"];
}