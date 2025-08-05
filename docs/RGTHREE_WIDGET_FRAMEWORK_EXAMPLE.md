# RGThree Widget Framework - Complete Example Implementation

This file provides a complete, working example of implementing the RGThree-style widget framework for a hypothetical "Advanced Sampler Controller" node.

## Complete Implementation Example

```javascript
// File: web/advanced_sampler_controller.js

import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Widget counter for unique names
let widgetCounter = 0;

// Custom dynamic widget class
class SamplerDynamicWidget {
    constructor(name, value) {
        this.name = name;
        this._value = value;
        this.type = "sampler_dynamic_widget";
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
        let posX = margin;
        
        ctx.save();
        
        // Background
        ctx.fillStyle = "rgba(0,0,0,0.2)";
        ctx.beginPath();
        ctx.roundRect(posX, y + 2, width - margin * 2, height - 4, [height * 0.5]);
        ctx.fill();
        
        // Toggle
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
        const toggleX = this.value.on ? posX + height : posX + height * 0.5;
        ctx.fillStyle = this.value.on ? "#89B" : "#888";
        ctx.beginPath();
        ctx.arc(toggleX, midY, toggleRadius, 0, Math.PI * 2);
        ctx.fill();
        
        // Store bounds for mouse interaction
        this.toggleBounds = [posX, toggleBgWidth];
        posX += toggleBgWidth + innerMargin;
        
        // Apply opacity if disabled
        if (!this.value.on) {
            ctx.globalAlpha = app.canvas.editor_alpha * 0.4;
        }
        
        // Strength controls and value
        let strengthX = width - margin - innerMargin;
        
        // Down arrow
        const arrowSize = 10;
        const arrowX = strengthX - arrowSize;
        
        ctx.fillStyle = "#666";
        ctx.beginPath();
        ctx.moveTo(arrowX + arrowSize/2, midY + 3);
        ctx.lineTo(arrowX + 2, midY - 3);
        ctx.lineTo(arrowX + arrowSize - 2, midY - 3);
        ctx.closePath();
        ctx.fill();
        
        this.downArrowBounds = [arrowX, arrowSize];
        strengthX = arrowX - innerMargin;
        
        // Up arrow
        const upArrowX = strengthX - arrowSize;
        ctx.beginPath();
        ctx.moveTo(upArrowX + arrowSize/2, midY - 3);
        ctx.lineTo(upArrowX + 2, midY + 3);
        ctx.lineTo(upArrowX + arrowSize - 2, midY + 3);
        ctx.closePath();
        ctx.fill();
        
        this.upArrowBounds = [upArrowX, arrowSize];
        strengthX = upArrowX - innerMargin;
        
        // Strength value
        const strengthText = this.value.strength.toFixed(2);
        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
        ctx.textAlign = "center";
        ctx.font = `${ctx.font}`;
        const textMetrics = ctx.measureText(strengthText);
        const strengthTextX = strengthX - textMetrics.width/2 - 4;
        
        // Draggable background
        ctx.fillStyle = "rgba(255,255,255,0.1)";
        ctx.beginPath();
        ctx.roundRect(strengthTextX - textMetrics.width/2 - 2, y + 4, 
                      textMetrics.width + 4, height - 8, [3]);
        ctx.fill();
        
        // Value text
        ctx.fillStyle = this.value.on ? "#FFF" : "#AAA";
        ctx.fillText(strengthText, strengthTextX, midY);
        
        this.strengthBounds = [strengthTextX - textMetrics.width/2 - 2, textMetrics.width + 4];
        
        // Name
        const nameX = posX;
        const maxNameWidth = strengthTextX - textMetrics.width/2 - nameX - 10;
        
        ctx.textAlign = "left";
        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
        
        // Clip long names
        const displayName = this.value.name || "None";
        let truncatedName = displayName;
        if (ctx.measureText(displayName).width > maxNameWidth) {
            while (truncatedName.length > 0 && 
                   ctx.measureText(truncatedName + "...").width > maxNameWidth) {
                truncatedName = truncatedName.slice(0, -1);
            }
            truncatedName += "...";
        }
        
        ctx.fillText(truncatedName, nameX, midY);
        
        // Store name bounds for right-click detection
        this.nameBounds = [nameX, ctx.measureText(truncatedName).width];
        
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
                return true;
            }
            
            // Up arrow
            if (localX >= this.upArrowBounds[0] && 
                localX <= this.upArrowBounds[0] + this.upArrowBounds[1]) {
                this.value.strength = Math.min(this.value.strength + 0.1, 10);
                node.setDirtyCanvas(true, true);
                return true;
            }
            
            // Down arrow
            if (localX >= this.downArrowBounds[0] && 
                localX <= this.downArrowBounds[0] + this.downArrowBounds[1]) {
                this.value.strength = Math.max(this.value.strength - 0.1, -10);
                node.setDirtyCanvas(true, true);
                return true;
            }
            
            // Strength drag start
            if (localX >= this.strengthBounds[0] && 
                localX <= this.strengthBounds[0] + this.strengthBounds[1]) {
                this.mouseState.dragging = true;
                this.mouseState.startX = pos[0];
                this.mouseState.startValue = this.value.strength;
                
                // Double-click detection
                const now = Date.now();
                if (now - this.mouseState.lastClickTime < 300) {
                    // Double-click - show input dialog
                    const newValue = prompt("Enter strength value:", this.value.strength);
                    if (newValue !== null && !isNaN(parseFloat(newValue))) {
                        this.value.strength = Math.max(-10, Math.min(10, parseFloat(newValue)));
                        node.setDirtyCanvas(true, true);
                    }
                    this.mouseState.dragging = false;
                }
                this.mouseState.lastClickTime = now;
                return true;
            }
        }
        else if (event.type === "mousemove" && this.mouseState.dragging) {
            const deltaX = pos[0] - this.mouseState.startX;
            const sensitivity = 0.01;
            this.value.strength = Math.max(-10, Math.min(10, 
                this.mouseState.startValue + deltaX * sensitivity));
            node.setDirtyCanvas(true, true);
            return true;
        }
        else if (event.type === "mouseup") {
            this.mouseState.dragging = false;
        }
        
        return false;
    }
    
    computeSize() {
        return [node.size[0], LiteGraph.NODE_WIDGET_HEIGHT];
    }
}

// Main extension registration
app.registerExtension({
    name: "Example.AdvancedSamplerController",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "AdvancedSamplerController") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                const node = this;
                
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Enable widget serialization
                this.serialize_widgets = true;
                
                // Initialize tracking
                this.hiddenWidgets = new Set();
                
                // Initialize storage
                if (!node.dynamicWidgets) {
                    node.dynamicWidgets = {
                        samplers: [],
                        schedulers: []
                    };
                }
                
                if (!node.addButtons) {
                    node.addButtons = {};
                }
                
                if (!node.textWidgets) {
                    node.textWidgets = {};
                }
                
                // Override configuration
                const onConfigure = nodeType.prototype.onConfigure;
                nodeType.prototype.onConfigure = function(info) {
                    this._configured = true;
                    
                    // Save widget values before ComfyUI modifies them
                    const savedWidgetValues = [...(info.widgets_values || [])];
                    
                    // Clear for fresh restoration
                    if (!this.hiddenWidgets) {
                        this.hiddenWidgets = new Set();
                    }
                    this.dynamicWidgets = {
                        samplers: [],
                        schedulers: []
                    };
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
                        if (value && typeof value === 'object' && value._type) {
                            const widget = new SamplerDynamicWidget(
                                `dynamic_${widgetCounter++}`,
                                value
                            );
                            this.addCustomWidget(widget);
                            
                            if (this.dynamicWidgets[value._type]) {
                                this.dynamicWidgets[value._type].push(widget);
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
                    if (this.widgets?.length > 0) {
                        const typeWidget = this.widgets.find(w => w.name === "sampler_type");
                        if (typeWidget) {
                            updateTypeWidgets(this, typeWidget.value, true);
                        }
                    }
                };
                
                // Override serialization
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
                
                // Widget change handlers
                const samplerWidget = this.widgets.find(w => w.name === "sampler_type");
                if (samplerWidget) {
                    const origCallback = samplerWidget.callback;
                    samplerWidget.callback = function() {
                        if (origCallback) {
                            origCallback.apply(this, arguments);
                        }
                        updateTypeWidgets(node, samplerWidget.value);
                    };
                }
            };
        }
    }
});

// Helper function to update widgets based on type
function updateTypeWidgets(node, type, skipClear = false) {
    if (!skipClear) {
        // Hide text widgets
        node.widgets?.forEach(widget => {
            if (widget.name?.includes("custom_values")) {
                widget.hidden = true;
                widget.computeSize = () => [0, 0];
                node.hiddenWidgets?.add(widget.name);
            }
        });
        
        // Clear dynamic widgets
        if (node.dynamicWidgets.samplers) {
            while (node.dynamicWidgets.samplers.length > 0) {
                const widget = node.dynamicWidgets.samplers.pop();
                const index = node.widgets.indexOf(widget);
                if (index > -1) {
                    node.widgets.splice(index, 1);
                }
            }
        }
    }
    
    // Add or unhide widgets based on type
    if (type === "custom") {
        const widgetName = "custom_values";
        let existingWidget = node.widgets?.find(w => w.name === widgetName);
        
        if (!existingWidget) {
            const textWidget = ComfyWidgets.STRING(node, widgetName, ["STRING", {
                default: "",
                multiline: true
            }]);
            node.textWidgets.custom = textWidget.widget;
        } else {
            existingWidget.hidden = false;
            existingWidget.computeSize = () => [node.size[0] - 20, LiteGraph.NODE_WIDGET_HEIGHT];
            node.hiddenWidgets?.delete(existingWidget.name);
            node.textWidgets.custom = existingWidget;
        }
    } else if (type === "samplers") {
        // Add button for samplers
        if (!node.addButtons.samplers) {
            const button = node.addWidget("button", "+ Add Sampler", null, () => {
                addDynamicWidget(node, "samplers");
            });
            node.addButtons.samplers = button;
        }
    }
}

// Helper function to add dynamic widgets
function addDynamicWidget(node, type) {
    const widget = new SamplerDynamicWidget(
        `dynamic_${widgetCounter++}`,
        {
            on: true,
            name: type === "samplers" ? "euler" : "normal",
            strength: 1.0,
            _type: type
        }
    );
    
    node.addCustomWidget(widget);
    node.dynamicWidgets[type].push(widget);
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
                if (w.type === "sampler_dynamic_widget" && w.y && 
                    localY > w.y && localY < w.y + LiteGraph.NODE_WIDGET_HEIGHT) {
                    if (w.nameBounds && localX >= w.nameBounds[0] && 
                        localX <= w.nameBounds[0] + w.nameBounds[1]) {
                        return { widget: w, output: { type: "SAMPLER_WIDGET" } };
                    }
                }
            }
        }
        return slot;
    };
    
    const originalGetSlotMenuOptions = node.getSlotMenuOptions;
    node.getSlotMenuOptions = function(slot) {
        if (slot?.output?.type === "SAMPLER_WIDGET") {
            const widget = slot.widget;
            const arrayName = widget.value._type;
            const array = this.dynamicWidgets[arrayName];
            const currentIndex = array.indexOf(widget);
            
            const menuItems = [
                {
                    content: `${widget.value.on ? "⚫" : "🟢"} Toggle ${widget.value.on ? "Off" : "On"}`,
                    callback: () => {
                        widget.value.on = !widget.value.on;
                        this.setDirtyCanvas(true, true);
                    }
                },
                {
                    content: `⬆️ Move Up`,
                    disabled: currentIndex === 0,
                    callback: () => {
                        if (currentIndex > 0) {
                            // Swap in array
                            [array[currentIndex - 1], array[currentIndex]] = 
                            [array[currentIndex], array[currentIndex - 1]];
                            
                            // Swap in widgets
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
                            // Swap in array
                            [array[currentIndex], array[currentIndex + 1]] = 
                            [array[currentIndex + 1], array[currentIndex]];
                            
                            // Swap in widgets
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
                    }
                }
            ];
            
            new LiteGraph.ContextMenu(menuItems, {
                title: "SAMPLER OPTIONS",
                event: app.canvas.last_mouse_event || window.event
            });
            
            return null;
        }
        
        return originalGetSlotMenuOptions ? originalGetSlotMenuOptions.call(this, slot) : null;
    };
}
```

