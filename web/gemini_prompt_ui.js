import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

app.registerExtension({
    name: "ComfyAssets.GeminiPrompt",

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "GeminiPrompt") {
            // Add visual enhancements to the node
            const onNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function() {
                const result = onNodeCreated?.apply(this, arguments);

                // Store reference to widgets
                this.promptTypeWidget = this.widgets.find(w => w.name === "prompt_type");
                this.modelWidget = this.widgets.find(w => w.name === "model");
                this.apiKeyWidget = this.widgets.find(w => w.name === "api_key");
                this.customPromptWidget = this.widgets.find(w => w.name === "custom_prompt");

                // Add helper text button
                const helpButton = this.addWidget("button", "Help / API Setup", null, () => {
                    this.showHelpDialog();
                });

                // Style the button
                helpButton.serialize = false;

                // Add refresh models button
                const refreshButton = this.addWidget("button", "Refresh Model List", null, () => {
                    this.refreshModelList();
                });
                refreshButton.serialize = false;

                // Add status indicator
                this.status = this.addWidget("text", "status", "Ready", () => {}, {
                    serialize: false
                });
                this.status.disabled = true;

                // Update custom prompt visibility based on selection
                if (this.promptTypeWidget && this.customPromptWidget) {
                    const originalCallback = this.promptTypeWidget.callback;
                    this.promptTypeWidget.callback = (value) => {
                        if (originalCallback) originalCallback.call(this.promptTypeWidget, value);
                        this.updateCustomPromptVisibility();
                    };
                }

                return result;
            };

            // Add method to show help dialog
            nodeType.prototype.showHelpDialog = function() {
                const helpContent = `
                    <div style="padding: 20px; max-width: 600px;">
                        <h2>Gemini Prompt Engineer Setup</h2>

                        <h3>1. Get API Key</h3>
                        <p>Get your free API key from: <a href="https://makersuite.google.com/app/apikey" target="_blank">Google AI Studio</a></p>

                        <h3>2. Set API Key</h3>
                        <p>Choose one of these methods:</p>
                        <ul>
                            <li><strong>Environment Variable:</strong> Set GEMINI_API_KEY in your system</li>
                            <li><strong>Config File:</strong> Create gemini_config.json in ComfyUI root with {"api_key": "your-key"}</li>
                            <li><strong>Node Input:</strong> Enter directly in the api_key field</li>
                        </ul>

                        <h3>3. Install Dependencies</h3>
                        <code>pip install google-generativeai</code>

                        <h3>Prompt Types</h3>
                        <ul>
                            <li><strong>FLUX:</strong> Detailed artistic prompts with quality markers</li>
                            <li><strong>SDXL:</strong> Positive/negative prompt pairs with weights</li>
                            <li><strong>Danbooru:</strong> Anime-style booru tags</li>
                            <li><strong>Video:</strong> Motion and temporal descriptions</li>
                        </ul>

                        <h3>Gemini Models</h3>
                        <ul>
                            <li><strong>gemini-1.5-flash:</strong> Fast and efficient (recommended for most uses)</li>
                            <li><strong>gemini-1.5-flash-8b:</strong> Smaller and faster, good for simple prompts</li>
                            <li><strong>gemini-1.5-pro:</strong> Most capable, best quality results</li>
                            <li><strong>gemini-1.0-pro:</strong> Previous generation, stable option</li>
                        </ul>

                        <h3>Custom Prompts</h3>
                        <p>You can override any template by entering your own system prompt in the custom_prompt field.</p>
                    </div>
                `;

                app.ui.dialog.show(helpContent);
            };

            // Add method to update custom prompt visibility
            nodeType.prototype.updateCustomPromptVisibility = function() {
                // You could implement logic here to show/hide custom prompt based on selection
                // For now, it's always visible but this method provides extensibility
            };

            // Add method to refresh model list
            nodeType.prototype.refreshModelList = function() {
                if (this.status) {
                    this.status.value = "Refreshing models...";
                }

                // Set the refresh_models flag
                const refreshWidget = this.widgets.find(w => w.name === "refresh_models");
                if (refreshWidget) {
                    refreshWidget.value = true;
                }

                // Show message
                alert("Model list will refresh on next execution. Make sure API key is set and run the node.");

                if (this.status) {
                    setTimeout(() => {
                        this.status.value = "Ready - Run node to refresh";
                    }, 2000);
                }
            };

            // Override execute to show status
            const onExecute = nodeType.prototype.onExecute;
            nodeType.prototype.onExecute = function() {
                if (this.status) {
                    this.status.value = "Processing...";
                }
                const result = onExecute?.apply(this, arguments);
                return result;
            };

            // Handle execution feedback
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                const result = onExecuted?.apply(this, arguments);

                if (this.status) {
                    // Check if there was an error in the output
                    const outputs = message.output;
                    if (outputs && outputs.prompt && outputs.prompt[0] && outputs.prompt[0].startsWith("Error:")) {
                        this.status.value = "Error - Check output";
                        this.bgcolor = "#552222";
                    } else {
                        this.status.value = "Success!";
                        this.bgcolor = "#225522";
                    }

                    // Reset color after delay
                    setTimeout(() => {
                        this.bgcolor = "";
                        if (this.status) {
                            this.status.value = "Ready";
                        }
                    }, 3000);
                }

                return result;
            };
        }
    },

    // Add custom styling
    async setup() {
        const style = document.createElement("style");
        style.textContent = `
            .gemini-prompt-help {
                background: #1a1a1a;
                border: 1px solid #444;
                border-radius: 8px;
                color: #fff;
            }

            .gemini-prompt-help h2 {
                color: #4285f4;
                margin-top: 0;
            }

            .gemini-prompt-help h3 {
                color: #8ab4f8;
                margin-top: 20px;
            }

            .gemini-prompt-help code {
                background: #333;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: monospace;
            }

            .gemini-prompt-help a {
                color: #8ab4f8;
                text-decoration: none;
            }

            .gemini-prompt-help a:hover {
                text-decoration: underline;
            }
        `;
        document.head.appendChild(style);
    }
});
