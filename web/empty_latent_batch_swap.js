// ComfyUI-KikoTools - Empty Latent Batch with Swap Button
import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "comfyassets.EmptyLatentBatch",
  async beforeRegisterNodeDef(nodeType, nodeData, _app) {
    if (nodeData.name === "EmptyLatentBatch") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        if (onNodeCreated) onNodeCreated.apply(this, []);

        // Helper function to extract resolution from formatted preset string
        this.extractResolutionFromPreset = function (presetValue) {
          if (presetValue === "custom") return null;

          // If it contains formatting metadata, extract the resolution part
          if (presetValue.includes(" - ")) {
            // Format is: "1024×1024 - 1:1 (1.0MP) - SDXL"
            return presetValue.split(" - ")[0];
          }

          // Otherwise assume it's already a raw resolution
          return presetValue;
        };

        // Create swap button as DOM widget
        this.createSwapButton();

        // Override preset callback to update width/height widgets when preset changes
        const presetWidget = this.widgets.find((w) => w.name === "preset");
        if (presetWidget) {
          const originalCallback = presetWidget.callback;
          presetWidget.callback = function (
            value,
            graphcanvas,
            node,
            pos,
            event,
          ) {
            // Call original callback first
            if (originalCallback) {
              originalCallback.call(this, value, graphcanvas, node, pos, event);
            }

            // Update width/height widgets based on preset
            const widthWidget = node.widgets.find((w) => w.name === "width");
            const heightWidget = node.widgets.find((w) => w.name === "height");

            if (widthWidget && heightWidget && value !== "custom") {
              // Extract raw resolution from formatted preset
              const rawResolution = node.extractResolutionFromPreset(value);

              // Define all available presets from our preset system
              const presetDimensions = {
                // SDXL Presets
                "1024×1024": [1024, 1024],
                "896×1152": [896, 1152],
                "832×1216": [832, 1216],
                "768×1344": [768, 1344],
                "640×1536": [640, 1536],
                "1152×896": [1152, 896],
                "1216×832": [1216, 832],
                "1344×768": [1344, 768],
                "1536×640": [1536, 640],
                // FLUX Presets
                "1920×1080": [1920, 1080],
                "1536×1536": [1536, 1536],
                "1280×768": [1280, 768],
                "768×1280": [768, 1280],
                "1440×1080": [1440, 1080],
                "1080×1440": [1080, 1440],
                "1728×1152": [1728, 1152],
                "1152×1728": [1152, 1728],
                // Ultra-Wide Presets
                "2560×1080": [2560, 1080],
                "2048×768": [2048, 768],
                "1792×768": [1792, 768],
                "2304×768": [2304, 768],
                "1080×2560": [1080, 2560],
                "768×2048": [768, 2048],
                "768×1792": [768, 1792],
                "768×2304": [768, 2304],
                // Qwen Presets
                "1328×1328": [1328, 1328],
                "1664×928": [1664, 928],
                "928×1664": [928, 1664],
                "1472×1104": [1472, 1104],
                "1104×1472": [1104, 1472],
                "1584×1056": [1584, 1056],
                "1056×1584": [1056, 1584],
                "2080×688": [2080, 688],
                "688×2080": [688, 2080],
              };

              if (rawResolution && presetDimensions[rawResolution]) {
                const [w, h] = presetDimensions[rawResolution];
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
        this.swapDimensions = function () {
          const widthWidget = this.widgets.find((w) => w.name === "width");
          const heightWidget = this.widgets.find((w) => w.name === "height");
          const presetWidget = this.widgets.find((w) => w.name === "preset");

          if (widthWidget && heightWidget && presetWidget) {
            // Handle preset swapping first
            if (presetWidget.value !== "custom") {
              const currentPreset = presetWidget.value;

              // Extract raw resolution from formatted preset
              const rawResolution =
                this.extractResolutionFromPreset(currentPreset);
              if (!rawResolution) return;

              // Parse current preset dimensions (handle both × and x separators)
              let w, h;
              if (rawResolution.includes("×")) {
                [w, h] = rawResolution.split("×").map((v) => parseInt(v));
              } else if (rawResolution.includes("x")) {
                [w, h] = rawResolution.split("x").map((v) => parseInt(v));
              } else {
                return; // Invalid preset format
              }

              const swappedRawPreset = `${h}×${w}`;

              // Find the formatted version of the swapped preset from available options
              const availablePresets =
                presetWidget.options.values || presetWidget.options;
              let swappedFormattedPreset = null;

              for (const option of availablePresets) {
                if (option === "custom") continue;
                const extractedRes = this.extractResolutionFromPreset(option);
                if (extractedRes === swappedRawPreset) {
                  swappedFormattedPreset = option;
                  break;
                }
              }

              if (swappedFormattedPreset) {
                // Swapped preset exists, use the formatted version
                presetWidget.value = swappedFormattedPreset;
                widthWidget.value = h;
                heightWidget.value = w;
                if (presetWidget.callback) {
                  presetWidget.callback(
                    swappedFormattedPreset,
                    app.canvas,
                    this,
                    [0, 0],
                    null
                  );
                }
                if (widthWidget.callback) {
                  widthWidget.callback(widthWidget.value, app.canvas, this, [0, 0], null);
                }
                if (heightWidget.callback) {
                  heightWidget.callback(heightWidget.value, app.canvas, this, [0, 0], null);
                }
              } else {
                // Swapped preset doesn't exist, switch to custom and swap manual values
                presetWidget.value = "custom";
                widthWidget.value = h;
                heightWidget.value = w;

                if (presetWidget.callback) {
                  presetWidget.callback("custom", app.canvas, this, [0, 0], null);
                }
                if (widthWidget.callback) {
                  widthWidget.callback(widthWidget.value, app.canvas, this, [0, 0], null);
                }
                if (heightWidget.callback) {
                  heightWidget.callback(heightWidget.value, app.canvas, this, [0, 0], null);
                }
              }
            } else {
              // Custom preset - just swap the width and height values
              const tempWidth = widthWidget.value;
              widthWidget.value = heightWidget.value;
              heightWidget.value = tempWidth;

              // Trigger widget change events
              if (widthWidget.callback) {
                widthWidget.callback(widthWidget.value, app.canvas, this, [0, 0], null);
              }
              if (heightWidget.callback) {
                heightWidget.callback(heightWidget.value, app.canvas, this, [0, 0], null);
              }
            }

            // Mark the graph as changed
            this.graph?.setDirtyCanvas(true, true);
          }
        };
      };

      // Create swap button as DOM widget
      nodeType.prototype.createSwapButton = function () {
        // Create button container
        const buttonContainer = document.createElement("div");
        buttonContainer.style.cssText = `
          padding: 4px;
          text-align: center;
        `;

        // Create swap button
        const swapButton = document.createElement("button");
        swapButton.innerHTML = "↔️ Swap W×H";
        swapButton.style.cssText = `
          background: #4A90E2;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 6px 12px;
          cursor: pointer;
          font-size: 11px;
          font-weight: bold;
          transition: background 0.2s;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        `;

        // Button hover effects
        swapButton.addEventListener("mouseenter", () => {
          swapButton.style.background = "#5BA0F2";
          swapButton.style.transform = "translateY(-1px)";
          swapButton.style.boxShadow = "0 3px 6px rgba(0,0,0,0.3)";
        });

        swapButton.addEventListener("mouseleave", () => {
          swapButton.style.background = "#4A90E2";
          swapButton.style.transform = "translateY(0)";
          swapButton.style.boxShadow = "0 2px 4px rgba(0,0,0,0.2)";
        });

        // Button click effect and functionality
        swapButton.addEventListener("mousedown", () => {
          swapButton.style.background = "#3A80D2";
          swapButton.style.transform = "translateY(1px)";
          swapButton.style.boxShadow = "0 1px 2px rgba(0,0,0,0.2)";
        });

        swapButton.addEventListener("mouseup", () => {
          swapButton.style.background = "#5BA0F2";
          swapButton.style.transform = "translateY(-1px)";
          swapButton.style.boxShadow = "0 3px 6px rgba(0,0,0,0.3)";
        });

        // Main click functionality
        swapButton.addEventListener("click", () => {
          this.swapDimensions();
        });

        buttonContainer.appendChild(swapButton);

        // Add as DOM widget
        this.swapButtonWidget = this.addDOMWidget(
          "swap_button",
          "div",
          buttonContainer
        );
      };

    }
  },
});
