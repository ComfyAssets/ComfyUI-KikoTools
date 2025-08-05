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

// Helper function to fit string with ellipsis
function fitString(ctx, str, maxWidth) {
    let width = ctx.measureText(str).width;
    const ellipsis = "…";
    const ellipsisWidth = ctx.measureText(ellipsis).width;
    if (width <= maxWidth || width <= ellipsisWidth) {
        return str;
    }
    
    // Binary search for the right length
    let min = 0;
    let max = str.length;
    while (min <= max) {
        let guess = Math.floor((min + max) / 2);
        width = ctx.measureText(str.substring(0, guess)).width;
        if (width + ellipsisWidth === maxWidth) {
            return str.substring(0, guess) + ellipsis;
        }
        if (width + ellipsisWidth < maxWidth) {
            min = guess + 1;
        } else {
            max = guess - 1;
        }
    }
    return str.substring(0, max) + ellipsis;
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

// Draw number widget with arrows
function drawNumberWidgetPart(ctx, options) {
    const arrowWidth = 9;
    const arrowHeight = 10;
    const innerMargin = 3;
    const numberWidth = 32;
    const xBoundsArrowLess = [0, 0];
    const xBoundsNumber = [0, 0];
    const xBoundsArrowMore = [0, 0];
    
    ctx.save();
    let posX = options.posX;
    const { posY, height, value, textColor } = options;
    const midY = posY + height / 2;
    
    if (options.direction === -1) {
        posX = posX - arrowWidth - innerMargin - numberWidth - innerMargin - arrowWidth;
    }
    
    // Draw left arrow (decrease)
    ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
    ctx.fill(new Path2D(`M ${posX} ${midY} l ${arrowWidth} ${arrowHeight / 2} l 0 -${arrowHeight} L ${posX} ${midY} z`));
    xBoundsArrowLess[0] = posX;
    xBoundsArrowLess[1] = arrowWidth;
    posX += arrowWidth + innerMargin;
    
    // Draw number
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const oldTextcolor = ctx.fillStyle;
    if (textColor) {
        ctx.fillStyle = textColor;
    }
    ctx.fillText(fitString(ctx, value.toFixed(2), numberWidth), posX + numberWidth / 2, midY);
    ctx.fillStyle = oldTextcolor;
    xBoundsNumber[0] = posX;
    xBoundsNumber[1] = numberWidth;
    posX += numberWidth + innerMargin;
    
    // Draw right arrow (increase)
    ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
    ctx.fill(new Path2D(`M ${posX} ${midY - arrowHeight / 2} l ${arrowWidth} ${arrowHeight / 2} l -${arrowWidth} ${arrowHeight / 2} v -${arrowHeight} z`));
    xBoundsArrowMore[0] = posX;
    xBoundsArrowMore[1] = arrowWidth;
    
    ctx.restore();
    return [xBoundsArrowLess, xBoundsNumber, xBoundsArrowMore];
}
drawNumberWidgetPart.WIDTH_TOTAL = 9 + 3 + 32 + 3 + 9;

// Base widget class for XYZ selections
class XYZBaseWidget {
    constructor(name) {
        this.name = name;
        this.type = "custom";
        this.last_y = 0;
        this.y = 0;
        this.hitAreas = {};
    }
    
    computeSize(width) {
        return [width || 300, LiteGraph.NODE_WIDGET_HEIGHT];
    }
    
    // Base draw method
    draw(ctx, node, width, posY, height) {
        // To be overridden
    }
    
    // Base serialization
    serializeValue(node, index) {
        // Make sure we return a full copy of the value
        return this.value ? {...this.value} : null;
    }
    
    mouse(event, pos, node) {
        if (event.type === "pointerdown") {
            const localX = pos[0];
            
            // Check all hit areas
            for (const [key, area] of Object.entries(this.hitAreas)) {
                if (area.bounds && area.bounds[0] !== undefined && area.bounds[1] !== undefined) {
                    if (localX >= area.bounds[0] && localX <= area.bounds[0] + area.bounds[1]) {
                        if (area.onDown) {
                            return area.onDown.call(this, event, pos, node);
                        }
                    }
                }
            }
        }
        return false;
    }
}

// Widget for displaying selected items with toggle
class XYZSelectionWidget extends XYZBaseWidget {
    constructor(name) {
        super(name);
        this.value = {
            on: true,
            value: null,
            strength: 1.0,
            _axis: null,
            _type: null
        };
        
        this.hitAreas = {
            toggle: { bounds: [0, 0], onDown: this.onToggleDown },
            value: { bounds: [0, 0], onDown: this.onValueClick },
            strengthDec: { bounds: [0, 0], onDown: this.onStrengthDec },
            strengthVal: { bounds: [0, 0], onDown: this.onStrengthVal },
            strengthInc: { bounds: [0, 0], onDown: this.onStrengthInc }
        };
        
        this.lastClickTime = 0;
    }
    
    draw(ctx, node, width, posY) {
        const margin = 10;
        const innerMargin = 3;
        const height = LiteGraph.NODE_WIDGET_HEIGHT;
        const midY = posY + height / 2;
        const lowQuality = isLowQuality();
        let posX = margin;
        
        ctx.save();
        
        // Background - skip complex drawing in low quality
        if (!lowQuality) {
            ctx.fillStyle = "rgba(0,0,0,0.2)";
            ctx.beginPath();
            ctx.roundRect(posX, posY + 2, width - margin * 2, height - 4, [height * 0.5]);
            ctx.fill();
        }
        
        // Draw toggle
        const toggleResult = drawTogglePart(ctx, { posX, posY, height, value: this.value.on });
        this.hitAreas.toggle.bounds = toggleResult;
        posX += toggleResult[1] + innerMargin;
        
        if (lowQuality) {
            ctx.restore();
            return;
        }
        
        // Apply opacity if disabled
        if (!this.value.on) {
            ctx.globalAlpha = app.canvas.editor_alpha * 0.4;
        }
        
        // Calculate space for strength controls if lora
        let maxTextWidth = width - posX - margin;
        if (this.value._type === "loras") {
            maxTextWidth -= drawNumberWidgetPart.WIDTH_TOTAL + innerMargin * 2;
        }
        
        // Draw value text
        const valueText = String(this.value.value || "None");
        
        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        
        const displayText = fitString(ctx, valueText, maxTextWidth);
        ctx.fillText(displayText, posX, midY);
        
        this.hitAreas.value.bounds = [posX, ctx.measureText(displayText).width];
        
        // Draw strength controls for loras
        if (this.value._type === "loras" && this.value.value && this.value.value !== "None") {
            const [leftArrow, numberBounds, rightArrow] = drawNumberWidgetPart(ctx, {
                posX: width - margin - innerMargin,
                posY: posY,
                height: height,
                value: this.value.strength || 1.0,
                direction: -1
            });
            
            this.hitAreas.strengthDec.bounds = leftArrow;
            this.hitAreas.strengthVal.bounds = numberBounds;
            this.hitAreas.strengthInc.bounds = rightArrow;
        } else {
            // Clear strength hit areas
            this.hitAreas.strengthDec.bounds = [0, 0];
            this.hitAreas.strengthVal.bounds = [0, 0];
            this.hitAreas.strengthInc.bounds = [0, 0];
        }
        
        ctx.restore();
    }
    
    onToggleDown(event, pos, node) {
        this.value.on = !this.value.on;
        node.setDirtyCanvas(true, true);
        updateNodeTitle(node);
        return true;
    }
    
    async onValueClick(event, pos, node) {
        const type = this.value._type;
        const axis = this.value._axis;
        
        // Get options based on type
        const options = await getOptionsForType(type);
        
        if (options && options.length > 0) {
            new LiteGraph.ContextMenu(
                options,
                {
                    event: event,
                    title: `Choose ${type}`,
                    callback: (value) => {
                        this.value.value = value;
                        node.setDirtyCanvas(true, true);
                    }
                }
            );
        }
        
        return true;
    }
    
    onStrengthDec(event, pos, node) {
        if (this.value.strength > 0) {
            this.value.strength = Math.max(0, this.value.strength - 0.1);
            node.setDirtyCanvas(true, true);
        }
        return true;
    }
    
    onStrengthInc(event, pos, node) {
        if (this.value.strength < 2) {
            this.value.strength = Math.min(2, this.value.strength + 0.1);
            node.setDirtyCanvas(true, true);
        }
        return true;
    }
    
    onStrengthVal(event, pos, node) {
        // Check for double-click
        const currentTime = Date.now();
        if (this.lastClickTime && currentTime - this.lastClickTime < 300) {
            // Double-click detected - use LiteGraph's prompt for float input
            const currentValue = this.value.strength || 1.0;
            
            app.canvas.prompt("Strength", currentValue.toFixed(2), (value) => {
                if (value !== null && value !== undefined) {
                    const parsed = parseFloat(value);
                    if (!isNaN(parsed)) {
                        this.value.strength = Math.max(0, Math.min(2, parsed));
                        node.setDirtyCanvas(true, true);
                    }
                }
            }, event);
        }
        this.lastClickTime = currentTime;
        return true;
    }
}

// Button widget for adding new selections
class XYZAddButton extends XYZBaseWidget {
    constructor(name, type, axis) {
        super(name);
        this.type = "xyz_button";  // Use custom type to avoid conflicts
        this._type = type;
        this._axis = axis;
        this.value = null;
        this.serialize = false;  // Prevent serialization
    }
    
    serializeValue(node, index) {
        // Don't serialize button widgets - return a special marker
        return null;
    }
    
    draw(ctx, node, width, posY) {
        const margin = 10;
        const height = LiteGraph.NODE_WIDGET_HEIGHT;
        const lowQuality = isLowQuality();
        
        ctx.save();
        
        // Button background
        ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
        ctx.strokeStyle = lowQuality ? "transparent" : LiteGraph.WIDGET_OUTLINE_COLOR;
        
        ctx.beginPath();
        ctx.roundRect(margin, posY, width - margin * 2, height, lowQuality ? [0] : [4]);
        ctx.fill();
        if (!lowQuality) {
            ctx.stroke();
        }
        
        // Button text
        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        
        const label = this.name || `➕ Add ${this._type.charAt(0).toUpperCase() + this._type.slice(1, -1)}`;
        ctx.fillText(label, width / 2, posY + height / 2);
        
        ctx.restore();
    }
    
    mouse(event, pos, node) {
        if (event.type === "pointerdown") {
            this.onButtonClick(event, pos, node);
            return true;
        }
        return false;
    }
    
    async onButtonClick(event, pos, node) {
        const options = await getOptionsForType(this._type);
        
        if (!options || options.length === 0) {
            alert(`No ${this._type} found`);
            return;
        }
        
        new LiteGraph.ContextMenu(
            options,
            {
                event: event,
                title: `Choose ${this._type}`,
                callback: (value) => {
                    if (value !== "None" && value !== "Automatic") {
                        // Add new selection widget
                        const widget = new XYZSelectionWidget(`${this._axis}_${this._type}_${widgetCounter++}`);
                        // Ensure we properly copy the existing value structure
                        widget.value = {
                            on: true,
                            value: value,
                            strength: 1.0,
                            _axis: this._axis,
                            _type: this._type
                        };
                        
                        node.addCustomWidget(widget);
                        
                        // Store in dynamic widgets
                        if (!node.dynamicWidgets[this._axis]) {
                            node.dynamicWidgets[this._axis] = [];
                        }
                        node.dynamicWidgets[this._axis].push(widget);
                        
                        // Move button to end
                        const buttonIndex = node.widgets.indexOf(this);
                        if (buttonIndex > -1) {
                            node.widgets.splice(buttonIndex, 1);
                            node.widgets.push(this);
                        }
                        
                        updateNodeTitle(node);
                    }
                }
            }
        );
    }
}

// Cache for options
const optionsCache = {};

// Get options based on type
async function getOptionsForType(type) {
    if (optionsCache[type]) {
        return optionsCache[type];
    }
    
    let options = [];
    
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
    
    optionsCache[type] = options;
    return options;
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
                
                // Remove the onSerialize override - let ComfyUI handle it with proper serializeValue methods
                
                // Initialize storage
                if (!node.dynamicWidgets) {
                    node.dynamicWidgets = {
                        x: [],
                        y: [],
                        z: []
                    };
                }
                
                if (!node.addButtons) {
                    node.addButtons = {};
                }
                
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
                            // Defer widget update to next tick to ensure node is ready
                            setTimeout(() => {
                                    updateAxisWidgets(node, widgetName.split("_")[0], value);
                                updateNodeTitle(node);
                            }, 0);
                        };
                    }
                });
                
                // Pre-fetch common options
                setTimeout(() => {
                    getSamplers();
                    getSchedulers();
                }, 100);
                
                // Override configuration for proper restoration
                const onConfigure = nodeType.prototype.onConfigure;
                nodeType.prototype.onConfigure = function(info) {
                    
                    // Remove only custom widgets, keep base widgets
                    const baseWidgetNames = ['x_type', 'y_type', 'z_type', 'auto_queue'];
                    const toRemove = [];
                    
                    for (const w of this.widgets || []) {
                        if (!baseWidgetNames.includes(w.name)) {
                            toRemove.push(w);
                        }
                    }
                    
                    for (const w of toRemove) {
                        const idx = this.widgets.indexOf(w);
                        if (idx !== -1) {
                            this.widgets.splice(idx, 1);
                        }
                    }
                    
                    // Reset storage
                    this.dynamicWidgets = { x: [], y: [], z: [] };
                    this.addButtons = {};
                    this.textWidgets = {};
                    
                    // Call parent configure to restore base widget values
                    if (onConfigure) {
                        onConfigure.call(this, info);
                    }
                    
                    // Now restore dynamic widgets
                    if (info.widgets_values) {
                        
                        // Count base widgets to know where dynamic values start
                        let baseWidgetCount = 0;
                        for (const w of this.widgets) {
                            if (baseWidgetNames.includes(w.name)) {
                                baseWidgetCount++;
                            }
                        }
                        
                        // Group widgets by axis
                        const widgetsByAxis = { x: [], y: [], z: [] };
                        
                        // Collect all widgets first
                        for (let i = baseWidgetCount; i < info.widgets_values.length; i++) {
                            const value = info.widgets_values[i];
                            
                            if (value && typeof value === 'object' && value._axis && value._type) {
                                widgetsByAxis[value._axis].push(value);
                            }
                        }
                        
                        // Now restore widgets grouped by axis, with buttons after each group
                        for (const axis of ['x', 'y', 'z']) {
                            const typeWidget = this.widgets.find(w => w.name === `${axis}_type`);
                            const axisType = typeWidget ? typeWidget.value : 'none';
                            
                            if (axisType !== 'none' && needsDropdownWidget(axisType)) {
                                const axisWidgets = widgetsByAxis[axis];
                                
                                // Restore all widgets for this axis
                                for (const widgetData of axisWidgets) {
                                    const widget = new XYZSelectionWidget(`${axis}_${widgetData._type}_${widgetCounter++}`);
                                    widget.value = { ...widgetData };
                                    this.addCustomWidget(widget);
                                    
                                    if (!this.dynamicWidgets[axis]) {
                                        this.dynamicWidgets[axis] = [];
                                    }
                                    this.dynamicWidgets[axis].push(widget);
                                }
                                
                                // Add button for this axis
                                if (axisWidgets.length > 0 || axisType) {
                                    const buttonLabel = `➕ Add ${axisType.charAt(0).toUpperCase() + axisType.slice(1, -1)}`;
                                    const button = new XYZAddButton(buttonLabel, axisType, axis);
                                    this.addCustomWidget(button);
                                    this.addButtons[axis] = button;
                                }
                            }
                        }
                    }
                    
                    updateNodeTitle(this);
                };
                
                // Override getSlotInPosition to return widget as a fake slot
                const originalGetSlotInPosition = node.getSlotInPosition;
                node.getSlotInPosition = function(canvasX, canvasY) {
                    // First check the normal slots
                    const slot = originalGetSlotInPosition ? originalGetSlotInPosition.call(this, canvasX, canvasY) : null;
                    if (slot) {
                        return slot;
                    }
                    
                    // Check if we clicked on a widget
                    let lastWidget = null;
                    for (const widget of this.widgets) {
                        if (!widget.last_y) continue;
                        if (canvasY > this.pos[1] + widget.last_y) {
                            lastWidget = widget;
                            continue;
                        }
                        break;
                    }
                    
                    // If we found a widget and it's one of ours, return a fake slot
                    if (lastWidget instanceof XYZSelectionWidget) {
                        return { widget: lastWidget, output: { type: "XYZ_WIDGET" } };
                    }
                    
                    return null;
                };
                
                // Override getSlotMenuOptions for right-click menu
                const originalGetSlotMenuOptions = node.getSlotMenuOptions;
                node.getSlotMenuOptions = function(slot) {
                    // Check if slot has a widget and it's one of ours
                    if (slot?.widget instanceof XYZSelectionWidget) {
                        const widget = slot.widget;
                        const axis = widget.value._axis;
                        const array = this.dynamicWidgets[axis];
                        const currentIndex = array.indexOf(widget);
                            
                            return [
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
                                        const index = array.indexOf(widget);
                                        if (index > -1) {
                                            array.splice(index, 1);
                                        }
                                        
                                        const wIndex = this.widgets.indexOf(widget);
                                        if (wIndex > -1) {
                                            this.widgets.splice(wIndex, 1);
                                        }
                                        
                                        this.setDirtyCanvas(true, true);
                                        updateNodeTitle(this);
                                    }
                                }
                            ];
                    }
                    
                    return originalGetSlotMenuOptions ? originalGetSlotMenuOptions.call(this, slot) : null;
                };
            };
        }
    }
});

