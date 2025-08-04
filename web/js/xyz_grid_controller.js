import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import "./xyz_grid_widgets.js";
import "./xyz_grid_ui.js";

// Helper function to trigger re-execution
async function queueNextExecution(nodeId, batchId) {
    const node = app.graph._nodes.find(n => n.id === nodeId);
    if (!node) return;
    
    // Add a small delay to allow current execution to complete
    setTimeout(async () => {
        // Trigger graph execution
        await app.queuePrompt();
    }, 100);
}

app.registerExtension({
    name: "ComfyAssets.XYZGridController",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "XYZPlotController") {
            // Store execution state
            nodeType.prototype.executionState = null;
            
            // Override onExecuted to handle grid iterations
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(data) {
                if (onExecuted) {
                    onExecuted.apply(this, arguments);
                }
                
                // Check if we need to queue next execution
                if (data && data.batch_id && data.grid_data) {
                    const gridData = data.grid_data;
                    const totalImages = gridData.total_images || 1;
                    const currentIndex = gridData.current_index || 0;
                    
                    // Store state
                    this.executionState = {
                        batchId: data.batch_id,
                        totalImages: totalImages,
                        currentIndex: currentIndex + 1
                    };
                    
                    // Update progress display
                    this.updateProgressDisplay();
                    
                    // Queue next execution if not complete
                    if (this.executionState.currentIndex < totalImages) {
                        queueNextExecution(this.id, data.batch_id);
                    }
                }
            };
            
            // Add progress display
            nodeType.prototype.updateProgressDisplay = function() {
                if (!this.executionState) return;
                
                const progress = `${this.executionState.currentIndex}/${this.executionState.totalImages}`;
                this.setProperty("progress", progress);
                
                // Update node title to show progress
                const baseTitle = this.constructor.title || "XYZ Plot Controller";
                this.title = `${baseTitle} [${progress}]`;
            };
            
            // Override onRemoved to clean up
            const onRemoved = nodeType.prototype.onRemoved;
            nodeType.prototype.onRemoved = function() {
                if (onRemoved) {
                    onRemoved.apply(this, arguments);
                }
                this.executionState = null;
            };
        }
    },
    
    async nodeCreated(node) {
        if (node.comfyClass === "XYZPlotController") {
            // Add dynamic widgets based on axis selection
            setupDynamicWidgets(node);
            
            // Add preview of total images
            setupImageCountPreview(node);
        }
    }
});

function setupDynamicWidgets(node) {
    // Monitor axis type changes and update value input accordingly
    const axisTypes = ['x_axis_type', 'y_axis_type', 'z_axis_type'];
    
    axisTypes.forEach(axisType => {
        const widget = node.widgets.find(w => w.name === axisType);
        if (!widget) return;
        
        const originalCallback = widget.callback;
        widget.callback = function(value) {
            if (originalCallback) {
                originalCallback.call(this, value);
            }
            
            // Update corresponding value widget
            updateValueWidget(node, axisType, value);
            
            // Update image count preview
            updateImageCount(node);
        };
    });
}

function updateValueWidget(node, axisType, selectedType) {
    const axisPrefix = axisType.split('_')[0]; // 'x', 'y', or 'z'
    const valueWidgetName = `${axisPrefix}_values`;
    const valueWidget = node.widgets.find(w => w.name === valueWidgetName);
    
    if (!valueWidget) return;
    
    // Update placeholder text based on type
    switch(selectedType) {
        case 'model':
        case 'sampler':
        case 'scheduler':
        case 'vae':
        case 'lora':
            valueWidget.inputEl.placeholder = "Enter comma-separated values (e.g., model1.safetensors, model2.ckpt)";
            break;
        case 'cfg_scale':
            valueWidget.inputEl.placeholder = "Enter values or range (e.g., 5,7,9 or 5:10:1)";
            break;
        case 'steps':
            valueWidget.inputEl.placeholder = "Enter values or range (e.g., 20,30,40 or 20:50:10)";
            break;
        case 'prompt':
            valueWidget.inputEl.placeholder = "Enter prompts separated by newlines";
            break;
        case 'seed':
            valueWidget.inputEl.placeholder = "Enter seed values (e.g., 0,100,200)";
            break;
        default:
            valueWidget.inputEl.placeholder = "Enter values";
    }
}

function setupImageCountPreview(node) {
    // Add a display widget for total image count
    const countWidget = node.addWidget("text", "total_images", "", () => {}, { serialize: false });
    countWidget.inputEl.readOnly = true;
    countWidget.inputEl.style.textAlign = "center";
    countWidget.inputEl.style.fontWeight = "bold";
    
    // Monitor value changes
    const valueWidgets = ['x_values', 'y_values', 'z_values'];
    valueWidgets.forEach(widgetName => {
        const widget = node.widgets.find(w => w.name === widgetName);
        if (!widget) return;
        
        const originalCallback = widget.callback;
        widget.callback = function(value) {
            if (originalCallback) {
                originalCallback.call(this, value);
            }
            updateImageCount(node);
        };
    });
    
    // Initial update
    updateImageCount(node);
}

function updateImageCount(node) {
    const countWidget = node.widgets.find(w => w.name === "total_images");
    if (!countWidget) return;
    
    // Parse values for each axis
    let xCount = 1, yCount = 1, zCount = 1;
    
    const xValues = node.widgets.find(w => w.name === "x_values")?.value || "";
    const yValues = node.widgets.find(w => w.name === "y_values")?.value || "";
    const zValues = node.widgets.find(w => w.name === "z_values")?.value || "";
    
    const xType = node.widgets.find(w => w.name === "x_axis_type")?.value || "none";
    const yType = node.widgets.find(w => w.name === "y_axis_type")?.value || "none";
    const zType = node.widgets.find(w => w.name === "z_axis_type")?.value || "none";
    
    if (xType !== "none" && xValues) {
        xCount = countValues(xValues, xType);
    }
    if (yType !== "none" && yValues) {
        yCount = countValues(yValues, yType);
    }
    if (zType !== "none" && zValues) {
        zCount = countValues(zValues, zType);
    }
    
    const total = xCount * yCount * zCount;
    countWidget.value = `Total Images: ${total}`;
    
    // Warn if too many images
    if (total > 100) {
        countWidget.inputEl.style.color = "#ff6b6b";
        countWidget.value += " ⚠️ Large batch!";
    } else {
        countWidget.inputEl.style.color = "#4ecdc4";
    }
}

function countValues(valueString, axisType) {
    if (!valueString || !valueString.trim()) return 0;
    
    // Check for range syntax
    if (valueString.includes(':')) {
        const parts = valueString.split(':');
        if (parts.length >= 2) {
            const start = parseFloat(parts[0]);
            const stop = parseFloat(parts[1]);
            const step = parts.length > 2 ? parseFloat(parts[2]) : 1;
            return Math.floor((stop - start) / step) + 1;
        }
    }
    
    // Count comma-separated or newline-separated values
    const separator = axisType === 'prompt' ? '\n' : ',';
    return valueString.split(separator).filter(v => v.trim()).length;
}