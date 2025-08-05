# RGThree-Style Dynamic Widget Framework for ComfyUI

This document explains how to implement RGThree's Power Lora Loader-style dynamic widget system in your own ComfyUI nodes. This framework provides a clean UI with toggles, dynamic widget management, and proper persistence across page refreshes.

## Key Features

- **Dynamic widget addition/removal** - Users can add/remove items at runtime
- **Toggle switches** - Clean circular toggles instead of checkboxes
- **Strength controls** - Arrow buttons with editable values for fine control
- **Right-click context menus** - Only on the item name area
- **Full persistence** - All values persist across page refreshes
- **Hide/show widgets** - Proper cleanup when switching between types

## Core Implementation Pattern

### 1. Node Setup in JavaScript

```javascript
app.registerExtension({
    name: "YourExtension.YourNode",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "YourNodeName") {
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
                        category1: [],
                        category2: []
                    };
                }
                
                // Store references to buttons and text widgets
                if (!node.addButtons) {
                    node.addButtons = {};
                }
                if (!node.textWidgets) {
                    node.textWidgets = {};
                }
            };
        }
    }
});
```

### 2. Custom Widget Class

```javascript
class DynamicWidget {
    constructor(name, value) {
        this.name = name;
        this._value = value;
        this.type = "custom_dynamic_widget";
        this.y = 0;
        this.options = {};
        
        // Mouse tracking for drag operations
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
        // Return a deep copy to prevent modification
        return this._value ? { ...this._value } : null;
    }
    
    draw(ctx, node, width, y) {
        const margin = 10;
        const innerMargin = 3;
        const height = LiteGraph.NODE_WIDGET_HEIGHT;
        const midY = y + height / 2;
        let posX = margin;
        
        ctx.save();
        
        // Draw background
        ctx.fillStyle = "rgba(0,0,0,0.2)";
        ctx.beginPath();
        ctx.roundRect(posX, y + 2, width - margin * 2, height - 4, [height * 0.5]);
        ctx.fill();
        
        // Draw toggle (Power Lora style)
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
        
        this.toggleBounds = [posX, toggleBgWidth];
        posX += toggleBgWidth + innerMargin;
        
        // Apply opacity if disabled
        if (!this.value.on) {
            ctx.globalAlpha = app.canvas.editor_alpha * 0.4;
        }
        
        // Draw strength controls (if applicable)
        if (this.value.strength !== undefined) {
            let strengthX = width - margin - innerMargin;
            
            // Draw arrows and value
            // ... (implement arrow drawing as shown in xyz_plot_controller.js)
        }
        
        // Draw item name
        ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(this.value.name || "None", posX, midY);
        
        ctx.restore();
    }
    
    mouse(event, pos, node) {
        // Handle mouse events for toggle and controls
        if (event.type === "mousedown") {
            // Check toggle bounds
            if (pos[0] >= this.toggleBounds[0] && 
                pos[0] <= this.toggleBounds[0] + this.toggleBounds[1]) {
                this.value.on = !this.value.on;
                node.setDirtyCanvas(true, true);
                return true;
            }
            // Handle other controls...
        }
        return false;
    }
}
```

### 3. Configuration and Restoration

```javascript
// Override onConfigure for proper restoration
const onConfigure = nodeType.prototype.onConfigure;
nodeType.prototype.onConfigure = function(info) {
    // Mark as configured to prevent duplicate initialization
    this._configured = true;
    
    // Store widget values before ComfyUI modifies them
    const savedWidgetValues = [...(info.widgets_values || [])];
    
    // Clear tracking for fresh restoration
    if (!this.hiddenWidgets) {
        this.hiddenWidgets = new Set();
    }
    this.dynamicWidgets = { /* categories */ };
    this.addButtons = {};
    this.textWidgets = {};
    
    // Let ComfyUI restore base widgets
    if (onConfigure) {
        onConfigure.call(this, info);
    }
    
    // Restore dynamic widgets from saved values
    // ... (implement restoration logic)
    
    // Manually restore text widget values
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
};
```

### 4. Serialization Override

```javascript
// Override onSerialize to fix widget value persistence
const origOnSerialize = nodeType.prototype.onSerialize;
nodeType.prototype.onSerialize = function(info) {
    // Let ComfyUI serialize first
    if (origOnSerialize) {
        origOnSerialize.call(this, info);
    }
    
    // Fix empty text widget values
    if (info.widgets_values && this.widgets) {
        for (let i = 0; i < this.widgets.length && i < info.widgets_values.length; i++) {
            const widget = this.widgets[i];
            const serializedValue = info.widgets_values[i];
            
            // If serialized value is empty but widget has value, fix it
            if ((serializedValue === '' || serializedValue === null) && 
                widget && widget.value !== '' && widget.value !== null) {
                info.widgets_values[i] = widget.value;
            }
            
            // Also check inputEl for text widgets
            if (widget && widget.inputEl && widget.inputEl.value && 
                (serializedValue === '' || serializedValue === null)) {
                info.widgets_values[i] = widget.inputEl.value;
            }
        }
    }
};
```

