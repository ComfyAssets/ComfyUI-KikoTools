import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "ComfyAssets.XYZPlotController",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "XYZPlotController") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Store reference to node
                this.parameterHelpers = createParameterHelpers();
                this.setupComplete = false;
                
                // Setup UI after a delay to ensure widgets are ready
                setTimeout(() => {
                    if (!this.setupComplete) {
                        setupEnhancedUI(this);
                        this.setupComplete = true;
                    }
                }, 100);
            };
            
            // Handle widget changes
            const onWidgetChange = nodeType.prototype.onWidgetChange;
            nodeType.prototype.onWidgetChange = function(name, value, oldValue, widget) {
                if (onWidgetChange) {
                    onWidgetChange.call(this, name, value, oldValue, widget);
                }
                
                // Handle axis type changes
                if (name.endsWith('_axis_type')) {
                    const axisPrefix = name.split('_')[0];
                    const valueWidgetName = `${axisPrefix}_values`;
                    updateValueWidget(this, valueWidgetName, value);
                }
                
                // Update total count for any value change
                if (name.includes('_values') || name.includes('_axis_type')) {
                    updateImageCount(this);
                }
            };
        }
    }
});

// Parameter information
const parameterInfo = {
    none: { description: "No parameter selected" },
    model: {
        description: "Checkpoint/Model files",
        example: "Use the Select button to choose from available models",
        hasOptions: true
    },
    vae: {
        description: "VAE models",
        example: "Select VAEs or use 'Automatic'",
        hasOptions: true
    },
    lora: {
        description: "LoRA models",
        example: "Select LoRAs (use 'None' for no LoRA)",
        hasOptions: true
    },
    sampler: {
        description: "Sampling algorithms",
        example: "Select from available samplers",
        hasOptions: true
    },
    scheduler: {
        description: "Noise schedulers",
        example: "Select scheduler types",
        hasOptions: true
    },
    cfg_scale: {
        description: "CFG Scale (Classifier-Free Guidance)",
        example: "Examples:\n5, 7.5, 10, 12.5\n5:15:2.5 (range from 5 to 15, step 2.5)"
    },
    steps: {
        description: "Denoising steps",
        example: "Examples:\n20, 30, 40, 50\n10:50:10 (range)"
    },
    clip_skip: {
        description: "CLIP layers to skip",
        example: "Common values: 1, 2\nSDXL typically uses 1 or 2"
    },
    seed: {
        description: "Random seed",
        example: "Examples:\n42, 123, 456\n0:1000:100 (range)"
    },
    denoise: {
        description: "Denoising strength",
        example: "Examples:\n0.3, 0.5, 0.7, 1.0\n0.2:1.0:0.2 (range)"
    },
    flux_guidance: {
        description: "Flux guidance strength",
        example: "Examples:\n1.0, 2.0, 3.5, 5.0\n1:5:0.5 (range)"
    },
    prompt: {
        description: "Text prompts (one per line)",
        example: "Enter different prompts, one per line:\n\na beautiful sunset\na mystical forest\na futuristic city"
    }
};

