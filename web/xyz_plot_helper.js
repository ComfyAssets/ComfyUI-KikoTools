import { app } from "../../scripts/app.js";

// Helper information for each parameter type
const PARAM_HELP = {
    model: "Enter model names separated by commas:\nmodel1.safetensors, model2.safetensors",
    vae: "Enter VAE names separated by commas:\nAutomatic, vae1.safetensors, vae2.pt",
    lora: "Enter LoRA names separated by commas:\nNone, lora1.safetensors, lora2.safetensors",
    sampler: "Enter sampler names separated by commas:\neuler, euler_ancestral, dpm_2",
    scheduler: "Enter scheduler names separated by commas:\nnormal, karras, exponential",
    cfg_scale: "Enter values separated by commas: 5, 7.5, 10\nOr use range: 5:15:2.5",
    steps: "Enter values separated by commas: 20, 30, 40\nOr use range: 10:50:10",
    seed: "Enter values separated by commas: 42, 123, 456\nOr use range: 0:1000:100",
    denoise: "Enter values separated by commas: 0.3, 0.5, 0.7\nOr use range: 0.2:1.0:0.2",
    clip_skip: "Enter values separated by commas: 1, 2\nCommon values for SDXL",
    prompt: "Enter prompts separated by new lines:\nbeautiful sunset\nmystical forest\nfuturistic city"
};

app.registerExtension({
    name: "ComfyAssets.XYZPlotHelper",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "XYZPlotController") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function() {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }
                
                // Add widget callbacks to update help text
                const updateHelp = (axisPrefix) => {
                    const typeWidget = this.widgets.find(w => w.name === `${axisPrefix}_type`);
                    const valuesWidget = this.widgets.find(w => w.name === `${axisPrefix}_values`);
                    
                    if (typeWidget && valuesWidget) {
                        // Store original callback
                        const originalCallback = typeWidget.callback;
                        
                        // Add our callback
                        typeWidget.callback = function(value) {
                            // Update placeholder with help text
                            if (PARAM_HELP[value]) {
                                valuesWidget.inputEl.placeholder = PARAM_HELP[value];
                                valuesWidget.inputEl.title = PARAM_HELP[value];
                            } else {
                                valuesWidget.inputEl.placeholder = "No parameter selected";
                                valuesWidget.inputEl.title = "";
                            }
                            
                            // Call original callback
                            if (originalCallback) {
                                originalCallback.call(this, value);
                            }
                        };
                        
                        // Trigger initial update
                        typeWidget.callback(typeWidget.value);
                    }
                };
                
                // Setup help for all axes
                updateHelp('x');
                updateHelp('y');
                updateHelp('z');
                
                // Add a title to show total combinations
                const originalOnConnectionsChange = this.onConnectionsChange;
                this.onConnectionsChange = function(type, index, connected, link_info) {
                    if (originalOnConnectionsChange) {
                        originalOnConnectionsChange.call(this, type, index, connected, link_info);
                    }
                    
                    // Update title with total count
                    setTimeout(() => {
                        let totalImages = 1;
                        
                        ['x', 'y', 'z'].forEach(axis => {
                            const typeWidget = this.widgets.find(w => w.name === `${axis}_type`);
                            const valuesWidget = this.widgets.find(w => w.name === `${axis}_values`);
                            
                            if (typeWidget && valuesWidget && typeWidget.value !== 'none') {
                                const values = valuesWidget.value.trim();
                                if (values) {
                                    // Count values
                                    let count = 1;
                                    if (values.includes(':')) {
                                        // Range notation
                                        const parts = values.split(':');
                                        if (parts.length >= 2) {
                                            const start = parseFloat(parts[0]);
                                            const stop = parseFloat(parts[1]);
                                            const step = parts[2] ? parseFloat(parts[2]) : 1;
                                            count = Math.floor((stop - start) / step) + 1;
                                        }
                                    } else if (typeWidget.value === 'prompt') {
                                        count = values.split('\n').filter(v => v.trim()).length;
                                    } else {
                                        count = values.split(',').filter(v => v.trim()).length;
                                    }
                                    totalImages *= count;
                                }
                            }
                        });
                        
                        this.title = `XYZ Plot Controller (${totalImages} images)`;
                    }, 100);
                };
                
                // Set default title
                this.title = "XYZ Plot Controller (1 image)";
            };
        }
    }
});