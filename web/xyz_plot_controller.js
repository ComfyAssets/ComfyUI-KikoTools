import { app } from "../scripts/app.js";
import { api } from "../scripts/api.js";

// Load CSS
const link = document.createElement("link");
link.rel = "stylesheet";
link.type = "text/css";
link.href = "extensions/ComfyUI-KikoTools/css/xyz_grid.css";
document.head.appendChild(link);

// Parameter type information and examples
const parameterInfo = {
    none: {
        description: "No parameter selected",
        example: null
    },
    model: {
        description: "Checkpoint/Model files",
        example: "Select from available models using the button below",
        connection: "Connect to CheckpointLoaderSimple → ckpt_name",
        outputType: "STRING"
    },
    vae: {
        description: "VAE (Variational Autoencoder) models",
        example: "Select from available VAEs or use 'Automatic'",
        connection: "Connect to VAELoader → vae_name",
        outputType: "STRING"
    },
    lora: {
        description: "LoRA (Low-Rank Adaptation) models",
        example: "Select LoRAs to apply (use 'None' for no LoRA)",
        connection: "Connect to LoraLoader → lora_name",
        outputType: "STRING"
    },
    sampler: {
        description: "Sampling algorithms",
        example: "Select from available samplers",
        connection: "Connect to KSampler → sampler_name",
        outputType: "STRING"
    },
    scheduler: {
        description: "Noise schedulers",
        example: "Select scheduler types",
        connection: "Connect to KSampler → scheduler",
        outputType: "STRING"
    },
    cfg_scale: {
        description: "Classifier-Free Guidance scale",
        example: "Examples:\n• Single values: 5, 7.5, 10, 12.5\n• Range: 5:15:2.5 (from 5 to 15, step 2.5)\n• Mixed: 1, 3, 5:10:1",
        connection: "Connect y_float or x_float to KSampler → cfg",
        outputType: "FLOAT",
        range: { min: 0, max: 30, default: 7.5 }
    },
    steps: {
        description: "Number of denoising steps",
        example: "Examples:\n• List: 20, 30, 40, 50\n• Range: 10:50:10 (from 10 to 50, step 10)\n• Quick test: 10, 20, 50",
        connection: "Connect y_int or x_int to KSampler → steps",
        outputType: "INT",
        range: { min: 1, max: 150, default: 20 }
    },
    clip_skip: {
        description: "CLIP layers to skip from the end",
        example: "Examples:\n• Common values: 1, 2\n• Full test: 1, 2, 3, 4\n• SDXL typically uses 1 or 2",
        connection: "Connect to CLIPSetLastLayer → stop_at_clip_layer",
        outputType: "INT",
        range: { min: 1, max: 12, default: 1 }
    },
    seed: {
        description: "Random seed for generation",
        example: "Examples:\n• Specific seeds: 42, 123, 456, 789\n• Range: 0:1000:100\n• Random set: 12345, 67890, 11111",
        connection: "Connect y_int or x_int to KSampler → seed",
        outputType: "INT",
        range: { min: 0, max: "0xffffffffffffffff", default: 0 }
    },
    denoise: {
        description: "Denoising strength (0=no change, 1=full denoise)",
        example: "Examples:\n• Light: 0.3, 0.5, 0.7\n• Full range: 0.2:1.0:0.2\n• img2img: 0.4, 0.6, 0.8, 1.0",
        connection: "Connect y_float or x_float to KSampler → denoise",
        outputType: "FLOAT",
        range: { min: 0, max: 1, default: 1 }
    },
    flux_guidance: {
        description: "Flux model guidance strength",
        example: "Examples:\n• Low to high: 1.0, 2.0, 3.5, 5.0\n• Fine steps: 1:5:0.5\n• Recommended: 2.5, 3.5, 4.5",
        connection: "Connect to FluxGuidance → guidance",
        outputType: "FLOAT",
        range: { min: 0, max: 10, default: 3.5 }
    },
    prompt: {
        description: "Text prompts (one per line)",
        example: "Enter different prompts, one per line:\n\na serene lake at sunset\na bustling city street\na mystical forest path\n\nTip: Keep prompts similar length for better grid layout",
        connection: "Connect y_string or x_string to CLIPTextEncode → text",
        outputType: "STRING"
    }
};

