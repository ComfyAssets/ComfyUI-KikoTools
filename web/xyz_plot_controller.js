import { app } from "../../scripts/app.js";

console.log("[XYZ Plot Controller] Extension loading...");

app.registerExtension({
    name: "ComfyAssets.XYZPlotController",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        console.log("[XYZ Plot Controller] beforeRegisterNodeDef called for:", nodeData.name);
        
        if (nodeData.name === "XYZPlotController") {
            console.log("[XYZ Plot Controller] Configuring XYZPlotController node...");
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                console.log("[XYZ Plot Controller] onNodeCreated called");
                
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Store reference to node
                this.parameterHelpers = createParameterHelpers();
                this.setupComplete = false;
                
                // Setup UI after a delay to ensure widgets are ready
                setTimeout(() => {
                    console.log("[XYZ Plot Controller] Setting up enhanced UI...");
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
                    console.log(`[XYZ Plot Controller] Axis type changed: ${name} = ${value}`);
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
        example: "Click 'Select Models' to choose multiple checkpoints",
        hasOptions: true
    },
    vae: {
        description: "VAE models",
        example: "Click 'Select Vaes' to choose VAEs\n'Automatic' uses the model's built-in VAE",
        hasOptions: true
    },
    lora: {
        description: "LoRA models",
        example: "Click 'Select Loras' to choose LoRAs\n'None' disables LoRA",
        hasOptions: true
    },
    sampler: {
        description: "Sampling algorithms",
        example: "Click 'Select Samplers' to choose sampling methods",
        hasOptions: true
    },
    scheduler: {
        description: "Noise schedulers",
        example: "Click 'Select Schedulers' to choose scheduler types",
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

// Generic function to find options from any node type
async function findOptionsForParameter(paramType) {
    try {
        console.log(`[XYZ Plot Controller] Finding options for ${paramType}`);
        const resp = await fetch('/object_info');
        const data = await resp.json();
        
        // Map parameter types to common input names
        const parameterMappings = {
            model: ['ckpt_name', 'checkpoint', 'model_name', 'unet_name'],
            vae: ['vae_name', 'vae'],
            lora: ['lora_name', 'lora'],
            sampler: ['sampler_name', 'sampler'],
            scheduler: ['scheduler', 'scheduler_name'],
            // Add more mappings as needed
        };
        
        const possibleNames = parameterMappings[paramType] || [paramType];
        let allOptions = [];
        
        // Search through all nodes for matching inputs
        for (const [nodeName, nodeData] of Object.entries(data)) {
            if (nodeData.input?.required) {
                for (const [inputName, inputDef] of Object.entries(nodeData.input.required)) {
                    // Check if this input name matches what we're looking for
                    if (possibleNames.includes(inputName)) {
                        // Check if it's a list (array as first element)
                        if (Array.isArray(inputDef[0])) {
                            console.log(`[XYZ Plot Controller] Found ${paramType} options in ${nodeName}.${inputName}`);
                            allOptions = [...new Set([...allOptions, ...inputDef[0]])];
                        }
                    }
                }
            }
        }
        
        console.log(`[XYZ Plot Controller] Total ${paramType} options found:`, allOptions.length);
        return allOptions;
    } catch (e) {
        console.error(`[XYZ Plot Controller] Error finding options for ${paramType}:`, e);
        return [];
    }
}

function createParameterHelpers() {
    return {
        model: {
            getOptions: async () => {
                const options = await findOptionsForParameter('model');
                return options.length > 0 ? options : [];
            }
        },
        vae: {
            getOptions: async () => {
                const options = await findOptionsForParameter('vae');
                // Add "Automatic" as first option for VAEs
                return ["Automatic", ...options];
            }
        },
        lora: {
            getOptions: async () => {
                const options = await findOptionsForParameter('lora');
                // Add "None" as first option for LoRAs
                return ["None", ...options];
            }
        },
        sampler: {
            getOptions: async () => {
                const options = await findOptionsForParameter('sampler');
                return options.length > 0 ? options : 
                    ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", 
                     "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", 
                     "dpmpp_sde", "dpmpp_2m", "dpmpp_2m_sde", "ddim", "uni_pc"];
            }
        },
        scheduler: {
            getOptions: async () => {
                const options = await findOptionsForParameter('scheduler');
                return options.length > 0 ? options :
                    ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"];
            }
        }
    };
}

function setupEnhancedUI(node) {
    console.log("[XYZ Plot Controller] setupEnhancedUI called for node:", node);
    
    // Add custom UI container
    const container = document.createElement("div");
    container.style.cssText = `
        padding: 10px;
        background: #1e1e1e;
        border-radius: 6px;
        margin: 10px 5px;
        border: 1px solid #333;
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
    
    console.log("[XYZ Plot Controller] Adding DOM widget...");
    
    // Add widget
    try {
        node.addDOMWidget("xyz_ui", "div", container);
        console.log("[XYZ Plot Controller] DOM widget added successfully");
    } catch (error) {
        console.error("[XYZ Plot Controller] Error adding DOM widget:", error);
    }
    
    // Setup axis handlers
    ['x', 'y', 'z'].forEach(axis => {
        const typeWidget = node.widgets.find(w => w.name === `${axis}_axis_type`);
        const valueWidget = node.widgets.find(w => w.name === `${axis}_values`);
        
        console.log(`[XYZ Plot Controller] Setting up ${axis} axis - type: ${typeWidget?.value}`);
        
        if (typeWidget && valueWidget) {
            // Initial setup
            if (typeWidget.value && typeWidget.value !== 'none') {
                updateValueWidget(node, `${axis}_values`, typeWidget.value);
            }
            
            // Force widget callback setup
            if (!typeWidget._xyz_initialized) {
                typeWidget._xyz_initialized = true;
                const originalCallback = typeWidget.callback;
                typeWidget.callback = function(value) {
                    console.log(`[XYZ Plot Controller] ${axis}_axis_type changed to: ${value}`);
                    updateValueWidget(node, `${axis}_values`, value);
                    updateImageCount(node);
                    if (originalCallback) {
                        originalCallback.call(this, value);
                    }
                };
            }
        }
    });
    
    // Initial count update
    updateImageCount(node);
}

function updateValueWidget(node, widgetName, paramType) {
    console.log(`[XYZ Plot Controller] updateValueWidget called: ${widgetName} -> ${paramType}`);
    
    const widget = node.widgets.find(w => w.name === widgetName);
    if (!widget) {
        console.error(`[XYZ Plot Controller] Widget ${widgetName} not found`);
        return;
    }
    
    // Always remove existing custom elements first
    const existingDiv = node.element?.querySelector(`#${widgetName}-custom`);
    if (existingDiv) {
        console.log(`[XYZ Plot Controller] Removing existing button for ${widgetName}`);
        existingDiv.remove();
    }
    
    const info = parameterInfo[paramType];
    if (!info || paramType === 'none') {
        // Hide info display if no parameter selected
        const infoDiv = node.element?.querySelector('#xyz-info-display');
        if (infoDiv) {
            infoDiv.style.display = 'none';
        }
        return;
    }
    
    // Update info display
    const infoDiv = node.element?.querySelector('#xyz-info-display');
    if (infoDiv) {
        infoDiv.style.display = 'block';
        infoDiv.innerHTML = `
            <div style="margin-bottom: 8px;">
                <strong style="color: #4ecdc4;">${paramType.toUpperCase()}</strong>
            </div>
            <div style="margin-bottom: 4px;">${info.description}</div>
            <small style="color: #888; white-space: pre-wrap;">${info.example || ''}</small>
        `;
    }
    
    // Add select button for options-based parameters
    if (info.hasOptions && node.parameterHelpers[paramType]) {
        console.log(`[XYZ Plot Controller] Creating select button for ${paramType}`);
        
        // Create new button
        let customDiv = document.createElement("div");
        customDiv.id = `${widgetName}-custom`;
        customDiv.style.cssText = `
            margin-top: 5px;
            margin-bottom: 15px;
            padding-bottom: 10px;
        `;
        
        const selectBtn = document.createElement("button");
        // Better pluralization
        const buttonLabels = {
            model: "Select Models",
            vae: "Select VAEs", 
            lora: "Select LoRAs",
            sampler: "Select Samplers",
            scheduler: "Select Schedulers"
        };
        selectBtn.textContent = `📁 ${buttonLabels[paramType] || `Select ${paramType}s`}`;
        selectBtn.style.cssText = `
            padding: 6px 12px;
            background: #4a90e2;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            width: 100%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transition: all 0.2s;
        `;
        
        selectBtn.onmouseenter = () => {
            selectBtn.style.background = "#357abd";
            selectBtn.style.transform = "translateY(-1px)";
            selectBtn.style.boxShadow = "0 3px 6px rgba(0,0,0,0.3)";
        };
        
        selectBtn.onmouseleave = () => {
            selectBtn.style.background = "#4a90e2";
            selectBtn.style.transform = "translateY(0)";
            selectBtn.style.boxShadow = "0 2px 4px rgba(0,0,0,0.2)";
        };
        
        selectBtn.onclick = async (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log(`[XYZ Plot Controller] Getting ${paramType} options...`);
            const options = await node.parameterHelpers[paramType].getOptions();
            console.log(`[XYZ Plot Controller] Got ${options.length} ${paramType} options:`, options);
            showSelectDialog(options, widget, paramType);
        };
        
        customDiv.appendChild(selectBtn);
        
        // Insert after widget
        const widgetElement = widget.inputEl || widget.element;
        console.log(`[XYZ Plot Controller] Widget element for ${widgetName}:`, widgetElement);
        console.log(`[XYZ Plot Controller] Widget parent:`, widgetElement?.parentElement);
        
        if (widgetElement && widgetElement.parentElement) {
            widgetElement.parentElement.appendChild(customDiv);
            console.log(`[XYZ Plot Controller] Button added for ${paramType}`);
            
            // Trigger node resize
            if (node.computeSize) {
                node.computeSize();
            }
            node.setDirtyCanvas(true, true);
        } else {
            console.error(`[XYZ Plot Controller] Could not find widget element for ${widgetName}`);
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
    console.log(`[XYZ Plot Controller] showSelectDialog called with ${options.length} options for ${paramType}`);
    
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
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    `;
    
    // Title
    const title = document.createElement("h3");
    const titleLabels = {
        model: "Select Models",
        vae: "Select VAEs", 
        lora: "Select LoRAs",
        sampler: "Select Samplers",
        scheduler: "Select Schedulers"
    };
    title.textContent = titleLabels[paramType] || `Select ${paramType} values`;
    title.style.cssText = "margin: 0 0 15px 0; color: #4ecdc4; font-size: 16px;";
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
            padding: 8px 10px;
            cursor: pointer;
            color: #ddd;
            transition: background 0.2s;
            border-radius: 4px;
            margin-bottom: 2px;
        `;
        
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = option;
        checkbox.checked = currentValues.includes(option);
        checkbox.style.cssText = `
            margin-right: 10px;
            width: 16px;
            height: 16px;
            cursor: pointer;
        `;
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(option));
        
        // Hover effect
        label.onmouseenter = () => {
            label.style.background = "rgba(78, 205, 196, 0.1)";
        };
        label.onmouseleave = () => {
            label.style.background = "transparent";
        };
        
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
    
    console.log("[XYZ Plot Controller] Dialog added to document body");
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

console.log("[XYZ Plot Controller] Extension module loaded successfully");