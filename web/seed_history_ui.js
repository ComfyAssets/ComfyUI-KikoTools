// ComfyUI-KikoTools - Seed History with Tracking UI
import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "comfyassets.SeedHistory",

  async setup() {
    // Store reference to all SeedHistory nodes
    window.seedHistoryNodes = window.seedHistoryNodes || [];
  },

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name === "SeedHistory") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;

      nodeType.prototype.onNodeCreated = function () {
        if (onNodeCreated) {
          onNodeCreated.apply(this, arguments);
        }

        // Initialize seed history
        this.seedHistory = this.loadSeedHistory();
        this.hideTimer = null;
        this.mouseOverHistory = false;

        // Register this node in global registry
        window.seedHistoryNodes = window.seedHistoryNodes || [];
        window.seedHistoryNodes.push(this);

        // Create UI container
        const uiContainer = document.createElement("div");
        uiContainer.style.padding = "8px";
        uiContainer.style.backgroundColor = "#1e1e1e";
        uiContainer.style.borderRadius = "6px";
        uiContainer.style.marginTop = "6px";
        uiContainer.style.border = "1px solid #404040";

        this.buildSeedInterface(uiContainer);

        // Add as widget
        this.seedWidget = this.addDOMWidget(
          "seed_history_ui",
          "div",
          uiContainer,
        );

        // Set node size
        if (!this.hasBeenResized) {
          this.size = [280, 320];
        }

        // Track manual resizing
        const originalResize = this.onResize;
        this.onResize = function (size) {
          this.hasBeenResized = true;
          if (originalResize) {
            originalResize.call(this, size);
          }
        };

        // Hook into seed widget callbacks to track all changes
        setTimeout(() => {
          this.setupSeedWidgetCallbacks();
        }, 100);

        // Hook directly into widget value changes
        const originalOnWidgetChange = this.onWidgetChange;
        this.onWidgetChange = function(name, value, oldValue, widget) {
          if (name === "seed" && value !== oldValue) {
            this.addSeedToHistory(value);
          }

          if (originalOnWidgetChange) {
            return originalOnWidgetChange.call(this, name, value, oldValue, widget);
          }
        };

        // Save/load data
        const originalSerialize = this.serialize;
        this.serialize = function () {
          const data = originalSerialize ? originalSerialize.call(this) : {};
          data.hasBeenResized = this.hasBeenResized;
          data.seedHistory = this.seedHistory;
          return data;
        };

        const originalConfigure = this.configure;
        this.configure = function (data) {
          if (originalConfigure) {
            originalConfigure.call(this, data);
          }
          if (data.hasBeenResized) {
            this.hasBeenResized = data.hasBeenResized;
          }
          if (data.seedHistory) {
            this.seedHistory = data.seedHistory;
            this.refreshHistoryDisplay();
          }
        };

        // Cleanup interval on node removal
        const originalOnRemoved = this.onRemoved;
        this.onRemoved = function () {
          if (this.seedValueWatcher) {
            clearInterval(this.seedValueWatcher);
            this.seedValueWatcher = null;
          }

          // Clean up deduplication tracking
          if (this.lastAddedSeed) {
            this.lastAddedSeed = null;
          }

          // Remove from global registry
          if (window.seedHistoryNodes) {
            const index = window.seedHistoryNodes.indexOf(this);
            if (index !== -1) {
              window.seedHistoryNodes.splice(index, 1);
            }
          }

          if (originalOnRemoved) {
            originalOnRemoved.call(this);
          }
        };

        this.setDirtyCanvas(true, true);
      };

      // Setup seed widget callbacks to track increment/decrement/randomize
      nodeType.prototype.setupSeedWidgetCallbacks = function () {
        // Find the seed widget
        const seedWidget = this.widgets?.find(w => w.name === "seed");
        if (!seedWidget) {
          setTimeout(() => this.setupSeedWidgetCallbacks(), 500);
          return;
        }

        // Store the last known seed value to detect changes
        this.lastSeedValue = seedWidget.value;

        // Monitor for value changes that might not trigger callback
        this.seedValueWatcher = setInterval(() => {
          if (seedWidget.value !== this.lastSeedValue) {
            this.lastSeedValue = seedWidget.value;
            this.addSeedToHistory(seedWidget.value);
          }
        }, 1000);
      };

      // Build the seed interface
      nodeType.prototype.buildSeedInterface = function (container) {
        container.innerHTML = "";

        // Header
        const headerDiv = document.createElement("div");
        headerDiv.style.marginBottom = "8px";

        const titleDiv = document.createElement("div");
        titleDiv.style.fontWeight = "bold";
        titleDiv.style.color = "#00d4ff";
        titleDiv.style.textAlign = "center";
        titleDiv.style.padding = "4px";
        titleDiv.style.backgroundColor = "rgba(0, 212, 255, 0.1)";
        titleDiv.style.borderRadius = "4px";
        titleDiv.style.fontSize = "11px";
        titleDiv.innerHTML = "🎲 Seed History";
        headerDiv.appendChild(titleDiv);

        // Action buttons
        const buttonDiv = document.createElement("div");
        buttonDiv.style.display = "flex";
        buttonDiv.style.gap = "4px";
        buttonDiv.style.marginTop = "6px";

        // Generate button
        const generateBtn = document.createElement("button");
        generateBtn.textContent = "🎲 Generate";
        generateBtn.style.flex = "1";
        generateBtn.style.padding = "3px 6px";
        generateBtn.style.backgroundColor = "#0088cc";
        generateBtn.style.color = "white";
        generateBtn.style.border = "none";
        generateBtn.style.borderRadius = "3px";
        generateBtn.style.cursor = "pointer";
        generateBtn.style.fontSize = "10px";
        generateBtn.addEventListener("click", () => this.generateRandomSeed());
        buttonDiv.appendChild(generateBtn);

        // Clear button
        const clearBtn = document.createElement("button");
        clearBtn.textContent = "🗑️ Clear";
        clearBtn.style.flex = "1";
        clearBtn.style.padding = "3px 6px";
        clearBtn.style.backgroundColor = "#cc4444";
        clearBtn.style.color = "white";
        clearBtn.style.border = "none";
        clearBtn.style.borderRadius = "3px";
        clearBtn.style.cursor = "pointer";
        clearBtn.style.fontSize = "10px";
        clearBtn.addEventListener("click", () => this.clearSeedHistory());
        buttonDiv.appendChild(clearBtn);

        headerDiv.appendChild(buttonDiv);
        container.appendChild(headerDiv);

        // History display
        const historyDiv = document.createElement("div");
        historyDiv.style.maxHeight = "180px";
        historyDiv.style.overflowY = "auto";
        historyDiv.style.border = "1px solid #333";
        historyDiv.style.borderRadius = "4px";
        historyDiv.style.backgroundColor = "#2a2a2a";
        historyDiv.style.padding = "6px";
        historyDiv.style.fontSize = "10px";
        historyDiv.style.fontFamily = "monospace";

        // Mouse events for auto-hide
        historyDiv.addEventListener("mouseenter", () => {
          this.mouseOverHistory = true;
          this.cancelAutoHide();
        });

        historyDiv.addEventListener("mouseleave", () => {
          this.mouseOverHistory = false;
          this.startAutoHide();
        });

        this.historyDisplay = historyDiv;
        container.appendChild(historyDiv);

        this.refreshHistoryDisplay();
      };

      // Load history from storage
      nodeType.prototype.loadSeedHistory = function () {
        try {
          const stored = localStorage.getItem('comfyui_kikotools_seed_history');
          return stored ? JSON.parse(stored) : [];
        } catch (error) {
          return [];
        }
      };

      // Save history to storage
      nodeType.prototype.saveSeedHistory = function () {
        try {
          localStorage.setItem('comfyui_kikotools_seed_history', JSON.stringify(this.seedHistory));
        } catch (error) {
          // Silently handle storage errors
        }
      };

      // Add seed to history
      nodeType.prototype.addSeedToHistory = function (seed) {
        if (!seed || seed === 0) return;

        const numSeed = typeof seed === 'string' ? parseInt(seed) : seed;
        const now = Date.now();

        // Deduplication: prevent adding the same seed within 500ms window
        if (!this.lastAddedSeed) {
          this.lastAddedSeed = { seed: null, timestamp: 0 };
        }

        const timeSinceLastAdd = now - this.lastAddedSeed.timestamp;
        const isSameSeed = this.lastAddedSeed.seed === numSeed;
        const isWithinDupeWindow = timeSinceLastAdd < 500; // 500ms window

        if (isSameSeed && isWithinDupeWindow) {
          return;
        }

        // Update deduplication tracking
        this.lastAddedSeed = { seed: numSeed, timestamp: now };

        // Remove if already exists in history
        this.seedHistory = this.seedHistory.filter(item => item.seed !== numSeed);

        // Add to front
        this.seedHistory.unshift({
          seed: numSeed,
          timestamp: now,
          dateString: new Date().toLocaleString()
        });

        // Keep only last 10
        if (this.seedHistory.length > 10) {
          this.seedHistory = this.seedHistory.slice(0, 10);
        }

        this.saveSeedHistory();
        this.refreshHistoryDisplay();
        this.startAutoHide();
      };

      // Generate new random seed
      nodeType.prototype.generateRandomSeed = function () {
        const newSeed = Math.floor(Math.random() * 0xFFFFFFFFFFFFFFFF);

        const seedWidget = this.widgets?.find(w => w.name === "seed");
        if (seedWidget) {
          seedWidget.value = newSeed;
          if (seedWidget.callback) {
            seedWidget.callback(newSeed, this, seedWidget);
          }
        }

        this.addSeedToHistory(newSeed);
        this.setDirtyCanvas(true, true);
        this.showMessage(`Generated: ${newSeed}`, "success");
      };

      // Use seed from history
      nodeType.prototype.useSeedFromHistory = function (historyItem, index) {
        const seedWidget = this.widgets?.find(w => w.name === "seed");
        if (seedWidget) {
          seedWidget.value = historyItem.seed;
          if (seedWidget.callback) {
            seedWidget.callback(historyItem.seed, this, seedWidget);
          }
        }

        this.highlightHistoryEntry(index);
        this.setDirtyCanvas(true, true);
        this.startAutoHide();
        this.showMessage(`Loaded: ${historyItem.seed}`, "info");
      };

      // Clear history
      nodeType.prototype.clearSeedHistory = function () {
        this.seedHistory = [];
        this.saveSeedHistory();
        this.refreshHistoryDisplay();
        this.showMessage("History cleared", "info");
      };

      // Refresh history display
      nodeType.prototype.refreshHistoryDisplay = function () {
        if (!this.historyDisplay) return;

        if (!this.seedHistory || this.seedHistory.length === 0) {
          this.historyDisplay.innerHTML =
            '<div style="color: #888; text-align: center; padding: 15px;">No seeds tracked<br><small>Generate seeds to build history</small></div>';
          return;
        }

        this.historyDisplay.innerHTML = "";

        this.seedHistory.forEach((item, index) => {
          const entryDiv = document.createElement("div");
          entryDiv.style.padding = "4px";
          entryDiv.style.marginBottom = "3px";
          entryDiv.style.backgroundColor = "#333";
          entryDiv.style.borderRadius = "2px";
          entryDiv.style.cursor = "pointer";
          entryDiv.style.border = "1px solid transparent";
          entryDiv.style.lineHeight = "1.2";

          entryDiv.addEventListener("mouseenter", () => {
            entryDiv.style.backgroundColor = "#444";
            entryDiv.style.border = "1px solid #555";
          });
          entryDiv.addEventListener("mouseleave", () => {
            entryDiv.style.backgroundColor = "#333";
            entryDiv.style.border = "1px solid transparent";
          });

          entryDiv.addEventListener("click", () => {
            this.useSeedFromHistory(item, index);
          });

          const timeAgo = this.formatTimeAgo(item.timestamp);
          entryDiv.innerHTML = `
            <div style="color: #fff; font-weight: bold; margin-bottom: 1px;">
              🎲 ${item.seed}
            </div>
            <div style="color: #999; font-size: 8px;">
              ⏰ ${timeAgo}
            </div>
          `;

          this.historyDisplay.appendChild(entryDiv);
        });

        this.startAutoHide();
      };

      // Highlight selected entry
      nodeType.prototype.highlightHistoryEntry = function (index) {
        const entries = this.historyDisplay.querySelectorAll('div[style*="cursor: pointer"]');
        entries.forEach((entry, i) => {
          if (i === index) {
            entry.style.backgroundColor = "#006600";
            entry.style.border = "1px solid #00aa00";
          } else {
            entry.style.backgroundColor = "#333";
            entry.style.border = "1px solid transparent";
          }
        });
      };

      // Auto-hide functionality
      nodeType.prototype.startAutoHide = function () {
        this.cancelAutoHide();
        if (!this.mouseOverHistory) {
          this.hideTimer = setTimeout(() => {
            this.hideHistorySection();
          }, 2500);
        }
      };

      nodeType.prototype.cancelAutoHide = function () {
        if (this.hideTimer) {
          clearTimeout(this.hideTimer);
          this.hideTimer = null;
        }
      };

      nodeType.prototype.hideHistorySection = function () {
        if (this.historyDisplay && !this.mouseOverHistory) {
          this.historyDisplay.style.display = "none";

          if (!this.restoreButton) {
            const restoreDiv = document.createElement("div");
            restoreDiv.style.padding = "10px";
            restoreDiv.style.backgroundColor = "#2a2a2a";
            restoreDiv.style.border = "1px solid #333";
            restoreDiv.style.borderRadius = "4px";
            restoreDiv.style.textAlign = "center";
            restoreDiv.style.cursor = "pointer";
            restoreDiv.style.color = "#888";
            restoreDiv.style.fontSize = "10px";
            restoreDiv.innerHTML = "🎲 History auto-hidden<br><small>Click to show</small>";

            restoreDiv.addEventListener("mouseenter", () => {
              restoreDiv.style.backgroundColor = "#333";
              restoreDiv.style.color = "#bbb";
            });
            restoreDiv.addEventListener("mouseleave", () => {
              restoreDiv.style.backgroundColor = "#2a2a2a";
              restoreDiv.style.color = "#888";
            });

            restoreDiv.addEventListener("click", () => {
              this.showHistorySection();
            });

            this.restoreButton = restoreDiv;
            this.historyDisplay.parentNode.insertBefore(
              restoreDiv,
              this.historyDisplay.nextSibling
            );
          }
        }
      };

      nodeType.prototype.showHistorySection = function () {
        if (this.historyDisplay) {
          this.historyDisplay.style.display = "block";

          if (this.restoreButton && this.restoreButton.parentNode) {
            this.restoreButton.parentNode.removeChild(this.restoreButton);
            this.restoreButton = null;
          }

          this.startAutoHide();
        }
      };

      // Format time ago
      nodeType.prototype.formatTimeAgo = function (timestamp) {
        const now = Date.now();
        const diff = now - timestamp;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return `${seconds}s ago`;
      };

      // Show messages
      nodeType.prototype.showMessage = function (message, type = "info") {
        const notification = document.createElement("div");
        notification.style.position = "fixed";
        notification.style.top = "15px";
        notification.style.right = "15px";
        notification.style.padding = "6px 10px";
        notification.style.borderRadius = "3px";
        notification.style.color = "white";
        notification.style.fontSize = "10px";
        notification.style.zIndex = "10000";
        notification.style.maxWidth = "200px";
        notification.textContent = message;

        switch (type) {
          case "success":
            notification.style.backgroundColor = "#28a745";
            break;
          case "error":
            notification.style.backgroundColor = "#dc3545";
            break;
          case "warning":
            notification.style.backgroundColor = "#ffc107";
            break;
          default:
            notification.style.backgroundColor = "#17a2b8";
        }

        document.body.appendChild(notification);

        setTimeout(() => {
          if (notification.parentNode) {
            document.body.removeChild(notification);
          }
        }, 1800);
      };
    }
  },
});
