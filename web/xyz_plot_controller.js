import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Parameter definitions
const PARAM_INFO = {
    none: { 
        description: "No parameter selected",
        hasOptions: false 
    },
    model: {
        description: "Checkpoint/Model files",
        hasOptions: true,
        inputNames: ['ckpt_name', 'checkpoint', 'model_name', 'unet_name']
    },
    vae: {
        description: "VAE models",
        hasOptions: true,
        inputNames: ['vae_name', 'vae'],
        addDefault: "Automatic"
    },
    lora: {
        description: "LoRA models",
        hasOptions: true,
        inputNames: ['lora_name', 'lora'],
        addDefault: "None"
    },
    sampler: {
        description: "Sampling algorithms",
        hasOptions: true,
        inputNames: ['sampler_name', 'sampler']
    },
    scheduler: {
        description: "Noise schedulers",
        hasOptions: true,
        inputNames: ['scheduler', 'scheduler_name']
    },
    cfg_scale: {
        description: "CFG Scale values",
        example: "Examples: 5, 7.5, 10\nRange: 5:15:2.5"
    },
    steps: {
        description: "Sampling steps",
        example: "Examples: 20, 30, 40\nRange: 10:50:10"
    },
    seed: {
        description: "Random seeds",
        example: "Examples: 42, 123, 456\nRange: 0:1000:100"
    },
    denoise: {
        description: "Denoising strength",
        example: "Examples: 0.3, 0.5, 0.7\nRange: 0.2:1.0:0.2"
    },
    flux_guidance: {
        description: "Flux guidance strength",
        example: "Examples: 1.0, 3.5, 5.0\nRange: 1:5:0.5"
    },
    prompt: {
        description: "Text prompts",
        example: "Enter one prompt per line:\n\na beautiful sunset\na mystical forest"
    }
};

// Get options for parameter types
async function getParameterOptions(paramType) {
    if (!PARAM_INFO[paramType]?.hasOptions) return [];
    
    try {
        const resp = await fetch('/object_info');
        const data = await resp.json();
        
        const inputNames = PARAM_INFO[paramType].inputNames || [paramType];
        let allOptions = [];
        
        // Search through all nodes
        for (const [nodeName, nodeData] of Object.entries(data)) {
            if (nodeData.input?.required) {
                for (const [inputName, inputDef] of Object.entries(nodeData.input.required)) {
                    if (inputNames.includes(inputName) && Array.isArray(inputDef[0])) {
                        allOptions = [...new Set([...allOptions, ...inputDef[0]])];
                    }
                }
            }
        }
        
        // Add default option if specified
        if (PARAM_INFO[paramType].addDefault) {
            allOptions.unshift(PARAM_INFO[paramType].addDefault);
        }
        
        return allOptions;
    } catch (e) {
        console.error(`Error fetching ${paramType} options:`, e);
        return [];
    }
}

// Create multi-select dialog
function showMultiSelectDialog(options, currentValues, paramType, onApply) {
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
        width: 90%;
        max-height: 70vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    `;
    
    // Title
    const title = document.createElement("h3");
    title.textContent = `Select ${paramType.charAt(0).toUpperCase() + paramType.slice(1)}s`;
    title.style.cssText = "margin: 0 0 15px 0; color: #4ecdc4; font-size: 16px;";
    dialog.appendChild(title);
    
    // Search box
    const searchBox = document.createElement("input");
    searchBox.type = "text";
    searchBox.placeholder = "Search...";
    searchBox.style.cssText = `
        padding: 8px;
        margin-bottom: 10px;
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 4px;
        color: #fff;
        font-size: 14px;
    `;
    dialog.appendChild(searchBox);
    
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
    
    const checkboxes = [];
    const labels = [];
    
    // Create checkboxes
    options.forEach(option => {
        const label = document.createElement("label");
        label.style.cssText = `
            display: block;
            padding: 8px;
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
        
        label.onmouseenter = () => label.style.background = "rgba(78, 205, 196, 0.1)";
        label.onmouseleave = () => label.style.background = "transparent";
        
        checkboxes.push(checkbox);
        labels.push(label);
        optionsContainer.appendChild(label);
    });
    
    dialog.appendChild(optionsContainer);
    
    // Search functionality
    searchBox.oninput = () => {
        const searchTerm = searchBox.value.toLowerCase();
        labels.forEach((label, i) => {
            const text = options[i].toLowerCase();
            label.style.display = text.includes(searchTerm) ? "block" : "none";
        });
    };
    
    // Buttons
    const buttonContainer = document.createElement("div");
    buttonContainer.style.cssText = `
        margin-top: 15px;
        display: flex;
        gap: 10px;
        justify-content: flex-end;
    `;
    
    const selectAllBtn = document.createElement("button");
    selectAllBtn.textContent = "Select All";
    selectAllBtn.style.cssText = `
        padding: 8px 15px;
        background: #666;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    `;
    selectAllBtn.onclick = () => {
        checkboxes.forEach(cb => {
            if (cb.parentElement.style.display !== "none") {
                cb.checked = true;
            }
        });
    };
    
    const clearBtn = document.createElement("button");
    clearBtn.textContent = "Clear All";
    clearBtn.style.cssText = `
        padding: 8px 15px;
        background: #666;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    `;
    clearBtn.onclick = () => {
        checkboxes.forEach(cb => cb.checked = false);
    };
    
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
        onApply(selected);
        document.body.removeChild(overlay);
    };
    
    buttonContainer.appendChild(selectAllBtn);
    buttonContainer.appendChild(clearBtn);
    buttonContainer.appendChild(cancelBtn);
    buttonContainer.appendChild(applyBtn);
    dialog.appendChild(buttonContainer);
    
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    
    // Focus search box
    searchBox.focus();
}

