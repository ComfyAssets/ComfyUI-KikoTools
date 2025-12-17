import { app } from "../../scripts/app.js";

/**
 * KikoTools Extensions - Adds utility features to all ComfyAssets nodes
 */
app.registerExtension({
    name: "ComfyAssets.Extensions",

    async setup() {
        // Wait for the canvas to be ready
        setTimeout(() => {
            const getNodeMenuOptions = LGraphCanvas.prototype.getNodeMenuOptions;

            LGraphCanvas.prototype.getNodeMenuOptions = function (node) {
                const options = getNodeMenuOptions.apply(this, arguments);

                // Only add our menu items to ComfyAssets nodes
                if (node.constructor.category && node.constructor.category.includes("ComfyAssets")) {
                    node.setDirtyCanvas(true, true);

                    // Find the position before the last separator (usually before "Remove")
                    let insertIndex = options.length - 1;
                    for (let i = options.length - 1; i >= 0; i--) {
                        if (options[i] === null) {
                            insertIndex = i;
                            break;
                        }
                    }

                    // Insert our custom menu items
                    const kikoOptions = [
                        null, // separator
                        {
                            content: "🎨 Node Dimensions",
                            callback: () => {
                                KikoToolsExtensions.showNodeDimensionsDialog(node);
                            }
                        }
                    ];

                    options.splice(insertIndex, 0, ...kikoOptions);
                }

                return options;
            };
        }, 500);
    }
});

/**
 * KikoTools Extensions utilities
 */
class KikoToolsExtensions {
    /**
     * Create a dialog for settings
     */
    static createDialog(htmlContent, onOK, onCancel) {
        const dialog = document.createElement("div");
        dialog.className = "kikotools-dialog";
        dialog.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #202020;
            border: 2px solid #444;
            border-radius: 8px;
            padding: 20px;
            z-index: 10000;
            font-family: Arial, sans-serif;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        `;

        dialog.innerHTML = htmlContent;

        // Create button container
        const buttonContainer = document.createElement("div");
        buttonContainer.style.cssText = `
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            margin-top: 15px;
        `;

        // Create OK button
        const okButton = document.createElement("button");
        okButton.textContent = "OK";
        okButton.style.cssText = `
            padding: 8px 20px;
            background: #4A90E2;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        `;
        okButton.onmouseover = () => okButton.style.background = "#5BA0F2";
        okButton.onmouseout = () => okButton.style.background = "#4A90E2";

        // Create Cancel button
        const cancelButton = document.createElement("button");
        cancelButton.textContent = "Cancel";
        cancelButton.style.cssText = `
            padding: 8px 20px;
            background: #666;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        `;
        cancelButton.onmouseover = () => cancelButton.style.background = "#777";
        cancelButton.onmouseout = () => cancelButton.style.background = "#666";

        buttonContainer.appendChild(cancelButton);
        buttonContainer.appendChild(okButton);
        dialog.appendChild(buttonContainer);

        // Dialog close function
        dialog.close = function() {
            if (dialog.parentNode) {
                dialog.parentNode.removeChild(dialog);
            }
        };

        // Get all inputs
        const inputs = Array.from(dialog.querySelectorAll("input, select"));

        // Handle keyboard events
        inputs.forEach(input => {
            input.addEventListener("keydown", function(e) {
                if (e.keyCode === 27) { // ESC
                    onCancel && onCancel();
                    dialog.close();
                } else if (e.keyCode === 13) { // Enter
                    onOK && onOK(dialog, inputs.map(input => input.value));
                    dialog.close();
                }
                e.stopPropagation();
            });
        });

        // Button click handlers
        okButton.onclick = () => {
            onOK && onOK(dialog, inputs.map(input => input.value));
            dialog.close();
        };

        cancelButton.onclick = () => {
            onCancel && onCancel();
            dialog.close();
        };

        // Add to document
        document.body.appendChild(dialog);

        // Focus first input
        if (inputs.length > 0) {
            inputs[0].focus();
            inputs[0].select();
        }

        return dialog;
    }

    /**
     * Show node dimensions dialog
     */
    static showNodeDimensionsDialog(node) {
        const nodeWidth = Math.round(node.size[0]);
        const nodeHeight = Math.round(node.size[1]);

        const htmlContent = `
            <div style="color: #ddd; margin-bottom: 15px;">
                <h3 style="margin: 0 0 15px 0; color: #4A90E2;">Node Dimensions</h3>
                <div style="display: flex; gap: 20px; align-items: center;">
                    <div>
                        <label style="display: block; margin-bottom: 5px; font-size: 12px; color: #aaa;">Width:</label>
                        <input type="number" class="width" value="${nodeWidth}"
                               style="width: 100px; padding: 5px; background: #333; color: white; border: 1px solid #555; border-radius: 4px;">
                    </div>
                    <div>
                        <label style="display: block; margin-bottom: 5px; font-size: 12px; color: #aaa;">Height:</label>
                        <input type="number" class="height" value="${nodeHeight}"
                               style="width: 100px; padding: 5px; background: #333; color: white; border: 1px solid #555; border-radius: 4px;">
                    </div>
                </div>
                <div style="margin-top: 10px; font-size: 11px; color: #888;">
                    Tip: Minimum size will be enforced based on node content
                </div>
            </div>
        `;

        this.createDialog(
            htmlContent,
            function(dialog, values) {
                const widthValue = Number(values[0]) || nodeWidth;
                const heightValue = Number(values[1]) || nodeHeight;

                // Calculate minimum size based on node content
                const minSize = node.computeSize();

                // Apply new size (respecting minimums)
                node.setSize([
                    Math.max(minSize[0], widthValue),
                    Math.max(minSize[1], heightValue)
                ]);

                // Mark canvas as dirty to trigger redraw
                node.setDirtyCanvas(true, true);
            },
            null
        );
    }
}

// Export for global access
window.KikoToolsExtensions = KikoToolsExtensions;
