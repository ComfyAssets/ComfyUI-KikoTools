import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Helper to get available options for different parameter types
const parameterHelpers = {
    model: {
        getOptions: async () => {
            try {
                const resp = await fetch('/api/models');
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
                const resp = await fetch('/api/models');
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
                const resp = await fetch('/api/models');
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
    },
    
    cfg_scale: {
        example: "5, 7.5, 10, 12.5\n-- or --\n5:15:2.5",
        placeholder: "Enter CFG values or range (start:stop:step)",
        validate: (value) => {
            // Check if it's a valid number list or range
            const rangePattern = /^\d+(\.\d+)?:\d+(\.\d+)?(:\d+(\.\d+)?)?$/;
            const listPattern = /^[\d\.\s,]+$/;
            return rangePattern.test(value.trim()) || listPattern.test(value.trim());
        }
    },
    
    steps: {
        example: "20, 30, 40, 50\n-- or --\n10:50:10",
        placeholder: "Enter step counts or range",
        validate: (value) => {
            const rangePattern = /^\d+:\d+(:\d+)?$/;
            const listPattern = /^[\d\s,]+$/;
            return rangePattern.test(value.trim()) || listPattern.test(value.trim());
        }
    },
    
    clip_skip: {
        example: "1, 2, 3, 4",
        placeholder: "Enter clip skip values (typically 1-4)",
        validate: (value) => {
            const listPattern = /^[\d\s,]+$/;
            return listPattern.test(value.trim());
        }
    },
    
    seed: {
        example: "42, 123, 456, 789\n-- or --\n0:1000:100",
        placeholder: "Enter seed values or range",
        validate: (value) => {
            const rangePattern = /^\d+:\d+(:\d+)?$/;
            const listPattern = /^[\d\s,]+$/;
            return rangePattern.test(value.trim()) || listPattern.test(value.trim());
        }
    },
    
    denoise: {
        example: "0.5, 0.75, 1.0\n-- or --\n0.4:1.0:0.2",
        placeholder: "Enter denoise values (0.0-1.0)",
        validate: (value) => {
            const rangePattern = /^\d+(\.\d+)?:\d+(\.\d+)?(:\d+(\.\d+)?)?$/;
            const listPattern = /^[\d\.\s,]+$/;
            return rangePattern.test(value.trim()) || listPattern.test(value.trim());
        }
    },
    
    flux_guidance: {
        example: "1.0, 2.0, 3.5, 5.0\n-- or --\n1:5:0.5",
        placeholder: "Enter Flux guidance values",
        validate: (value) => {
            const rangePattern = /^\d+(\.\d+)?:\d+(\.\d+)?(:\d+(\.\d+)?)?$/;
            const listPattern = /^[\d\.\s,]+$/;
            return rangePattern.test(value.trim()) || listPattern.test(value.trim());
        }
    },
    
    prompt: {
        example: "a beautiful sunset over the ocean\na mystical forest at dawn\na futuristic city skyline\na cozy cottage in the mountains",
        placeholder: "Enter prompts (one per line)",
        multiline: true,
        validate: (value) => value.trim().length > 0
    }
};

// Create a custom widget for value selection
function createValueSelectorWidget(node, widgetName, axisType) {
    const widget = node.widgets.find(w => w.name === widgetName);
    if (!widget) return;
    
    const helper = parameterHelpers[axisType];
    if (!helper) return;
    
    // Store original widget
    const originalWidget = widget;
    
    // Create container for enhanced UI
    const container = document.createElement("div");
    container.className = "xyz-value-selector";
    container.style.cssText = `
        position: relative;
        margin: 5px 0;
    `;
    
    if (helper.getOptions) {
        // Create multi-select for file-based options
        createMultiSelect(container, helper, originalWidget);
    } else if (helper.example) {
        // Show example for numeric/text inputs
        createExampleHelper(container, helper, originalWidget);
    }
    
    // Replace widget element
    if (widget.inputEl && widget.inputEl.parentNode) {
        widget.inputEl.parentNode.insertBefore(container, widget.inputEl);
        container.appendChild(widget.inputEl);
    }
}

function createMultiSelect(container, helper, widget) {
    // Create select button
    const selectBtn = document.createElement("button");
    selectBtn.textContent = "Select Values...";
    selectBtn.style.cssText = `
        margin: 5px 0;
        padding: 5px 10px;
        background: #4a90e2;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
    `;
    
    selectBtn.onclick = async () => {
        const options = await helper.getOptions();
        showMultiSelectDialog(options, widget, helper.placeholder);
    };
    
    container.appendChild(selectBtn);
}

function createExampleHelper(container, helper, widget) {
    // Create example display
    const exampleDiv = document.createElement("div");
    exampleDiv.style.cssText = `
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 4px;
        padding: 8px;
        margin: 5px 0;
        font-size: 11px;
        color: #aaa;
        display: none;
    `;
    
    const exampleText = document.createElement("pre");
    exampleText.style.cssText = `
        margin: 0;
        font-family: monospace;
        white-space: pre-wrap;
    `;
    exampleText.textContent = `Example:\n${helper.example}`;
    exampleDiv.appendChild(exampleText);
    
    // Show/hide example based on focus
    widget.inputEl.addEventListener("focus", () => {
        exampleDiv.style.display = "block";
    });
    
    widget.inputEl.addEventListener("blur", () => {
        setTimeout(() => {
            exampleDiv.style.display = "none";
        }, 200);
    });
    
    // Update placeholder
    if (helper.placeholder) {
        widget.inputEl.placeholder = helper.placeholder;
    }
    
    // Add validation
    if (helper.validate) {
        widget.inputEl.addEventListener("input", () => {
            const isValid = helper.validate(widget.inputEl.value);
            widget.inputEl.style.borderColor = isValid ? "" : "#ff6b6b";
        });
    }
    
    container.appendChild(exampleDiv);
}

function showMultiSelectDialog(options, widget, placeholder) {
    // Create modal overlay
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
    title.textContent = placeholder || "Select Values";
    title.style.cssText = "margin: 0 0 15px 0; color: #fff;";
    dialog.appendChild(title);
    
    // Search input
    const searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.placeholder = "Search...";
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
        checkboxes.forEach(({ checkbox, label }) => {
            if (label.style.display !== "none") {
                checkbox.checked = true;
            }
        });
    };
    
    const clearBtn = document.createElement("button");
    clearBtn.textContent = "Clear";
    clearBtn.style.cssText = selectAllBtn.style.cssText;
    clearBtn.onclick = () => {
        checkboxes.forEach(({ checkbox }) => checkbox.checked = false);
    };
    
    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    cancelBtn.style.cssText = selectAllBtn.style.cssText;
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

// Register the extension
app.registerExtension({
    name: "ComfyAssets.XYZGridWidgets",
    
    async nodeCreated(node) {
        if (node.comfyClass === "XYZPlotController") {
            // Wait for widgets to be created
            setTimeout(() => {
                setupEnhancedWidgets(node);
            }, 100);
        }
    }
});

function setupEnhancedWidgets(node) {
    const axisTypes = ['x_axis_type', 'y_axis_type', 'z_axis_type'];
    
    axisTypes.forEach(axisType => {
        const typeWidget = node.widgets.find(w => w.name === axisType);
        if (!typeWidget) return;
        
        const axisPrefix = axisType.split('_')[0]; // 'x', 'y', or 'z'
        const valueWidgetName = `${axisPrefix}_values`;
        
        // Monitor axis type changes
        const originalCallback = typeWidget.callback;
        typeWidget.callback = function(value) {
            if (originalCallback) {
                originalCallback.call(this, value);
            }
            
            // Clear any existing enhancements
            const valueWidget = node.widgets.find(w => w.name === valueWidgetName);
            if (valueWidget && valueWidget.inputEl) {
                const container = valueWidget.inputEl.parentNode;
                if (container && container.className === "xyz-value-selector") {
                    // Remove enhancements
                    while (container.firstChild !== valueWidget.inputEl) {
                        container.removeChild(container.firstChild);
                    }
                    while (container.lastChild !== valueWidget.inputEl) {
                        container.removeChild(container.lastChild);
                    }
                }
            }
            
            // Add new enhancements based on type
            if (value && value !== "none") {
                setTimeout(() => {
                    createValueSelectorWidget(node, valueWidgetName, value);
                }, 50);
            }
        };
    });
}