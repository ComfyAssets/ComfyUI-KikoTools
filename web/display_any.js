import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "ComfyAssets.DisplayAny",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DisplayAny") {
            const onExecuted = nodeType.prototype.onExecuted;
            
            nodeType.prototype.onExecuted = function(message) {
                onExecuted?.apply(this, arguments);
                
                console.log("DisplayAny onExecuted message:", message);
                
                if (message?.text && message.text.length > 0) {
                    const displayText = message.text[0];
                    console.log("DisplayAny displayText:", displayText);
                    
                    // Update the display widget with the value
                    this.updateDisplay(displayText);
                    
                    // Also show a condensed version in the title
                    const firstLine = displayText.split('\n')[0];
                    const condensed = firstLine.length > 50 
                        ? firstLine.substring(0, 50) + "..." 
                        : firstLine;
                    this.title = `DisplayAny: ${condensed}`;
                } else {
                    console.log("DisplayAny no text in message");
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
                    displayText: text || "",
                    scrollY: 0,
                    maxScrollHeight: 0,
                    
                    draw: function(ctx, node, widget_width, y, H) {
                        const margin = 10;
                        const padding = 10;
                        const lineHeight = 16;
                        const minHeight = 60;
                        
                        // Fixed viewport height for scrollable area
                        const viewportHeight = 200; // Fixed height for display area
                        ctx.font = "12px monospace";
                        const lines = this.displayText ? this.displayText.split('\n') : [""];
                        
                        // Draw background
                        ctx.fillStyle = "#2a2a2a";
                        ctx.fillRect(margin, y, widget_width - margin * 2, viewportHeight);
                        
                        // Draw border
                        ctx.strokeStyle = "#444";
                        ctx.strokeRect(margin, y, widget_width - margin * 2, viewportHeight);
                        
                        // Draw text area background
                        ctx.fillStyle = "#1e1e1e";
                        ctx.fillRect(margin + 1, y + 1, widget_width - margin * 2 - 2, viewportHeight - 2);
                        
                        // Save context for clipping
                        ctx.save();
                        ctx.beginPath();
                        ctx.rect(margin + 1, y + 1, widget_width - margin * 2 - 2, viewportHeight - 2);
                        ctx.clip();
                        
                        // Prepare text
                        ctx.fillStyle = "#ddd";
                        ctx.textAlign = "left";
                        ctx.textBaseline = "top";
                        
                        // Draw each line with scrolling
                        const maxWidth = widget_width - margin * 2 - padding * 2;
                        let currentY = y + padding - this.scrollY;
                        
                        // Process text - wrap long lines for JSON
                        let processedLines = [];
                        for (const line of lines) {
                            if (line.length > 0) {
                                // Split long lines into chunks that fit
                                let remaining = line;
                                while (remaining.length > 0) {
                                    let chunkSize = remaining.length;
                                    while (chunkSize > 0 && ctx.measureText(remaining.substring(0, chunkSize)).width > maxWidth) {
                                        chunkSize--;
                                    }
                                    if (chunkSize === 0) chunkSize = 1; // At least one character
                                    processedLines.push(remaining.substring(0, chunkSize));
                                    remaining = remaining.substring(chunkSize);
                                }
                            } else {
                                processedLines.push(line);
                            }
                        }
                        
                        // Calculate total content height for scrolling
                        const totalContentHeight = processedLines.length * lineHeight + padding * 2;
                        this.maxScrollHeight = Math.max(0, totalContentHeight - viewportHeight);
                        
                        // Draw all visible lines
                        for (let i = 0; i < processedLines.length; i++) {
                            // Only draw if line is in viewport
                            if (currentY > y - lineHeight && currentY < y + viewportHeight) {
                                ctx.fillText(processedLines[i], margin + padding, currentY);
                            }
                            currentY += lineHeight;
                        }
                        
                        // Restore context
                        ctx.restore();
                        
                        // Draw scrollbar if needed
                        if (this.maxScrollHeight > 0) {
                            const scrollbarWidth = 6;
                            const scrollbarX = margin + widget_width - margin * 2 - scrollbarWidth - 2;
                            const scrollbarHeight = Math.max(20, (viewportHeight / totalContentHeight) * viewportHeight);
                            const scrollbarY = y + 2 + (this.scrollY / this.maxScrollHeight) * (viewportHeight - scrollbarHeight - 4);
                            
                            // Scrollbar track
                            ctx.fillStyle = "#333";
                            ctx.fillRect(scrollbarX, y + 2, scrollbarWidth, viewportHeight - 4);
                            
                            // Scrollbar thumb
                            ctx.fillStyle = "#666";
                            ctx.fillRect(scrollbarX, scrollbarY, scrollbarWidth, scrollbarHeight);
                        }
                        
                        return viewportHeight;
                    },
                    
                    computeSize: function(width) {
                        // Fixed height for scrollable viewport
                        const viewportHeight = 200;
                        return [width, viewportHeight];
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
                
                // Set minimum size - make it wider for better JSON display
                this.size[0] = Math.max(this.size[0], 400);
                this.size[1] = Math.max(this.size[1], 250); // Increased for viewport
                
                // Add placeholder text
                this.updateDisplay("Value will appear here...");
                
                // Mark this node as having a scrollable widget
                this.flags = this.flags || {};
                this.flags.allow_interaction = true;
            };
            
            // Handle mouse wheel events on the node
            const onMouseWheel = nodeType.prototype.onMouseWheel;
            nodeType.prototype.onMouseWheel = function(event, local_pos, delta) {
                // Check if we have a display widget
                const displayWidget = this.widgets?.find(w => w.name === "display_value");
                if (displayWidget && displayWidget.maxScrollHeight > 0) {
                    // Scroll by 3 lines at a time
                    const scrollStep = 48; // 3 lines * 16px
                    displayWidget.scrollY = Math.max(0, Math.min(displayWidget.maxScrollHeight, displayWidget.scrollY - delta[1] * scrollStep));
                    this.setDirtyCanvas(true);
                    return true; // Consume the event
                }
                
                // Call original handler if exists
                return onMouseWheel?.apply(this, arguments) || false;
            };
        }
    }
});