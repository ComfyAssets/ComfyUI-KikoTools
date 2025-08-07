import { app } from "../../../scripts/app.js";
import { ComfyWidgets } from "../../../scripts/widgets.js";

app.registerExtension({
    name: "ComfyAssets.DisplayText",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DisplayText") {
            const onExecuted = nodeType.prototype.onExecuted;
            
            nodeType.prototype.onExecuted = function(message) {
                onExecuted?.apply(this, arguments);
                
                if (message?.text) {
                    // Create or update the text widget
                    this.updateTextDisplay(message.text[0]);
                }
            };
            
            nodeType.prototype.updateTextDisplay = function(text) {
                // Remove existing text widget if any
                const existingWidget = this.widgets?.find(w => w.name === "displayed_text");
                if (existingWidget) {
                    const index = this.widgets.indexOf(existingWidget);
                    this.widgets.splice(index, 1);
                }
                
                // Parse the text to detect positive/negative prompt format
                function parsePrompts(text) {
                    const posMatch = text.match(/Positive prompt:\s*([\s\S]*?)(?=Negative prompt:|$)/i);
                    const negMatch = text.match(/Negative prompt:\s*([\s\S]*?)(?=\*\*|$)/i);
                    
                    if (posMatch && negMatch) {
                        // Extract just the prompt content, stopping at the first ** marker
                        let positiveText = posMatch[1].trim();
                        let negativeText = negMatch[1].trim();
                        
                        // Remove any trailing ** markers and everything after them
                        const posEndIndex = positiveText.indexOf('**');
                        if (posEndIndex > 0) {
                            positiveText = positiveText.substring(0, posEndIndex).trim();
                        }
                        
                        const negEndIndex = negativeText.indexOf('**');
                        if (negEndIndex > 0) {
                            negativeText = negativeText.substring(0, negEndIndex).trim();
                        }
                        
                        return {
                            type: 'prompts',
                            positive: positiveText,
                            negative: negativeText
                        };
                    }
                    
                    return {
                        type: 'text',
                        content: text
                    };
                }
                
                const parsedContent = parsePrompts(text);
                
                // Create custom widget for text display
                const widget = {
                    type: "custom_text_display",
                    name: "displayed_text",
                    size: [this.size[0] - 20, this.size[1] - 60], // Adjust for node chrome
                    parsedContent: parsedContent,
                    scrollOffset: 0,
                    posScrollOffset: 0,
                    negScrollOffset: 0,
                    
                    draw: function(ctx, node, widget_width, y, H) {
                        const margin = 10;
                        const padding = 10;
                        const lineHeight = 20;
                        const buttonHeight = 30;
                        const buttonWidth = 90;
                        
                        // Use the actual widget height from node size
                        const availableHeight = node.size[1] - 60; // Account for node header and margins
                        this.size[1] = Math.max(100, availableHeight);
                        
                        // Calculate available width for text
                        const availableWidth = widget_width - margin * 2 - padding * 2;
                        
                        // Word wrap function with better performance
                        function wrapText(text, maxWidth) {
                            const words = text.split(' ');
                            const lines = [];
                            let currentLine = '';
                            
                            ctx.font = "14px monospace";
                            
                            for (const word of words) {
                                const testLine = currentLine + (currentLine ? ' ' : '') + word;
                                const metrics = ctx.measureText(testLine);
                                
                                if (metrics.width > maxWidth && currentLine) {
                                    lines.push(currentLine);
                                    currentLine = word;
                                } else {
                                    currentLine = testLine;
                                }
                            }
                            
                            if (currentLine) {
                                lines.push(currentLine);
                            }
                            
                            return lines.length > 0 ? lines : [''];
                        }
                        
                        // Draw background
                        ctx.fillStyle = "#2a2a2a";
                        ctx.fillRect(margin, y, widget_width - margin * 2, this.size[1]);
                        
                        // Draw border
                        ctx.strokeStyle = "#444";
                        ctx.strokeRect(margin, y, widget_width - margin * 2, this.size[1]);
                        
                        if (this.parsedContent.type === 'prompts') {
                            // Simple split view for positive/negative prompts
                            const headerHeight = 25;
                            const buttonAreaHeight = buttonHeight + padding;
                            const totalTextHeight = this.size[1] - buttonAreaHeight;
                            const halfHeight = totalTextHeight / 2;
                            
                            // Draw positive prompt header
                            ctx.fillStyle = "#3a3a3a";
                            ctx.fillRect(margin + 1, y + 1, widget_width - margin * 2 - 2, headerHeight);
                            ctx.fillStyle = "#8f8";
                            ctx.font = "12px sans-serif";
                            ctx.fillText("✓ Positive Prompt", margin + padding, y + headerHeight - 7);
                            
                            // Positive prompt text area
                            const posTextY = y + headerHeight;
                            const posTextHeight = halfHeight - headerHeight;
                            ctx.fillStyle = "#1e1e1e";
                            ctx.fillRect(margin + 1, posTextY, widget_width - margin * 2 - 2, posTextHeight);
                            
                            // Draw separator
                            const separatorY = y + halfHeight;
                            ctx.strokeStyle = "#555";
                            ctx.beginPath();
                            ctx.moveTo(margin, separatorY);
                            ctx.lineTo(widget_width - margin, separatorY);
                            ctx.stroke();
                            
                            // Draw negative prompt header
                            ctx.fillStyle = "#3a3a3a";
                            ctx.fillRect(margin + 1, separatorY + 1, widget_width - margin * 2 - 2, headerHeight);
                            ctx.fillStyle = "#f88";
                            ctx.font = "12px sans-serif";
                            ctx.fillText("✗ Negative Prompt", margin + padding, separatorY + headerHeight - 7);
                            
                            // Negative prompt text area
                            const negTextY = separatorY + headerHeight;
                            const negTextHeight = halfHeight - headerHeight;
                            ctx.fillStyle = "#1e1e1e";
                            ctx.fillRect(margin + 1, negTextY, widget_width - margin * 2 - 2, negTextHeight);
                            
                            // Draw text for both sections
                            ctx.font = "14px monospace";
                            ctx.fillStyle = "#ddd";
                            
                            // Wrap text for both prompts
                            const posLines = [];
                            const posParagraphs = this.parsedContent.positive.split('\n');
                            for (const para of posParagraphs) {
                                if (para.trim() === '') {
                                    posLines.push('');
                                } else {
                                    posLines.push(...wrapText(para, availableWidth - 10));
                                }
                            }
                            
                            const negLines = [];
                            const negParagraphs = this.parsedContent.negative.split('\n');
                            for (const para of negParagraphs) {
                                if (para.trim() === '') {
                                    negLines.push('');
                                } else {
                                    negLines.push(...wrapText(para, availableWidth - 10));
                                }
                            }
                            
                            // Draw positive prompt text with clipping
                            ctx.save();
                            ctx.beginPath();
                            ctx.rect(margin + padding, posTextY + padding, availableWidth - 10, posTextHeight - padding * 2);
                            ctx.clip();
                            
                            let currentY = posTextY + padding + lineHeight - 5;
                            const posVisibleLines = Math.floor((posTextHeight - padding * 2) / lineHeight);
                            const posStartLine = Math.floor(this.posScrollOffset);
                            const posEndLine = Math.min(posStartLine + posVisibleLines, posLines.length);
                            
                            for (let i = posStartLine; i < posEndLine; i++) {
                                ctx.fillText(posLines[i], margin + padding, currentY);
                                currentY += lineHeight;
                            }
                            ctx.restore();
                            
                            // Draw positive scroll indicator if needed
                            if (posLines.length > posVisibleLines) {
                                const scrollBarWidth = 6;
                                const scrollBarX = widget_width - margin - scrollBarWidth - 2;
                                const scrollBarHeight = posTextHeight - padding * 2;
                                const maxScroll = posLines.length - posVisibleLines;
                                const scrollRatio = this.posScrollOffset / maxScroll;
                                const thumbHeight = Math.max(20, (posVisibleLines / posLines.length) * scrollBarHeight);
                                const thumbY = posTextY + padding + scrollRatio * (scrollBarHeight - thumbHeight);
                                
                                ctx.fillStyle = "#333";
                                ctx.fillRect(scrollBarX, posTextY + padding, scrollBarWidth, scrollBarHeight);
                                ctx.fillStyle = "#666";
                                ctx.fillRect(scrollBarX, thumbY, scrollBarWidth, thumbHeight);
                            }
                            
                            // Draw negative prompt text with clipping
                            ctx.save();
                            ctx.beginPath();
                            ctx.rect(margin + padding, negTextY + padding, availableWidth - 10, negTextHeight - padding * 2);
                            ctx.clip();
                            
                            ctx.fillStyle = "#ddd";
                            currentY = negTextY + padding + lineHeight - 5;
                            const negVisibleLines = Math.floor((negTextHeight - padding * 2) / lineHeight);
                            const negStartLine = Math.floor(this.negScrollOffset);
                            const negEndLine = Math.min(negStartLine + negVisibleLines, negLines.length);
                            
                            for (let i = negStartLine; i < negEndLine; i++) {
                                ctx.fillText(negLines[i], margin + padding, currentY);
                                currentY += lineHeight;
                            }
                            ctx.restore();
                            
                            // Draw negative scroll indicator if needed
                            if (negLines.length > negVisibleLines) {
                                const scrollBarWidth = 6;
                                const scrollBarX = widget_width - margin - scrollBarWidth - 2;
                                const scrollBarHeight = negTextHeight - padding * 2;
                                const maxScroll = negLines.length - negVisibleLines;
                                const scrollRatio = this.negScrollOffset / maxScroll;
                                const thumbHeight = Math.max(20, (negVisibleLines / negLines.length) * scrollBarHeight);
                                const thumbY = negTextY + padding + scrollRatio * (scrollBarHeight - thumbHeight);
                                
                                ctx.fillStyle = "#333";
                                ctx.fillRect(scrollBarX, negTextY + padding, scrollBarWidth, scrollBarHeight);
                                ctx.fillStyle = "#666";
                                ctx.fillRect(scrollBarX, thumbY, scrollBarWidth, thumbHeight);
                            }
                            
                            // Draw copy buttons
                            const buttonY = y + this.size[1] - buttonHeight - padding / 2;
                            const halfWidth = (widget_width - margin * 2) / 2;
                            
                            // Positive copy button
                            const posButtonX = margin + halfWidth / 2 - buttonWidth / 2;
                            ctx.fillStyle = this.posCopyHovered ? "#5a5a5a" : "#4a4a4a";
                            ctx.fillRect(posButtonX, buttonY, buttonWidth, buttonHeight);
                            ctx.strokeStyle = "#666";
                            ctx.strokeRect(posButtonX, buttonY, buttonWidth, buttonHeight);
                            
                            ctx.fillStyle = "#fff";
                            ctx.font = "12px sans-serif";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.fillText(this.posCopySuccess ? "✓ Copied!" : "📋 Positive", posButtonX + buttonWidth/2, buttonY + buttonHeight/2);
                            
                            // Negative copy button
                            const negButtonX = margin + halfWidth + halfWidth / 2 - buttonWidth / 2;
                            ctx.fillStyle = this.negCopyHovered ? "#5a5a5a" : "#4a4a4a";
                            ctx.fillRect(negButtonX, buttonY, buttonWidth, buttonHeight);
                            ctx.strokeStyle = "#666";
                            ctx.strokeRect(negButtonX, buttonY, buttonWidth, buttonHeight);
                            
                            // Ensure text color and alignment are set
                            ctx.fillStyle = "#fff";
                            ctx.font = "12px sans-serif";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.fillText(this.negCopySuccess ? "✓ Copied!" : "📋 Negative", negButtonX + buttonWidth/2, buttonY + buttonHeight/2);
                            
                            ctx.textAlign = "left";
                            ctx.textBaseline = "alphabetic";
                            
                        } else {
                            // Regular text display
                            const textAreaHeight = this.size[1] - buttonHeight - padding;
                            
                            // Draw text area background
                            ctx.fillStyle = "#1e1e1e";
                            ctx.fillRect(margin + 1, y + 1, widget_width - margin * 2 - 2, textAreaHeight);
                            
                            // Process text
                            ctx.font = "14px monospace";
                            const paragraphs = this.parsedContent.content.split('\n');
                            const allLines = [];
                            
                            for (const paragraph of paragraphs) {
                                if (paragraph.trim() === '') {
                                    allLines.push('');
                                } else {
                                    const wrappedLines = wrapText(paragraph, availableWidth);
                                    allLines.push(...wrappedLines);
                                }
                            }
                            
                            // Draw text with clipping
                            ctx.save();
                            ctx.beginPath();
                            ctx.rect(margin + padding, y + padding, availableWidth, textAreaHeight - padding * 2);
                            ctx.clip();
                            
                            const visibleLines = Math.floor((textAreaHeight - padding * 2) / lineHeight);
                            const maxScroll = Math.max(0, allLines.length - visibleLines);
                            this.scrollOffset = Math.max(0, Math.min(this.scrollOffset, maxScroll));
                            
                            ctx.fillStyle = "#ddd";
                            let currentY = y + padding + lineHeight - 5 - (this.scrollOffset * lineHeight);
                            
                            for (let i = 0; i < allLines.length; i++) {
                                if (currentY > y && currentY < y + textAreaHeight) {
                                    ctx.fillText(allLines[i], margin + padding, currentY);
                                }
                                currentY += lineHeight;
                            }
                            
                            ctx.restore();
                            
                            // Draw scroll indicator if needed
                            if (allLines.length > visibleLines) {
                                const scrollBarWidth = 6;
                                const scrollBarX = widget_width - margin - scrollBarWidth - 2;
                                const scrollBarHeight = textAreaHeight - 4;
                                const thumbHeight = Math.max(20, (visibleLines / allLines.length) * scrollBarHeight);
                                const thumbY = y + 2 + (this.scrollOffset / maxScroll) * (scrollBarHeight - thumbHeight);
                                
                                ctx.fillStyle = "#333";
                                ctx.fillRect(scrollBarX, y + 2, scrollBarWidth, scrollBarHeight);
                                ctx.fillStyle = "#666";
                                ctx.fillRect(scrollBarX, thumbY, scrollBarWidth, thumbHeight);
                            }
                            
                            // Draw copy button
                            const buttonX = widget_width - margin - buttonWidth - padding;
                            const buttonY = y + textAreaHeight + padding / 2;
                            
                            ctx.fillStyle = this.copyButtonHovered ? "#5a5a5a" : "#4a4a4a";
                            ctx.fillRect(buttonX, buttonY, buttonWidth, buttonHeight);
                            ctx.strokeStyle = "#666";
                            ctx.strokeRect(buttonX, buttonY, buttonWidth, buttonHeight);
                            
                            ctx.fillStyle = "#fff";
                            ctx.font = "12px sans-serif";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            ctx.fillText(this.copySuccess ? "✓ Copied!" : "📋 Copy", buttonX + buttonWidth/2, buttonY + buttonHeight/2);
                            ctx.textAlign = "left";
                            ctx.textBaseline = "alphabetic";
                        }
                        
                        return this.size[1];
                    },
                    
                    mouse: function(event, pos, node) {
                        const margin = 10;
                        const padding = 10;
                        const buttonWidth = 90;
                        const buttonHeight = 30;
                        const lineHeight = 20;
                        
                        // Check if mouse is over the widget
                        const isOver = pos[1] > this.last_y && pos[1] < this.last_y + this.size[1];
                        if (!isOver) return false;
                        
                        if (this.parsedContent.type === 'prompts') {
                            // Handle split view
                            const headerHeight = 25;
                            const buttonAreaHeight = buttonHeight + padding;
                            const totalTextHeight = this.size[1] - buttonAreaHeight;
                            const halfHeight = totalTextHeight / 2;
                            
                            const posTextY = this.last_y + headerHeight;
                            const posTextHeight = halfHeight - headerHeight;
                            const negTextY = this.last_y + halfHeight + headerHeight;
                            const negTextHeight = halfHeight - headerHeight;
                            
                            const buttonY = this.last_y + this.size[1] - buttonHeight - padding / 2;
                            const halfWidth = (node.size[0] - margin * 2) / 2;
                            
                            // Check which section for scrolling
                            const inPosSection = pos[1] > posTextY && pos[1] < posTextY + posTextHeight;
                            const inNegSection = pos[1] > negTextY && pos[1] < negTextY + negTextHeight;
                            
                            // Handle scrolling
                            if (event.type === "wheel") {
                                if (inPosSection) {
                                    const delta = event.deltaY > 0 ? 1 : -1;
                                    this.posScrollOffset = (this.posScrollOffset || 0) + delta;
                                    
                                    // Calculate max scroll
                                    const visibleLines = Math.floor((posTextHeight - padding * 2) / lineHeight);
                                    const totalLines = this.parsedContent.positive.split('\n').length * 2; // Estimate
                                    const maxScroll = Math.max(0, totalLines - visibleLines);
                                    this.posScrollOffset = Math.max(0, Math.min(this.posScrollOffset, maxScroll));
                                    
                                    node.setDirtyCanvas(true);
                                    return true;
                                } else if (inNegSection) {
                                    const delta = event.deltaY > 0 ? 1 : -1;
                                    this.negScrollOffset = (this.negScrollOffset || 0) + delta;
                                    
                                    // Calculate max scroll
                                    const visibleLines = Math.floor((negTextHeight - padding * 2) / lineHeight);
                                    const totalLines = this.parsedContent.negative.split('\n').length * 2; // Estimate
                                    const maxScroll = Math.max(0, totalLines - visibleLines);
                                    this.negScrollOffset = Math.max(0, Math.min(this.negScrollOffset, maxScroll));
                                    
                                    node.setDirtyCanvas(true);
                                    return true;
                                }
                            }
                            
                            // Check button hovers
                            const posButtonX = margin + halfWidth / 2 - buttonWidth / 2;
                            const negButtonX = margin + halfWidth + halfWidth / 2 - buttonWidth / 2;
                            
                            const oldPosHover = this.posCopyHovered;
                            const oldNegHover = this.negCopyHovered;
                            
                            this.posCopyHovered = pos[0] > posButtonX && pos[0] < posButtonX + buttonWidth &&
                                                 pos[1] > buttonY && pos[1] < buttonY + buttonHeight;
                            this.negCopyHovered = pos[0] > negButtonX && pos[0] < negButtonX + buttonWidth &&
                                                 pos[1] > buttonY && pos[1] < buttonY + buttonHeight;
                            
                            if (oldPosHover !== this.posCopyHovered || oldNegHover !== this.negCopyHovered) {
                                node.setDirtyCanvas(true);
                            }
                            
                            // Handle button clicks
                            if (event.type === "pointerdown") {
                                if (this.posCopyHovered) {
                                    this.copyToClipboard(this.parsedContent.positive, 'positive');
                                    return true;
                                } else if (this.negCopyHovered) {
                                    this.copyToClipboard(this.parsedContent.negative, 'negative');
                                    return true;
                                }
                            }
                        } else {
                            // Regular text handling
                            const textAreaHeight = this.size[1] - buttonHeight - padding;
                            const buttonX = node.size[0] - margin - buttonWidth - padding;
                            const buttonY = this.last_y + textAreaHeight + padding / 2;
                            
                            // Handle scrolling
                            if (event.type === "wheel" && pos[1] < this.last_y + textAreaHeight) {
                                const delta = event.deltaY > 0 ? 1 : -1;
                                this.scrollOffset = (this.scrollOffset || 0) + delta;
                                
                                const visibleLines = Math.floor((textAreaHeight - padding * 2) / lineHeight);
                                const totalLines = this.parsedContent.content.split('\n').length * 2; // Estimate
                                const maxScroll = Math.max(0, totalLines - visibleLines);
                                this.scrollOffset = Math.max(0, Math.min(this.scrollOffset, maxScroll));
                                
                                node.setDirtyCanvas(true);
                                return true;
                            }
                            
                            // Check button hover
                            const oldHover = this.copyButtonHovered;
                            this.copyButtonHovered = pos[0] > buttonX && pos[0] < buttonX + buttonWidth &&
                                                   pos[1] > buttonY && pos[1] < buttonY + buttonHeight;
                            
                            if (oldHover !== this.copyButtonHovered) {
                                node.setDirtyCanvas(true);
                            }
                            
                            // Handle button click
                            if (event.type === "pointerdown" && this.copyButtonHovered) {
                                this.copyToClipboard(this.parsedContent.content, 'regular');
                                return true;
                            }
                        }
                        
                        return false;
                    },
                    
                    copyToClipboard: function(text, type) {
                        const node = this._node;
                        navigator.clipboard.writeText(text).then(() => {
                            if (type === 'positive') {
                                this.posCopySuccess = true;
                            } else if (type === 'negative') {
                                this.negCopySuccess = true;
                            } else {
                                this.copySuccess = true;
                            }
                            node.setDirtyCanvas(true);
                            
                            setTimeout(() => {
                                this.posCopySuccess = false;
                                this.negCopySuccess = false;
                                this.copySuccess = false;
                                node.setDirtyCanvas(true);
                            }, 1500);
                        }).catch(err => {
                            console.error('Failed to copy:', err);
                            // Fallback copy method
                            const textArea = document.createElement("textarea");
                            textArea.value = text;
                            textArea.style.position = "fixed";
                            textArea.style.opacity = "0";
                            document.body.appendChild(textArea);
                            textArea.select();
                            try {
                                document.execCommand('copy');
                                if (type === 'positive') {
                                    this.posCopySuccess = true;
                                } else if (type === 'negative') {
                                    this.negCopySuccess = true;
                                } else {
                                    this.copySuccess = true;
                                }
                                node.setDirtyCanvas(true);
                                setTimeout(() => {
                                    this.posCopySuccess = false;
                                    this.negCopySuccess = false;
                                    this.copySuccess = false;
                                    node.setDirtyCanvas(true);
                                }, 1500);
                            } catch (err) {
                                console.error('Fallback copy failed:', err);
                            }
                            document.body.removeChild(textArea);
                        });
                    },
                    
                    computeSize: function(width) {
                        return [width, this.size[1]];
                    }
                };
                
                // Store reference to node for callbacks
                widget._node = this;
                
                // Store the last y position for mouse detection
                const originalDraw = widget.draw;
                widget.draw = function(ctx, node, widget_width, y, H) {
                    this.last_y = y;
                    return originalDraw.call(this, ctx, node, widget_width, y, H);
                };
                
                // Add the widget
                if (!this.widgets) {
                    this.widgets = [];
                }
                this.widgets.push(widget);
                
                // Adjust node size to accommodate the widget
                this.computeSize();
            };
            
            // Handle node resizing
            const onResize = nodeType.prototype.onResize;
            nodeType.prototype.onResize = function(size) {
                onResize?.apply(this, arguments);
                
                // Update widget size when node is resized
                const textWidget = this.widgets?.find(w => w.name === "displayed_text");
                if (textWidget) {
                    textWidget.size[0] = size[0] - 20;
                    textWidget.size[1] = size[1] - 60;
                    this.setDirtyCanvas(true);
                }
            };
            
            // Initialize on node creation
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                onNodeCreated?.apply(this, arguments);
                
                // Set default size
                this.size[0] = Math.max(this.size[0], 350);
                this.size[1] = Math.max(this.size[1], 300);
                
                // Add placeholder text
                this.updateTextDisplay("Text will appear here after execution...");
                
                // Mark this node as having a scrollable widget
                this.flags = this.flags || {};
                this.flags.allow_interaction = true;
            };
            
            // Override mouse wheel handler at node level
            const onMouseWheel = nodeType.prototype.onMouseWheel;
            nodeType.prototype.onMouseWheel = function(event, local_pos, delta) {
                const textWidget = this.widgets?.find(w => w.name === "displayed_text");
                if (textWidget) {
                    // Let the widget handle the mouse event
                    const fakeEvent = { type: "wheel", deltaY: -delta[1] * 100 };
                    if (textWidget.mouse && textWidget.mouse.call(textWidget, fakeEvent, local_pos, this)) {
                        return true;
                    }
                }
                return onMouseWheel?.apply(this, arguments) || false;
            };
        }
    }
});