## Python Node Definition

```python
# File: kikotools/tools/advanced_sampler_controller/node.py

class AdvancedSamplerController:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "sampler_type": (["samplers", "custom", "schedulers"], {
                    "default": "samplers"
                }),
                "enabled": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "custom_values": ("STRING", {"multiline": True, "default": ""}),
            }
        }
    
    RETURN_TYPES = ("SAMPLER_CONFIG",)
    RETURN_NAMES = ("config",)
    FUNCTION = "process"
    CATEGORY = "ComfyAssets"
    
    def process(self, sampler_type, enabled, custom_values="", **kwargs):
        config = {
            "type": sampler_type,
            "enabled": enabled,
            "samplers": [],
            "custom": custom_values
        }
        
        # Process dynamic widgets
        for key, value in kwargs.items():
            if isinstance(value, dict) and value.get("_type") == "samplers":
                if value.get("on", False):
                    config["samplers"].append({
                        "name": value.get("name"),
                        "strength": value.get("strength", 1.0)
                    })
        
        return (config,)
```

## Key Implementation Points

1. **Widget Class Design**
   - Custom widget class with proper value getter/setter
   - `serializeValue` method for persistence
   - Complete `draw` and `mouse` methods
   - Proper bounds tracking for all interactive elements

2. **Node Setup**
   - `serialize_widgets = true` in onNodeCreated
   - Tracking objects for dynamic widgets, buttons, and text widgets
   - Hidden widgets set for visibility management