function createParameterHelpers() {
    return {
        model: {
            getOptions: async () => {
                try {
                    const resp = await fetch('/api/models');
                    const data = await resp.json();
                    return data.checkpoints || [];
                } catch (e) {
                    return [];
                }
            }
        },
        vae: {
            getOptions: async () => {
                try {
                    const resp = await fetch('/api/models');
                    const data = await resp.json();
                    return ["Automatic", ...(data.vae || [])];
                } catch (e) {
                    return ["Automatic"];
                }
            }
        },
        lora: {
            getOptions: async () => {
                try {
                    const resp = await fetch('/api/models');
                    const data = await resp.json();
                    return ["None", ...(data.loras || [])];
                } catch (e) {
                    return ["None"];
                }
            }
        },
        sampler: {
            getOptions: async () => {
                // Try to get from KSampler definition
                if (window.LiteGraph && window.LiteGraph.registered_node_types) {
                    const ksampler = window.LiteGraph.registered_node_types["KSampler"];
                    if (ksampler?.nodeData?.input?.required?.sampler_name?.[0]) {
                        return ksampler.nodeData.input.required.sampler_name[0];
                    }
                }
                return ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", 
                        "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", 
                        "dpmpp_sde", "dpmpp_2m", "dpmpp_2m_sde", "ddim", "uni_pc"];
            }
        },
        scheduler: {
            getOptions: async () => {
                if (window.LiteGraph && window.LiteGraph.registered_node_types) {
                    const ksampler = window.LiteGraph.registered_node_types["KSampler"];
                    if (ksampler?.nodeData?.input?.required?.scheduler?.[0]) {
                        return ksampler.nodeData.input.required.scheduler[0];
                    }
                }
                return ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"];
            }
        }
    };
}

function setupEnhancedUI(node) {
    // Add custom UI container
    const container = document.createElement("div");
    container.style.cssText = `
        padding: 10px;
        background: #1e1e1e;
        border-radius: 6px;
        margin: 5px;
    `;
    
    // Add info display
    const infoDiv = document.createElement("div");
    infoDiv.id = "xyz-info-display";
    infoDiv.style.cssText = `
        background: #2a2a2a;
        padding: 8px;
        border-radius: 4px;
        margin-bottom: 10px;
        font-size: 12px;
        color: #ccc;
        display: none;
    `;
    container.appendChild(infoDiv);
    
    // Add total count display
    const countDiv = document.createElement("div");
    countDiv.id = "xyz-count-display";
    countDiv.style.cssText = `
        background: #2a2a2a;
        padding: 8px;
        border-radius: 4px;
        text-align: center;
        font-weight: bold;
        color: #4ecdc4;
    `;
    countDiv.textContent = "Total Images: 0";
    container.appendChild(countDiv);
    
    // Add widget
    node.addDOMWidget("xyz_ui", "div", container);
    
    // Setup axis handlers
    ['x', 'y', 'z'].forEach(axis => {
        const typeWidget = node.widgets.find(w => w.name === `${axis}_axis_type`);
        const valueWidget = node.widgets.find(w => w.name === `${axis}_values`);
        
        if (typeWidget && valueWidget) {
            // Initial setup
            if (typeWidget.value && typeWidget.value !== 'none') {
                updateValueWidget(node, `${axis}_values`, typeWidget.value);
            }
        }
    });
    
    // Initial count update
    updateImageCount(node);
}

function updateValueWidget(node, widgetName, paramType) {
    const widget = node.widgets.find(w => w.name === widgetName);
    if (!widget) return;
    
    const info = parameterInfo[paramType];
    if (!info || paramType === 'none') {
        // Clear any custom elements
        const customDiv = node.element?.querySelector(`#${widgetName}-custom`);
        if (customDiv) customDiv.remove();
        return;
    }
    
    // Update info display
    const infoDiv = node.element?.querySelector('#xyz-info-display');
    if (infoDiv) {
        infoDiv.style.display = 'block';
        infoDiv.innerHTML = `
            <strong>${paramType.toUpperCase()}</strong><br>
            ${info.description}<br>
            <small style="color: #888;">${info.example || ''}</small>
        `;
    }
    
    // Add select button for options-based parameters
    if (info.hasOptions && node.parameterHelpers[paramType]) {
        // Remove existing button
        let customDiv = node.element?.querySelector(`#${widgetName}-custom`);
        if (customDiv) customDiv.remove();
        
        // Create new button
        customDiv = document.createElement("div");
        customDiv.id = `${widgetName}-custom`;
        customDiv.style.marginTop = "5px";
        
        const selectBtn = document.createElement("button");
        selectBtn.textContent = "📁 Select Values";
        selectBtn.style.cssText = `
            padding: 5px 10px;
            background: #4a90e2;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            width: 100%;
        `;
        
        selectBtn.onclick = async () => {
            const options = await node.parameterHelpers[paramType].getOptions();
            showSelectDialog(options, widget, paramType);
        };
        
        customDiv.appendChild(selectBtn);
        
        // Insert after widget
        const widgetElement = widget.inputEl || widget.element;
        if (widgetElement && widgetElement.parentElement) {
            widgetElement.parentElement.appendChild(customDiv);
        }
    }
    
    // Add validation for numeric types
    if (['cfg_scale', 'steps', 'clip_skip', 'seed', 'denoise', 'flux_guidance'].includes(paramType)) {
        if (widget.inputEl) {
            widget.inputEl.addEventListener('input', () => {
                const value = widget.inputEl.value.trim();
                let isValid = true;
                
                if (value) {
                    const rangePattern = /^\d+(\.\d+)?:\d+(\.\d+)?(:\d+(\.\d+)?)?$/;
                    const listPattern = /^[\d\.\s,]+$/;
                    isValid = rangePattern.test(value) || listPattern.test(value);
                }
                
                widget.inputEl.style.borderColor = isValid ? "#4ecdc4" : "#ff6b6b";
            });
        }
    }
}

