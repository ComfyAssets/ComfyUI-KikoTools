// ComfyUI-KikoTools - Width Height Selector with Swap Button
import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "comfyassets.WidthHeightSelector", 
  async beforeRegisterNodeDef(nodeType, nodeData, _app) {
    if (nodeData.name === "WidthHeightSelector") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        if (onNodeCreated) onNodeCreated.apply(this, []);
        
        // Track button click state for visual feedback
        this.swapButtonPressed = false;
        
        // Override preset callback to update width/height widgets when preset changes
        const presetWidget = this.widgets.find(w => w.name === "preset");
        if (presetWidget) {
          const originalCallback = presetWidget.callback;
          presetWidget.callback = function(value, graphcanvas, node, pos, event) {
            // Call original callback first
            if (originalCallback) {
              originalCallback.call(this, value, graphcanvas, node, pos, event);
            }
            
            // Update width/height widgets based on preset
            const widthWidget = node.widgets.find(w => w.name === "width");
            const heightWidget = node.widgets.find(w => w.name === "height");
            
            if (widthWidget && heightWidget && value !== "custom") {
              // Define all available presets from our preset system
              const presetDimensions = {
                // SDXL Presets
                "1024×1024": [1024, 1024], "896×1152": [896, 1152], "832×1216": [832, 1216], 
                "768×1344": [768, 1344], "640×1536": [640, 1536], "1152×896": [1152, 896], 
                "1216×832": [1216, 832], "1344×768": [1344, 768], "1536×640": [1536, 640],
                // FLUX Presets  
                "1920×1080": [1920, 1080], "1536×1536": [1536, 1536], "1280×768": [1280, 768], 
                "768×1280": [768, 1280], "1440×1080": [1440, 1080], "1080×1440": [1080, 1440], 
                "1728×1152": [1728, 1152], "1152×1728": [1152, 1728],
                // Ultra-Wide Presets
                "2560×1080": [2560, 1080], "2048×768": [2048, 768], "1792×768": [1792, 768], 
                "2304×768": [2304, 768], "1080×2560": [1080, 2560], "768×2048": [768, 2048], 
                "768×1792": [768, 1792], "768×2304": [768, 2304]
              };
              
              if (presetDimensions[value]) {
                const [w, h] = presetDimensions[value];
                widthWidget.value = w;
                heightWidget.value = h;
                
                // Trigger widget callbacks to update the UI
                if (widthWidget.callback) {
                  widthWidget.callback(w, graphcanvas, node, pos, event);
                }
                if (heightWidget.callback) {
                  heightWidget.callback(h, graphcanvas, node, pos, event);
                }
              }
            }
          };
        }
        
        // Add swap functionality
        this.swapDimensions = function() {
          const widthWidget = this.widgets.find(w => w.name === "width");
          const heightWidget = this.widgets.find(w => w.name === "height");
          const presetWidget = this.widgets.find(w => w.name === "preset");
          
          if (widthWidget && heightWidget && presetWidget) {
            // Handle preset swapping first
            if (presetWidget.value !== "custom") {
              const currentPreset = presetWidget.value;
              
              // Parse current preset dimensions (handle both × and x separators)
              let w, h;
              if (currentPreset.includes('×')) {
                [w, h] = currentPreset.split('×').map(v => parseInt(v));
              } else if (currentPreset.includes('x')) {
                [w, h] = currentPreset.split('x').map(v => parseInt(v));
              } else {
                return; // Invalid preset format
              }
              
              const swappedPreset = `${h}×${w}`;
              
              // Define all available presets from our preset system
              const availablePresets = [
                "custom",
                // SDXL Presets
                "1024×1024", "896×1152", "832×1216", "768×1344", "640×1536",
                "1152×896", "1216×832", "1344×768", "1536×640",
                // FLUX Presets  
                "1920×1080", "1536×1536", "1280×768", "768×1280",
                "1440×1080", "1080×1440", "1728×1152", "1152×1728",
                // Ultra-Wide Presets
                "2560×1080", "2048×768", "1792×768", "2304×768",
                "1080×2560", "768×2048", "768×1792", "768×2304"
              ];
              
              if (availablePresets.includes(swappedPreset)) {
                // Swapped preset exists, use it
                presetWidget.value = swappedPreset;
                widthWidget.value = h;
                heightWidget.value = w;
                if (presetWidget.callback) {
                  presetWidget.callback(swappedPreset, this, presetWidget);
                }
                if (widthWidget.callback) {
                  widthWidget.callback(h, this, widthWidget);
                }
                if (heightWidget.callback) {
                  heightWidget.callback(w, this, heightWidget);
                }
              } else {
                // Swapped preset doesn't exist, switch to custom and swap manual values
                presetWidget.value = "custom";
                widthWidget.value = h;
                heightWidget.value = w;
                
                if (presetWidget.callback) {
                  presetWidget.callback("custom", this, presetWidget);
                }
                if (widthWidget.callback) {
                  widthWidget.callback(h, this, widthWidget);
                }
                if (heightWidget.callback) {
                  heightWidget.callback(w, this, heightWidget);
                }
              }
            } else {
              // Custom preset - just swap the width and height values
              const tempWidth = widthWidget.value;
              widthWidget.value = heightWidget.value;
              heightWidget.value = tempWidth;
              
              // Trigger widget change events
              if (widthWidget.callback) {
                widthWidget.callback(widthWidget.value, this, widthWidget);
              }
              if (heightWidget.callback) {
                heightWidget.callback(heightWidget.value, this, heightWidget);
              }
            }
            
            // Mark the graph as changed
            this.graph?.setDirtyCanvas(true, true);
          }
        };
      };

      const onDrawForeground = nodeType.prototype.onDrawForeground;
      nodeType.prototype.onDrawForeground = function (ctx) {
        if (onDrawForeground) {
          onDrawForeground.apply(this, arguments);
        }
        
        if (this.flags.collapsed) return;
        
        // Draw swap button with consistent spacing from widgets
        const swapButtonSize = 24;
        const margin = 6;
        const swapButtonX = this.size[0] - swapButtonSize - margin;
        
        // Calculate button position based on widget spacing rather than bottom margin
        // Estimate widget area height and add consistent spacing
        const estimatedWidgetHeight = 90; // Approximate height for 3 widgets
        const topMargin = 35; // Space from top to first widget
        const buttonSpacing = 10; // Space between last widget and button
        const swapButtonY = topMargin + estimatedWidgetHeight + buttonSpacing;
        
        // Button background - change color based on pressed state
        if (this.swapButtonPressed) {
          // Darker when pressed
          ctx.fillStyle = "rgba(30, 120, 200, 0.9)"; // Darker blue when clicked
        } else {
          // Normal state
          ctx.fillStyle = "rgba(66, 165, 245, 0.8)"; // Material blue
        }
        ctx.beginPath();
        ctx.roundRect(swapButtonX, swapButtonY, swapButtonSize, swapButtonSize, 4);
        ctx.fill();
        
        // Button border with subtle highlight
        ctx.strokeStyle = this.swapButtonPressed ? "rgba(20, 100, 180, 1.0)" : "rgba(33, 150, 243, 0.9)";
        ctx.lineWidth = 1;
        ctx.stroke();
        
        // Draw swap icon - modern double arrow design
        ctx.strokeStyle = "rgba(255, 255, 255, 0.95)";
        ctx.lineWidth = 2;
        ctx.lineCap = "round";
        
        const centerX = swapButtonX + 12;
        const centerY = swapButtonY + 12;
        
        // Top arrow (pointing right) - width to height
        ctx.beginPath();
        ctx.moveTo(centerX - 7, centerY - 3);
        ctx.lineTo(centerX + 5, centerY - 3);
        ctx.stroke();
        
        // Top arrow head
        ctx.beginPath();
        ctx.moveTo(centerX + 5, centerY - 3);
        ctx.lineTo(centerX + 2, centerY - 5);
        ctx.moveTo(centerX + 5, centerY - 3);
        ctx.lineTo(centerX + 2, centerY - 1);
        ctx.stroke();
        
        // Bottom arrow (pointing left) - height to width
        ctx.beginPath();
        ctx.moveTo(centerX + 5, centerY + 3);
        ctx.lineTo(centerX - 7, centerY + 3);
        ctx.stroke();
        
        // Bottom arrow head
        ctx.beginPath();
        ctx.moveTo(centerX - 7, centerY + 3);
        ctx.lineTo(centerX - 4, centerY + 1);
        ctx.moveTo(centerX - 7, centerY + 3);
        ctx.lineTo(centerX - 4, centerY + 5);
        ctx.stroke();
        
        // Add subtle tooltip text when hovering (if we had hover state)
        // This could be extended with hover detection for better UX
      };

      const onMouseDown = nodeType.prototype.onMouseDown;
      nodeType.prototype.onMouseDown = function (e) {
        // Check if click is on swap button
        const swapButtonSize = 24;
        const margin = 6;
        const swapButtonX = this.pos[0] + this.size[0] - swapButtonSize - margin;
        
        // Use same positioning logic as drawing
        const estimatedWidgetHeight = 90;
        const topMargin = 35;
        const buttonSpacing = 10;
        const swapButtonY = this.pos[1] + topMargin + estimatedWidgetHeight + buttonSpacing;
        
        if (
          e.canvasX >= swapButtonX &&
          e.canvasX <= swapButtonX + swapButtonSize &&
          e.canvasY >= swapButtonY &&
          e.canvasY <= swapButtonY + swapButtonSize
        ) {
          // Visual feedback - set button as pressed
          this.swapButtonPressed = true;
          this.setDirtyCanvas(true, true);
          
          // Execute swap
          this.swapDimensions();
          
          // Reset button state after a short delay for visual feedback
          setTimeout(() => {
            this.swapButtonPressed = false;
            this.setDirtyCanvas(true, true);
          }, 150);
          
          return true; // Consume the event
        }
        
        // Call original onMouseDown if not clicking swap button
        if (onMouseDown) {
          return onMouseDown.apply(this, arguments);
        }
      };

      // Optional: Add hover effect for better user feedback
      const onMouseMove = nodeType.prototype.onMouseMove;
      nodeType.prototype.onMouseMove = function (e) {
        // Check if hovering over swap button
        const swapButtonSize = 24;
        const margin = 6;
        const swapButtonX = this.pos[0] + this.size[0] - swapButtonSize - margin;
        
        // Use same positioning logic as drawing
        const estimatedWidgetHeight = 90;
        const topMargin = 35;
        const buttonSpacing = 10;
        const swapButtonY = this.pos[1] + topMargin + estimatedWidgetHeight + buttonSpacing;
        
        const isHovering = (
          e.canvasX >= swapButtonX &&
          e.canvasX <= swapButtonX + swapButtonSize &&
          e.canvasY >= swapButtonY &&
          e.canvasY <= swapButtonY + swapButtonSize
        );
        
        // Update cursor style for better UX (safely)
        if (isHovering && this.graph && this.graph.canvas && this.graph.canvas.canvas) {
          this.graph.canvas.canvas.style.cursor = "pointer";
        } else if (this.graph && this.graph.canvas && this.graph.canvas.canvas) {
          this.graph.canvas.canvas.style.cursor = "default";
        }
        
        // Call original onMouseMove
        if (onMouseMove) {
          return onMouseMove.apply(this, arguments);
        }
      };
    }
  },
});