### 5. Right-Click Context Menu

```javascript
// Override getSlotInPosition to detect clicks on widget areas
const originalGetSlotInPosition = node.getSlotInPosition;
node.getSlotInPosition = function(x, y) {
    const slot = originalGetSlotInPosition ? originalGetSlotInPosition.call(this, x, y) : null;
    if (!slot) {
        // Check if we clicked on a dynamic widget's name area
        const localX = x - this.pos[0];
        const localY = y - this.pos[1];
        
        for (const w of this.widgets || []) {
            if (w.type === "custom_dynamic_widget" && w.y && 
                localY > w.y && localY < w.y + LiteGraph.NODE_WIDGET_HEIGHT) {
                // Check if click is within name bounds
                if (w.nameBounds && localX >= w.nameBounds[0] && 
                    localX <= w.nameBounds[0] + w.nameBounds[1]) {
                    return { widget: w, output: { type: "DYNAMIC_WIDGET" } };
                }
            }
        }
    }
    return slot;
};

// Override getSlotMenuOptions for context menu
const originalGetSlotMenuOptions = node.getSlotMenuOptions;
node.getSlotMenuOptions = function(slot) {
    if (slot?.output?.type === "DYNAMIC_WIDGET") {
        const widget = slot.widget;
        
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
                disabled: !canMoveUp,
                callback: () => { /* implement move */ }
            },
            {
                content: `⬇️ Move Down`,
                disabled: !canMoveDown,
                callback: () => { /* implement move */ }
            },
            {
                content: `🗑️ Remove`,
                callback: () => { /* implement remove */ }
            }
        ];
        
        new LiteGraph.ContextMenu(menuItems, {
            title: "WIDGET OPTIONS",
            event: app.canvas.last_mouse_event || window.event
        });
        
        return null; // Prevent default menu
    }
    
    return originalGetSlotMenuOptions ? originalGetSlotMenuOptions.call(this, slot) : null;
};
```

### 6. Widget Visibility Management

```javascript
function updateWidgets(node, category, type, skipClear = false) {
    // Hide/show widgets instead of removing them
    if (!skipClear) {
        // Hide all widgets for this category
        node.widgets?.forEach(widget => {
            if (widget.name?.includes(category)) {
                widget.hidden = true;
                widget.computeSize = () => [0, 0];
                node.hiddenWidgets?.add(widget.name);
            }
        });
        
        // Clear dynamic widgets
        if (node.dynamicWidgets[category]) {
            while (node.dynamicWidgets[category].length > 0) {
                const widget = node.dynamicWidgets[category].pop();
                const index = node.widgets.indexOf(widget);
                if (index > -1) {
                    node.widgets.splice(index, 1);
                }
            }
        }
    }
    
    // Add or unhide widgets based on type
    if (needsTextWidget(type)) {
        const widgetName = `${category}_text`;
        let existingWidget = node.widgets?.find(w => w.name === widgetName);
        
        if (!existingWidget) {
            // Create new widget
            const textWidget = ComfyWidgets.STRING(node, widgetName, ["STRING", {
                default: "",
                multiline: true
            }]);
            node.textWidgets[category] = textWidget.widget;
        } else {
            // Unhide existing widget
            existingWidget.hidden = false;
            existingWidget.computeSize = () => [node.size[0] - 20, LiteGraph.NODE_WIDGET_HEIGHT];
            node.hiddenWidgets?.delete(existingWidget.name);
            node.textWidgets[category] = existingWidget;
        }
    }
}
```

## Best Practices

1. **Always use hide/show instead of remove/add** for text widgets to preserve values
2. **Track widget state** in dedicated objects (dynamicWidgets, textWidgets, etc.)
3. **Override serialization** to ensure ComfyUI properly saves widget values
4. **Use skipClear flags** during restoration to prevent widget clearing
5. **Implement proper mouse bounds checking** for custom controls
6. **Store metadata** (_axis, _type) with widget values for easier restoration
7. **Don't auto-resize nodes** - respect user's manual sizing

## Common Pitfalls to Avoid

1. **Don't remove widgets during configure** - this loses their values
2. **Don't rely on widget indices** - they can change
3. **Don't forget to handle inputEl** for text widgets
4. **Don't create widgets without checking if they exist** first
5. **Always deep copy values** when serializing to prevent modification

## Testing Checklist

- [ ] Widgets persist across page refresh
- [ ] Toggle states are maintained
- [ ] Strength/value controls work with click and drag
- [ ] Right-click menu only appears on name area
- [ ] Moving widgets up/down works correctly
- [ ] Removing widgets works without errors
- [ ] Switching between types doesn't leave artifacts
- [ ] All text input types persist (numbers, ranges, prompts)
- [ ] Hidden widgets don't take up visual space
- [ ] Widget values serialize correctly in workflow JSON

This framework provides a robust foundation for creating professional, user-friendly ComfyUI nodes with dynamic widget management that matches the quality of RGThree's implementations.