import { app } from "../../scripts/app.js";

// Load CSS
const link = document.createElement("link");
link.rel = "stylesheet";
link.type = "text/css";
link.href = "extensions/ComfyUI-KikoTools/css/xyz_grid.css";
document.head.appendChild(link);

// Parameter type information and examples
export const parameterInfo = {
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

// Create info panel for parameter type
function createInfoPanel(node, paramType) {
    const info = parameterInfo[paramType];
    if (!info || paramType === 'none') return null;
    
    const panel = document.createElement("div");
    panel.className = "xyz-grid-info";
    panel.innerHTML = `
        <div style="flex: 1;">
            <div style="font-weight: bold; margin-bottom: 4px;">${paramType.toUpperCase()}</div>
            <div style="font-size: 11px; color: #999; margin-bottom: 4px;">${info.description}</div>
            ${info.connection ? `<div style="font-size: 10px; color: #4ecdc4;">↗ ${info.connection}</div>` : ''}
        </div>
        ${info.range ? `
        <div style="text-align: right; font-size: 10px; color: #888;">
            Range: ${info.range.min}-${info.range.max}<br>
            Default: ${info.range.default}
        </div>
        ` : ''}
    `;
    
    return panel;
}

// Show example usage in a nice overlay
function showExampleOverlay(paramType, targetElement) {
    const info = parameterInfo[paramType];
    if (!info || !info.example) return;
    
    // Remove any existing overlay
    const existing = document.querySelector('.xyz-example-overlay');
    if (existing) existing.remove();
    
    const overlay = document.createElement("div");
    overlay.className = "xyz-example-overlay";
    overlay.style.cssText = `
        position: absolute;
        background: #1e1e1e;
        border: 2px solid #4a90e2;
        border-radius: 8px;
        padding: 15px;
        z-index: 1000;
        max-width: 400px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    `;
    
    const title = document.createElement("h4");
    title.style.cssText = "margin: 0 0 10px 0; color: #4a90e2;";
    title.textContent = `${paramType.toUpperCase()} - Usage Examples`;
    
    const content = document.createElement("pre");
    content.style.cssText = `
        margin: 0;
        color: #ddd;
        font-size: 12px;
        line-height: 1.5;
        white-space: pre-wrap;
    `;
    content.textContent = info.example;
    
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "×";
    closeBtn.style.cssText = `
        position: absolute;
        top: 10px;
        right: 10px;
        background: none;
        border: none;
        color: #999;
        font-size: 20px;
        cursor: pointer;
    `;
    closeBtn.onclick = () => overlay.remove();
    
    overlay.appendChild(title);
    overlay.appendChild(content);
    overlay.appendChild(closeBtn);
    
    // Position near the target element
    const rect = targetElement.getBoundingClientRect();
    overlay.style.left = rect.left + "px";
    overlay.style.top = (rect.bottom + 5) + "px";
    
    document.body.appendChild(overlay);
    
    // Auto-close on click outside
    setTimeout(() => {
        const closeOnClickOutside = (e) => {
            if (!overlay.contains(e.target)) {
                overlay.remove();
                document.removeEventListener('click', closeOnClickOutside);
            }
        };
        document.addEventListener('click', closeOnClickOutside);
    }, 100);
}

// Enhance the value input widget based on parameter type
export function enhanceValueWidget(node, widgetName, paramType) {
    const widget = node.widgets.find(w => w.name === widgetName);
    if (!widget || !widget.inputEl) return;
    
    const info = parameterInfo[paramType];
    if (!info) return;
    
    // Add info panel above the input
    const infoPanel = createInfoPanel(node, paramType);
    if (infoPanel && widget.inputEl.parentNode) {
        widget.inputEl.parentNode.insertBefore(infoPanel, widget.inputEl);
    }
    
    // Add example button if there's an example
    if (info.example) {
        const exampleBtn = document.createElement("button");
        exampleBtn.textContent = "Show Examples";
        exampleBtn.style.cssText = `
            margin: 5px 0;
            padding: 4px 10px;
            background: #3a3a3a;
            color: #aaa;
            border: 1px solid #555;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        `;
        exampleBtn.onclick = () => showExampleOverlay(paramType, widget.inputEl);
        
        if (widget.inputEl.parentNode) {
            widget.inputEl.parentNode.insertBefore(exampleBtn, widget.inputEl.nextSibling);
        }
    }
    
    // Add validation for numeric types
    if (['cfg_scale', 'steps', 'clip_skip', 'seed', 'denoise', 'flux_guidance'].includes(paramType)) {
        widget.inputEl.addEventListener('input', () => {
            const value = widget.inputEl.value.trim();
            let isValid = true;
            
            if (value) {
                // Check for range syntax or comma-separated numbers
                const rangePattern = /^\d+(\.\d+)?:\d+(\.\d+)?(:\d+(\.\d+)?)?$/;
                const listPattern = /^[\d\.\s,]+$/;
                
                isValid = rangePattern.test(value) || listPattern.test(value);
            }
            
            widget.inputEl.classList.toggle('xyz-value-input', true);
            widget.inputEl.classList.toggle('valid', isValid);
            widget.inputEl.classList.toggle('invalid', !isValid);
        });
    }
}

// Register UI enhancements
app.registerExtension({
    name: "ComfyAssets.XYZGridUI",
    
    async nodeCreated(node) {
        if (node.comfyClass === "XYZPlotController") {
            setupUIEnhancements(node);
        }
    }
});

function setupUIEnhancements(node) {
    // Monitor all axis type widgets
    ['x_axis_type', 'y_axis_type', 'z_axis_type'].forEach(axisName => {
        const widget = node.widgets.find(w => w.name === axisName);
        if (!widget) return;
        
        const axisPrefix = axisName.split('_')[0];
        const valueWidgetName = `${axisPrefix}_values`;
        
        // Enhance callback to update UI
        const originalCallback = widget.callback;
        widget.callback = function(value) {
            if (originalCallback) {
                originalCallback.call(this, value);
            }
            
            // Clear previous enhancements
            const valueWidget = node.widgets.find(w => w.name === valueWidgetName);
            if (valueWidget && valueWidget.inputEl) {
                // Remove any info panels or buttons
                const parent = valueWidget.inputEl.parentNode;
                const infoPanels = parent.querySelectorAll('.xyz-grid-info');
                const buttons = parent.querySelectorAll('button');
                infoPanels.forEach(el => el.remove());
                buttons.forEach(el => {
                    if (el.textContent === 'Show Examples') el.remove();
                });
            }
            
            // Add new enhancements
            if (value && value !== 'none') {
                setTimeout(() => {
                    enhanceValueWidget(node, valueWidgetName, value);
                }, 50);
            }
        };
        
        // Trigger for initial values
        if (widget.value && widget.value !== 'none') {
            setTimeout(() => {
                enhanceValueWidget(node, valueWidgetName, widget.value);
            }, 100);
        }
    });
}