// Helper function to update widgets based on axis type
function updateAxisWidgets(node, axis, type, skipClear = false) {
    console.log(`updateAxisWidgets called: axis=${axis}, type=${type}, skipClear=${skipClear}`);
    console.log("Current widgets:", node.widgets.map(w => ({ name: w.name, type: w.type })));
    
    if (!skipClear) {
        // Remove ALL widgets for this axis - be very thorough
        const widgetsToRemove = [];
        
        // Find all widgets that belong to this axis
        for (const widget of node.widgets) {
            // Skip base widgets
            if (['x_type', 'y_type', 'z_type', 'auto_queue'].includes(widget.name)) {
                continue;
            }
            
            // Log widget details for debugging
            console.log(`Checking widget: name="${widget.name}", type="${widget.type}", axis="${axis}"`);
            
            // Check if it's a dynamic widget for this axis
            if (node.dynamicWidgets[axis] && node.dynamicWidgets[axis].includes(widget)) {
                console.log("  -> Found as dynamic widget");
                widgetsToRemove.push(widget);
            }
            
            // Check if it's the add button for this axis
            if (node.addButtons[axis] === widget) {
                console.log("  -> Found as add button");
                widgetsToRemove.push(widget);
            }
            
            // Check if it's a text widget for this axis
            if (node.textWidgets[axis] === widget) {
                console.log("  -> Found as text widget");
                widgetsToRemove.push(widget);
            }
            
            // Check by name pattern
            const axisPatterns = [
                `${axis}_prompt`, `${axis}_cfg_scale`, `${axis}_steps`,
                `${axis}_seed`, `${axis}_denoise`, `${axis}_clip_skip`
            ];
            if (widget.name && axisPatterns.includes(widget.name)) {
                console.log("  -> Found by name pattern");
                widgetsToRemove.push(widget);
            }
            
            // Check if widget name starts with axis
            if (widget.name && widget.name.startsWith(`${axis}_`)) {
                console.log("  -> Found by axis prefix");
                widgetsToRemove.push(widget);
            }
            
            // Special check for text widgets that might not have proper names
            if ((widget.type === 'text' || widget.type === 'customtext') && widget.inputEl && 
                widget.inputEl.placeholder && widget.inputEl.placeholder.includes("prompt")) {
                console.log("  -> Found prompt widget by placeholder text");
                widgetsToRemove.push(widget);
            }
        }
        
        // Remove all found widgets (remove duplicates first)
        const uniqueWidgets = [...new Set(widgetsToRemove)];
        console.log(`Removing ${uniqueWidgets.length} widgets for axis ${axis}:`, uniqueWidgets.map(w => w.name));
        
        // Remove in reverse order to avoid index issues
        for (let i = node.widgets.length - 1; i >= 0; i--) {
            const widget = node.widgets[i];
            if (uniqueWidgets.includes(widget)) {
                // Remove DOM element if it exists
                if (widget.inputEl && widget.inputEl.parentNode) {
                    widget.inputEl.parentNode.removeChild(widget.inputEl);
                }
                // Call onRemoved callback if it exists
                if (widget.onRemoved) {
                    widget.onRemoved();
                }
                // Remove from widgets array
                node.widgets.splice(i, 1);
            }
        }
        
        // Clear references
        node.dynamicWidgets[axis] = [];
        node.addButtons[axis] = null;
        node.textWidgets[axis] = null;
        
        // Force canvas redraw and recalculate size
        node.setDirtyCanvas(true, true);
        const size = node.computeSize();
        node.size[1] = size[1];
    }
    
    // If type is "none", don't add any widgets
    if (type === "none") {
        return;
    }
    
    // Add widgets based on type
    if (needsTextWidget(type)) {
        const widgetName = `${axis}_${type}`;
        
        // Check if widget already exists
        const existingWidget = node.widgets.find(w => w.name === widgetName);
        if (!existingWidget) {
            console.log(`Creating text widget: ${widgetName}`);
            console.log("Widgets before creation:", node.widgets.length);
            
            const textWidget = ComfyWidgets.STRING(node, widgetName, ["STRING", {
                default: "",
                multiline: type === "prompt",
                placeholder: PARAM_HELP[type] || ""
            }]);
            
            console.log("Widgets after creation:", node.widgets.length);
            console.log("All widget names:", node.widgets.map(w => w.name));
            
            // Find the actual widget that was added - get the last one with this name
            const matchingWidgets = node.widgets.filter(w => w.name === widgetName);
            const addedWidget = matchingWidgets[matchingWidgets.length - 1];
            
            if (addedWidget) {
                node.textWidgets[axis] = addedWidget;
                console.log(`Text widget created and stored: ${widgetName}`);
                
                // Set placeholder
                if (addedWidget.inputEl && PARAM_HELP[type]) {
                    addedWidget.inputEl.placeholder = PARAM_HELP[type];
                }
            }
        } else {
            console.log(`Text widget already exists: ${widgetName}`);
            node.textWidgets[axis] = existingWidget;
        }
    } else if (needsDropdownWidget(type)) {
        // Only add button if not already present
        if (!node.addButtons[axis]) {
            const buttonLabel = `➕ Add ${type.charAt(0).toUpperCase() + type.slice(1, -1)}`;
            const button = new XYZAddButton(buttonLabel, type, axis);
            // Make sure widget is added at the end
            const index = node.widgets.length;
            node.addCustomWidget(button);
            // Move to proper position if needed
            if (node.widgets[index] !== button) {
                const actualIndex = node.widgets.indexOf(button);
                if (actualIndex > -1) {
                    node.widgets.splice(actualIndex, 1);
                    node.widgets.push(button);
                }
            }
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
                const enabledWidgets = (node.dynamicWidgets[axis] || []).filter(w => w.value.on);
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

// API helper functions
async function getCheckpoints() {
    try {
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
    try {
        const nodeData = await api.getNodeDefs();
        if (nodeData.KSampler && nodeData.KSampler.input.required.sampler_name) {
            return nodeData.KSampler.input.required.sampler_name[0];
        }
    } catch {}
    return ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_sde", "dpmpp_2m", "dpmpp_3m_sde"];
}

async function getSchedulers() {
    try {
        const nodeData = await api.getNodeDefs();
        if (nodeData.KSampler && nodeData.KSampler.input.required.scheduler) {
            return nodeData.KSampler.input.required.scheduler[0];
        }
    } catch {}
    return ["normal", "karras", "exponential", "simple", "ddim_uniform"];
}