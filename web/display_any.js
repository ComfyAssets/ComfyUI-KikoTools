import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "ComfyAssets.DisplayAny",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DisplayAny") {
            const onExecuted = nodeType.prototype.onExecuted;
            
            nodeType.prototype.onExecuted = function(message) {
                onExecuted?.apply(this, arguments);
                
                if (message?.text && message.text.length > 0) {
                    const displayText = message.text[0];
                    // Update the display widget with the value
                    this.updateDisplay(displayText);
                    
                    // Also show a condensed version in the title
                    const condensed = displayText.length > 20 
                        ? displayText.substring(0, 20) + "..." 
                        : displayText;
                    this.title = `DisplayAny: ${condensed}`;
                }
            };
            
            nodeType.prototype.updateDisplay = function(text) {
                // Remove existing display widget if any
                const existingWidget = this.widgets?.find(w => w.name === "display_value");
                if (existingWidget) {
                    const index = this.widgets.indexOf(existingWidget);
                    this.widgets.splice(index, 1);
                }
                
                // Create display widget
                const widget = {
                    type: "custom_display",
                    name: "display_value",
                    size: [this.size[0] - 20, 80],
                    displayText: text,
                    
                    draw: function(ctx, node, widget_width, y, H) {
                        const margin = 10;
                        const padding = 10;
                        const lineHeight = 16;
                        const minHeight = 60;
                        
                        // Calculate needed height based on text
                        ctx.font = "12px monospace";
                        const lines = this.displayText ? this.displayText.split('\n') : [""];
                        const textHeight = Math.max(minHeight, lines.length * lineHeight + padding * 2);
                        
                        // Draw background
                        ctx.fillStyle = "#2a2a2a";
                        ctx.fillRect(margin, y, widget_width - margin * 2, textHeight);
                        
                        // Draw border
                        ctx.strokeStyle = "#444";
                        ctx.strokeRect(margin, y, widget_width - margin * 2, textHeight);
                        
                        // Draw text area background
                        ctx.fillStyle = "#1e1e1e";
                        ctx.fillRect(margin + 1, y + 1, widget_width - margin * 2 - 2, textHeight - 2);
                        
                        // Prepare text
                        ctx.fillStyle = "#ddd";
                        ctx.textAlign = "left";
                        ctx.textBaseline = "top";
                        
                        // Draw each line
                        const maxWidth = widget_width - margin * 2 - padding * 2;
                        let currentY = y + padding;
                        
                        for (let i = 0; i < lines.length && i < 3; i++) { // Show max 3 lines
                            let line = lines[i];
                            const metrics = ctx.measureText(line);
                            
                            if (metrics.width > maxWidth) {
                                // Truncate line to fit
                                while (ctx.measureText(line + "...").width > maxWidth && line.length > 0) {
                                    line = line.slice(0, -1);
                                }
                                line = line + "...";
                            }
                            
                            ctx.fillText(line, margin + padding, currentY);
                            currentY += lineHeight;
                        }
                        
                        if (lines.length > 3) {
                            ctx.fillStyle = "#888";
                            ctx.fillText("...", margin + padding, currentY);
                        }
                        
                        return textHeight;
                    },
                    
                    computeSize: function(width) {
                        const lines = this.displayText ? this.displayText.split('\n') : [""];
                        const lineHeight = 16;
                        const padding = 10;
                        const minHeight = 60;
                        const textHeight = Math.max(minHeight, Math.min(lines.length, 3) * lineHeight + padding * 2);
                        return [width, textHeight];
                    }
                };
                
                // Add the widget
                if (!this.widgets) {
                    this.widgets = [];
                }
                this.widgets.push(widget);
                
                // Adjust node size
                this.computeSize();
                this.setDirtyCanvas(true);
            };
            
            // Initialize on node creation
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                onNodeCreated?.apply(this, arguments);
                
                // Set minimum size
                this.size[0] = Math.max(this.size[0], 250);
                this.size[1] = Math.max(this.size[1], 150);
                
                // Add placeholder text
                this.updateDisplay("Value will appear here...");
            };
        }
    }
});