// Create the enhanced UI
function createEnhancedUI(node) {
    const container = document.createElement("div");
    container.className = "xyz-controller-ui";
    container.innerHTML = `
        <style>
            .xyz-controller-ui {
                font-family: Arial, sans-serif;
                padding: 5px;
                background: #1e1e1e;
                border-radius: 4px;
                color: #ddd;
            }
            .xyz-axis-group {
                margin-bottom: 12px;
                padding: 10px;
                background: #2a2a2a;
                border-radius: 4px;
                border: 1px solid #333;
            }
            .xyz-axis-header {
                font-weight: bold;
                color: #4ecdc4;
                margin-bottom: 8px;
                font-size: 12px;
            }
            .xyz-axis-row {
                display: flex;
                align-items: center;
                margin-bottom: 8px;
                gap: 8px;
            }
            .xyz-axis-label {
                width: 70px;
                font-size: 11px;
                color: #aaa;
            }
            .xyz-axis-select {
                flex: 1;
                padding: 4px;
                background: #333;
                border: 1px solid #444;
                border-radius: 3px;
                color: #fff;
                font-size: 11px;
                height: 24px;
            }
            .xyz-axis-values {
                width: 100%;
                margin-top: 8px;
                padding: 6px;
                background: #333;
                border: 1px solid #444;
                border-radius: 3px;
                color: #fff;
                font-size: 11px;
                min-height: 40px;
                max-height: 60px;
                resize: vertical;
            }
            .xyz-select-button {
                width: 100%;
                margin-top: 6px;
                padding: 6px;
                background: #4a90e2;
                color: white;
                border: none;
                border-radius: 3px;
                cursor: pointer;
                font-size: 11px;
                transition: all 0.2s;
            }
            .xyz-select-button:hover {
                background: #357abd;
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            .xyz-info-box {
                margin-top: 6px;
                padding: 6px 8px;
                background: #1a1a1a;
                border-radius: 3px;
                font-size: 10px;
                border: 1px solid #333;
            }
            .xyz-info-box strong {
                color: #4ecdc4;
                font-size: 10px;
            }
            .xyz-info-example {
                color: #888;
                font-style: italic;
                white-space: pre-wrap;
                margin-top: 3px;
                font-size: 9px;
            }
            .xyz-total-count {
                text-align: center;
                padding: 10px;
                background: #2a2a2a;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                color: #4ecdc4;
                border: 1px solid #333;
                margin-top: 5px;
            }
            .xyz-total-count.warning {
                color: #ffaa00;
            }
            .xyz-total-count.danger {
                color: #ff6b6b;
            }
        </style>
        
        <!-- X Axis -->
        <div class="xyz-axis-group">
            <div class="xyz-axis-header">X AXIS</div>
            <div class="xyz-axis-row">
                <span class="xyz-axis-label">Parameter:</span>
                <select class="xyz-axis-select" id="x_axis_type">
                    <option value="none">None</option>
                    <option value="model">Model</option>
                    <option value="vae">VAE</option>
                    <option value="lora">LoRA</option>
                    <option value="sampler">Sampler</option>
                    <option value="scheduler">Scheduler</option>
                    <option value="cfg_scale">CFG Scale</option>
                    <option value="steps">Steps</option>
                    <option value="seed">Seed</option>
                    <option value="denoise">Denoise</option>
                    <option value="flux_guidance">Flux Guidance</option>
                    <option value="prompt">Prompt</option>
                </select>
            </div>
            <textarea class="xyz-axis-values" id="x_values" placeholder="Values will appear here..."></textarea>
            <button class="xyz-select-button" id="x_select_btn" style="display: none;">Select Values</button>
            <div class="xyz-info-box" id="x_info" style="display: none;"></div>
        </div>
        
        <!-- Y Axis -->
        <div class="xyz-axis-group">
            <div class="xyz-axis-header">Y AXIS</div>
            <div class="xyz-axis-row">
                <span class="xyz-axis-label">Parameter:</span>
                <select class="xyz-axis-select" id="y_axis_type">
                    <option value="none">None</option>
                    <option value="model">Model</option>
                    <option value="vae">VAE</option>
                    <option value="lora">LoRA</option>
                    <option value="sampler">Sampler</option>
                    <option value="scheduler">Scheduler</option>
                    <option value="cfg_scale">CFG Scale</option>
                    <option value="steps">Steps</option>
                    <option value="seed">Seed</option>
                    <option value="denoise">Denoise</option>
                    <option value="flux_guidance">Flux Guidance</option>
                    <option value="prompt">Prompt</option>
                </select>
            </div>
            <textarea class="xyz-axis-values" id="y_values" placeholder="Values will appear here..."></textarea>
            <button class="xyz-select-button" id="y_select_btn" style="display: none;">Select Values</button>
            <div class="xyz-info-box" id="y_info" style="display: none;"></div>
        </div>
        
        <!-- Z Axis -->
        <div class="xyz-axis-group">
            <div class="xyz-axis-header">Z AXIS (Optional)</div>
            <div class="xyz-axis-row">
                <span class="xyz-axis-label">Parameter:</span>
                <select class="xyz-axis-select" id="z_axis_type">
                    <option value="none">None</option>
                    <option value="model">Model</option>
                    <option value="vae">VAE</option>
                    <option value="lora">LoRA</option>
                    <option value="sampler">Sampler</option>
                    <option value="scheduler">Scheduler</option>
                    <option value="cfg_scale">CFG Scale</option>
                    <option value="steps">Steps</option>
                    <option value="seed">Seed</option>
                    <option value="denoise">Denoise</option>
                    <option value="flux_guidance">Flux Guidance</option>
                    <option value="prompt">Prompt</option>
                </select>
            </div>
            <textarea class="xyz-axis-values" id="z_values" placeholder="Values will appear here..."></textarea>
            <button class="xyz-select-button" id="z_select_btn" style="display: none;">Select Values</button>
            <div class="xyz-info-box" id="z_info" style="display: none;"></div>
        </div>
        
        <!-- Total Count -->
        <div class="xyz-total-count" id="xyz_total_count">Total Images: 0</div>
    `;
    
    // Setup event handlers
    function setupAxisHandlers(axis) {
        const typeSelect = container.querySelector(`#${axis}_axis_type`);
        const valuesTextarea = container.querySelector(`#${axis}_values`);
        const selectBtn = container.querySelector(`#${axis}_select_btn`);
        const infoBox = container.querySelector(`#${axis}_info`);
        
        typeSelect.addEventListener('change', async () => {
            const paramType = typeSelect.value;
            const info = PARAM_INFO[paramType];
            
            // Update widget values
            const typeWidget = (node.originalWidgets || node.widgets).find(w => w.name === `${axis}_axis_type`);
            if (typeWidget) {
                typeWidget.value = paramType;
                typeWidget.callback?.(paramType);
            }
            
            if (!info || paramType === 'none') {
                selectBtn.style.display = 'none';
                infoBox.style.display = 'none';
                valuesTextarea.placeholder = 'Values will appear here...';
                return;
            }
            
            // Show info
            infoBox.style.display = 'block';
            infoBox.innerHTML = `
                <strong>${info.description}</strong>
                ${info.example ? `<div class="xyz-info-example">${info.example}</div>` : ''}
            `;
            
            // Show/hide select button
            if (info.hasOptions) {
                selectBtn.style.display = 'block';
                selectBtn.textContent = `📁 Select ${paramType.charAt(0).toUpperCase() + paramType.slice(1)}s`;
                valuesTextarea.placeholder = 'Click the button above to select values...';
            } else {
                selectBtn.style.display = 'none';
                valuesTextarea.placeholder = 'Enter values...';
            }
            
            updateTotalCount();
        });
        
        selectBtn.addEventListener('click', async () => {
            const paramType = typeSelect.value;
            const options = await getParameterOptions(paramType);
            const currentValues = valuesTextarea.value.split(',').map(v => v.trim()).filter(v => v);
            
            showMultiSelectDialog(options, currentValues, paramType, (selected) => {
                valuesTextarea.value = selected.join(', ');
                const valueWidget = (node.originalWidgets || node.widgets).find(w => w.name === `${axis}_values`);
                if (valueWidget) {
                    valueWidget.value = valuesTextarea.value;
                    valueWidget.callback?.(valuesTextarea.value);
                }
                updateTotalCount();
            });
        });
        
        valuesTextarea.addEventListener('input', () => {
            const valueWidget = (node.originalWidgets || node.widgets).find(w => w.name === `${axis}_values`);
            if (valueWidget) {
                valueWidget.value = valuesTextarea.value;
                valueWidget.callback?.(valuesTextarea.value);
            }
            updateTotalCount();
        });
    }
    
    function updateTotalCount() {
        let xCount = 1, yCount = 1, zCount = 1;
        
        ['x', 'y', 'z'].forEach(axis => {
            const typeSelect = container.querySelector(`#${axis}_axis_type`);
            const valuesTextarea = container.querySelector(`#${axis}_values`);
            
            if (typeSelect.value !== 'none' && valuesTextarea.value.trim()) {
                const values = valuesTextarea.value.trim();
                
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
        });
        
        const total = xCount * yCount * zCount;
        const totalDiv = container.querySelector('#xyz_total_count');
        totalDiv.textContent = `Total Images: ${total}`;
        
        totalDiv.className = 'xyz-total-count';
        if (total > 100) {
            totalDiv.className += ' danger';
            totalDiv.textContent += ' ⚠️';
        } else if (total > 50) {
            totalDiv.className += ' warning';
        }
    }
    
    // Initialize handlers
    ['x', 'y', 'z'].forEach(axis => setupAxisHandlers(axis));
    
    // Sync with existing widget values
    function syncFromWidgets() {
        ['x', 'y', 'z'].forEach(axis => {
            const widgets = node.originalWidgets || node.widgets;
            const typeWidget = widgets.find(w => w.name === `${axis}_axis_type`);
            const valueWidget = widgets.find(w => w.name === `${axis}_values`);
            
            if (typeWidget) {
                const typeSelect = container.querySelector(`#${axis}_axis_type`);
                typeSelect.value = typeWidget.value;
                typeSelect.dispatchEvent(new Event('change'));
            }
            
            if (valueWidget) {
                const valuesTextarea = container.querySelector(`#${axis}_values`);
                valuesTextarea.value = valueWidget.value;
            }
        });
        updateTotalCount();
    }
    
    setTimeout(syncFromWidgets, 100);
    
    return container;
}

app.registerExtension({
    name: "ComfyAssets.XYZPlotControllerV2",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "XYZPlotController") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Set initial size immediately
                this.size = [350, 550];
                
                // Store original widgets for later access but hide them completely
                this.originalWidgets = this.widgets.slice();
                
                // Remove all original widgets from display
                this.widgets = this.widgets.filter(w => {
                    // Hide DOM elements
                    if (w.element) {
                        w.element.style.display = 'none';
                        if (w.element.parentElement) {
                            w.element.parentElement.style.display = 'none';
                        }
                    }
                    if (w.inputEl) {
                        w.inputEl.style.display = 'none';
                        if (w.inputEl.parentElement) {
                            w.inputEl.parentElement.style.display = 'none';
                        }
                    }
                    // Keep only non-visual widgets
                    return false;
                });
                
                // Create custom UI
                const ui = createEnhancedUI(this);
                const customWidget = this.addDOMWidget("xyz_enhanced_ui", "div", ui, {
                    serialize: false,
                    hideOnZoom: false
                });
                
                // Add our custom widget to the widgets array
                this.widgets = [customWidget];
                
                // Make sure size is correct
                this.size = [350, 550];
            };
        }
    }
});