// Helper to get available options for different parameter types
const parameterHelpers = {
    model: {
        getOptions: async () => {
            try {
                const resp = await api.fetchApi('/api/models');
                const data = await resp.json();
                return data.checkpoints || [];
            } catch (e) {
                console.error("Failed to fetch models:", e);
                return [];
            }
        },
        placeholder: "Select models...",
        multiselect: true
    },
    
    vae: {
        getOptions: async () => {
            try {
                const resp = await api.fetchApi('/api/models');
                const data = await resp.json();
                return ["Automatic", ...(data.vae || [])];
            } catch (e) {
                return ["Automatic"];
            }
        },
        placeholder: "Select VAEs...",
        multiselect: true
    },
    
    lora: {
        getOptions: async () => {
            try {
                const resp = await api.fetchApi('/api/models');
                const data = await resp.json();
                return ["None", ...(data.loras || [])];
            } catch (e) {
                return ["None"];
            }
        },
        placeholder: "Select LoRAs...",
        multiselect: true
    },
    
    sampler: {
        getOptions: async () => {
            // Get samplers from KSampler node definition
            const nodeData = LiteGraph.registered_node_types["KSampler"];
            if (nodeData && nodeData.nodeData && nodeData.nodeData.input) {
                const samplerInput = nodeData.nodeData.input.required.sampler_name;
                if (samplerInput && samplerInput[0]) {
                    return samplerInput[0];
                }
            }
            // Fallback list
            return ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", 
                    "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", 
                    "dpmpp_sde", "dpmpp_2m", "dpmpp_2m_sde", "ddim", "uni_pc"];
        },
        placeholder: "Select samplers...",
        multiselect: true
    },
    
    scheduler: {
        getOptions: async () => {
            const nodeData = LiteGraph.registered_node_types["KSampler"];
            if (nodeData && nodeData.nodeData && nodeData.nodeData.input) {
                const schedulerInput = nodeData.nodeData.input.required.scheduler;
                if (schedulerInput && schedulerInput[0]) {
                    return schedulerInput[0];
                }
            }
            return ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"];
        },
        placeholder: "Select schedulers...",
        multiselect: true
    }
};

// Show example usage in a nice tooltip
function showExampleTooltip(paramType, targetElement) {
    const info = parameterInfo[paramType];
    if (!info || !info.example) return;
    
    // Remove any existing tooltip
    const existing = document.querySelector('.xyz-example-tooltip');
    if (existing) existing.remove();
    
    const tooltip = document.createElement("div");
    tooltip.className = "xyz-example-tooltip";
    tooltip.style.cssText = `
        position: absolute;
        background: #1e1e1e;
        border: 2px solid #4a90e2;
        border-radius: 8px;
        padding: 15px;
        z-index: 10000;
        max-width: 400px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        opacity: 0;
        transition: opacity 0.2s ease;
    `;
    
    const content = document.createElement("pre");
    content.style.cssText = `
        margin: 0;
        color: #ddd;
        font-size: 12px;
        line-height: 1.5;
        white-space: pre-wrap;
        font-family: monospace;
    `;
    content.textContent = info.example;
    
    tooltip.appendChild(content);
    
    // Position near the target element
    const rect = targetElement.getBoundingClientRect();
    tooltip.style.left = rect.left + "px";
    tooltip.style.top = (rect.bottom + 5) + "px";
    
    document.body.appendChild(tooltip);
    
    // Fade in
    requestAnimationFrame(() => {
        tooltip.style.opacity = "1";
    });
    
    // Auto-close
    const closeTooltip = () => {
        tooltip.style.opacity = "0";
        setTimeout(() => tooltip.remove(), 200);
    };
    
    setTimeout(closeTooltip, 5000);
    targetElement.addEventListener('blur', closeTooltip);
    targetElement.addEventListener('input', closeTooltip);
}