3. **Configuration Override**
   - Save widget values before ComfyUI modifies them
   - Clear tracking objects for fresh restoration
   - Restore dynamic widgets from saved values
   - Manually restore text widget values

4. **Serialization Override**
   - Fix empty text widget values
   - Check both widget.value and widget.inputEl.value
   - Ensure all widget types persist correctly

5. **Context Menu Implementation**
   - Override getSlotInPosition to detect widget clicks
   - Check name bounds for right-click detection
   - Return custom slot type for menu trigger
   - Override getSlotMenuOptions for menu items

6. **Widget Management**
   - Hide/show pattern instead of remove/add
   - Proper cleanup when switching types
   - Dynamic widget arrays for organization
   - Button widgets for adding new items

## Testing Your Implementation

1. **Create Test Workflow**
   ```json
   {
     "nodes": [{
       "type": "AdvancedSamplerController",
       "widgets_values": [
         "samplers",
         true,
         "",
         {
           "on": true,
           "name": "euler",
           "strength": 0.8,
           "_type": "samplers"
         }
       ]
     }]
   }
   ```

2. **Test Checklist**
   - [ ] Add dynamic widgets with button
   - [ ] Toggle on/off states persist
   - [ ] Strength values persist after refresh
   - [ ] Right-click menu only on name area
   - [ ] Move up/down works correctly
   - [ ] Remove widget works
   - [ ] Switch types doesn't leave artifacts
   - [ ] Text values persist
   - [ ] Double-click to edit strength works

3. **Debug Tips**
   - Add console.log in key methods
   - Check browser console for errors
   - Verify widget array contents
   - Test with workflow JSON export/import

This complete example demonstrates all aspects of the RGThree widget framework and can be adapted for any custom node that needs dynamic widget management with professional UI/UX.