function showSelectDialog(options, widget, paramType) {
    // Create overlay
    const overlay = document.createElement("div");
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
    title.textContent = `Select ${paramType} values`;
    title.style.cssText = "margin: 0 0 15px 0; color: #fff;";
    dialog.appendChild(title);
    
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
        label.style.cssText = `
            display: block;
            padding: 5px;
            cursor: pointer;
            color: #ddd;
        `;
        
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = option;
        checkbox.checked = currentValues.includes(option);
        checkbox.style.marginRight = "8px";
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(option));
        
        checkboxes.push(checkbox);
        optionsContainer.appendChild(label);
    });
    
    dialog.appendChild(optionsContainer);
    
    // Buttons
    const buttonContainer = document.createElement("div");
    buttonContainer.style.cssText = `
        margin-top: 15px;
        display: flex;
        gap: 10px;
        justify-content: flex-end;
    `;
    
    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    cancelBtn.style.cssText = `
        padding: 8px 15px;
        background: #666;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    `;
    cancelBtn.onclick = () => document.body.removeChild(overlay);
    
    const applyBtn = document.createElement("button");
    applyBtn.textContent = "Apply";
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
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        widget.value = selected.join(", ");
        widget.callback?.(widget.value);
        document.body.removeChild(overlay);
    };
    
    buttonContainer.appendChild(cancelBtn);
    buttonContainer.appendChild(applyBtn);
    dialog.appendChild(buttonContainer);
    
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
}

function updateImageCount(node) {
    const countDiv = node.element?.querySelector('#xyz-count-display');
    if (!countDiv) return;
    
    let xCount = 1, yCount = 1, zCount = 1;
    
    ['x', 'y', 'z'].forEach(axis => {
        const typeWidget = node.widgets.find(w => w.name === `${axis}_axis_type`);
        const valueWidget = node.widgets.find(w => w.name === `${axis}_values`);
        
        if (typeWidget?.value && typeWidget.value !== 'none' && valueWidget?.value) {
            const values = valueWidget.value.trim();
            if (values) {
                // Check for range syntax
                if (values.includes(':')) {
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
                    if (axis === 'x') xCount = count;
                    else if (axis === 'y') yCount = count;
                    else if (axis === 'z') zCount = count;
                }
            }
        }
    });
    
    const total = xCount * yCount * zCount;
    countDiv.textContent = `Total Images: ${total}`;
    
    // Update color based on count
    if (total > 100) {
        countDiv.style.color = "#ff6b6b";
        countDiv.textContent += " ⚠️";
    } else if (total > 50) {
        countDiv.style.color = "#ffaa00";
    } else {
        countDiv.style.color = "#4ecdc4";
    }
}