// Create multi-select dialog for file-based parameters
function showMultiSelectDialog(options, widget, helper) {
    // Create modal overlay
    const overlay = document.createElement("div");
    overlay.className = "xyz-multiselect-overlay";
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
    `;
    
    // Create dialog
    const dialog = document.createElement("div");
    dialog.className = "xyz-multiselect-dialog";
    dialog.style.cssText = `
        background: #1e1e1e;
        border: 2px solid #444;
        border-radius: 8px;
        padding: 20px;
        max-width: 500px;
        max-height: 70vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    `;
    
    // Title
    const title = document.createElement("h3");
    title.textContent = helper.placeholder || "Select Values";
    title.style.cssText = "margin: 0 0 15px 0; color: #fff;";
    dialog.appendChild(title);
    
    // Search input
    const searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.placeholder = "Search...";
    searchInput.className = "xyz-search-input";
    searchInput.style.cssText = `
        width: 100%;
        padding: 8px;
        margin-bottom: 10px;
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 4px;
        color: #fff;
    `;
    dialog.appendChild(searchInput);
    
    // Options container
    const optionsContainer = document.createElement("div");
    optionsContainer.style.cssText = `
        flex: 1;
        overflow-y: auto;
        border: 1px solid #444;
        border-radius: 4px;
        padding: 10px;
        background: #2a2a2a;
        max-height: 400px;
    `;
    
    // Get current values
    const currentValues = widget.value.split(',').map(v => v.trim()).filter(v => v);
    
    // Create checkboxes
    const checkboxes = [];
    options.forEach(option => {
        const label = document.createElement("label");
        label.className = "xyz-checkbox-option";
        label.style.cssText = `
            display: block;
            padding: 5px;
            cursor: pointer;
            color: #ddd;
            margin: 2px 0;
        `;
        
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = option;
        checkbox.checked = currentValues.includes(option);
        checkbox.style.marginRight = "8px";
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(option));
        
        checkboxes.push({ checkbox, label, option });
        optionsContainer.appendChild(label);
    });
    
    dialog.appendChild(optionsContainer);
    
    // Search functionality
    searchInput.addEventListener("input", () => {
        const search = searchInput.value.toLowerCase();
        checkboxes.forEach(({ label, option }) => {
            label.style.display = option.toLowerCase().includes(search) ? "block" : "none";
        });
    });
    
    // Buttons
    const buttonContainer = document.createElement("div");
    buttonContainer.className = "xyz-button-group";
    buttonContainer.style.cssText = `
        margin-top: 15px;
        display: flex;
        gap: 10px;
        justify-content: flex-end;
    `;
    
    const selectAllBtn = document.createElement("button");
    selectAllBtn.textContent = "Select All";
    selectAllBtn.className = "xyz-button-secondary";
    selectAllBtn.style.cssText = `
        padding: 8px 15px;
        background: #666;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    `;
    selectAllBtn.onclick = () => {
        checkboxes.forEach(({ checkbox, label }) => {
            if (label.style.display !== "none") {
                checkbox.checked = true;
            }
        });
    };
    
    const clearBtn = document.createElement("button");
    clearBtn.textContent = "Clear";
    clearBtn.className = "xyz-button-secondary";
    clearBtn.style.cssText = selectAllBtn.style.cssText;
    clearBtn.onclick = () => {
        checkboxes.forEach(({ checkbox }) => checkbox.checked = false);
    };
    
    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    cancelBtn.className = "xyz-button-secondary";
    cancelBtn.style.cssText = selectAllBtn.style.cssText;
    cancelBtn.onclick = () => document.body.removeChild(overlay);
    
    const applyBtn = document.createElement("button");
    applyBtn.textContent = "Apply";
    applyBtn.className = "xyz-button-primary";
    applyBtn.style.cssText = `
        padding: 8px 15px;
        background: #4a90e2;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    `;
    applyBtn.onclick = () => {
        const selected = checkboxes
            .filter(({ checkbox }) => checkbox.checked)
            .map(({ checkbox }) => checkbox.value);
        widget.value = selected.join(", ");
        widget.callback?.(widget.value);
        document.body.removeChild(overlay);
    };
    
    buttonContainer.appendChild(selectAllBtn);
    buttonContainer.appendChild(clearBtn);
    buttonContainer.appendChild(cancelBtn);
    buttonContainer.appendChild(applyBtn);
    dialog.appendChild(buttonContainer);
    
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    
    // Focus search
    searchInput.focus();
    
    // Close on escape
    const handleEscape = (e) => {
        if (e.key === "Escape") {
            document.body.removeChild(overlay);
            document.removeEventListener("keydown", handleEscape);
        }
    };
    document.addEventListener("keydown", handleEscape);
}

// Main extension
app.registerExtension({
    name: "ComfyAssets.XYZPlotController",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "XYZPlotController") {
            // Add setup method
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Add our UI enhancements
                setTimeout(() => {
                    setupEnhancedUI(this);
                }, 100);
            };
        }
    }
});

function setupEnhancedUI(node) {
    // Setup for each axis
    ['x_axis_type', 'y_axis_type', 'z_axis_type'].forEach(axisName => {
        const typeWidget = node.widgets.find(w => w.name === axisName);
        if (!typeWidget) return;
        
        const axisPrefix = axisName.split('_')[0];
        const valueWidgetName = `${axisPrefix}_values`;
        
        // Override callback
        const originalCallback = typeWidget.callback;
        typeWidget.callback = function(value) {
            if (originalCallback) {
                originalCallback.call(this, value);
            }
            
            // Update value widget based on type
            updateValueWidget(node, valueWidgetName, value);
        };
        
        // Initial setup
        if (typeWidget.value && typeWidget.value !== 'none') {
            updateValueWidget(node, valueWidgetName, typeWidget.value);
        }
    });
    
    // Add total image count display
    addImageCountDisplay(node);
}

function updateValueWidget(node, widgetName, paramType) {
    const widget = node.widgets.find(w => w.name === widgetName);
    if (!widget) return;
    
    const helper = parameterHelpers[paramType];
    const info = parameterInfo[paramType];
    
    // Remove previous enhancements
    const parent = widget.element?.parentElement;
    if (parent) {
        const buttons = parent.querySelectorAll('button.xyz-select-btn');
        buttons.forEach(btn => btn.remove());
    }
    
    if (!info || paramType === 'none') return;
    
    // Update placeholder
    widget.element.placeholder = info.example ? 
        info.example.split('\n')[0] : 
        `Enter ${paramType} values...`;
    
    // Add select button for file-based parameters
    if (helper && helper.getOptions && widget.element) {
        const selectBtn = document.createElement("button");
        selectBtn.className = "xyz-select-btn";
        selectBtn.textContent = "📁 Select Values";
        selectBtn.style.cssText = `
            margin: 5px 0;
            padding: 5px 10px;
            background: #4a90e2;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            display: block;
        `;
        
        selectBtn.onclick = async () => {
            const options = await helper.getOptions();
            showMultiSelectDialog(options, widget, helper);
        };
        
        widget.element.parentElement.appendChild(selectBtn);
    }
    
    // Add example tooltip on focus
    if (info.example && widget.element) {
        widget.element.addEventListener('focus', () => {
            showExampleTooltip(paramType, widget.element);
        });
    }
    
    // Add validation for numeric types
    if (['cfg_scale', 'steps', 'clip_skip', 'seed', 'denoise', 'flux_guidance'].includes(paramType)) {
        widget.element.addEventListener('input', () => {
            const value = widget.element.value.trim();
            let isValid = true;
            
            if (value) {
                const rangePattern = /^\d+(\.\d+)?:\d+(\.\d+)?(:\d+(\.\d+)?)?$/;
                const listPattern = /^[\d\.\s,]+$/;
                isValid = rangePattern.test(value) || listPattern.test(value);
            }
            
            widget.element.style.borderColor = isValid ? "#4ecdc4" : "#ff6b6b";
        });
    }
}

function addImageCountDisplay(node) {
    // Find or create display widget
    let countWidget = node.widgets.find(w => w.name === "_image_count");
    if (!countWidget) {
        countWidget = node.addWidget("text", "_image_count", "Total Images: 0", () => {}, {});
        countWidget.element.readOnly = true;
        countWidget.element.style.textAlign = "center";
        countWidget.element.style.fontWeight = "bold";
        countWidget.element.style.background = "#2a2a2a";
    }
    
    // Monitor value changes
    const updateCount = () => {
        let xCount = 1, yCount = 1, zCount = 1;
        
        ['x', 'y', 'z'].forEach(axis => {
            const typeWidget = node.widgets.find(w => w.name === `${axis}_axis_type`);
            const valueWidget = node.widgets.find(w => w.name === `${axis}_values`);
            
            if (typeWidget?.value && typeWidget.value !== 'none' && valueWidget?.value) {
                const values = valueWidget.value.trim();
                if (values.includes(':')) {
                    // Parse range
                    const parts = values.split(':');
                    if (parts.length >= 2) {
                        const start = parseFloat(parts[0]);
                        const stop = parseFloat(parts[1]);
                        const step = parts[2] ? parseFloat(parts[2]) : 1;
                        const count = Math.floor((stop - start) / step) + 1;
                        if (axis === 'x') xCount = count;
                        else if (axis === 'y') yCount = count;
                        else if (axis === 'z') zCount = count;
                    }
                } else {
                    // Count comma-separated values
                    const count = values.split(',').filter(v => v.trim()).length;
                    if (axis === 'x') xCount = count || 1;
                    else if (axis === 'y') yCount = count || 1;
                    else if (axis === 'z') zCount = count || 1;
                }
            }
        });
        
        const total = xCount * yCount * zCount;
        countWidget.value = `Total Images: ${total}`;
        
        // Color based on count
        if (total > 100) {
            countWidget.element.style.color = "#ff6b6b";
            countWidget.value += " ⚠️ Large batch!";
        } else if (total > 50) {
            countWidget.element.style.color = "#ffaa00";
        } else {
            countWidget.element.style.color = "#4ecdc4";
        }
    };
    
    // Add listeners
    node.widgets.forEach(w => {
        if (w.name.includes('_values') || w.name.includes('_axis_type')) {
            w.callback = (() => {
                const original = w.callback;
                return function() {
                    if (original) original.apply(this, arguments);
                    updateCount();
                };
            })();
        }
    });
    
    // Initial update
    updateCount();
}