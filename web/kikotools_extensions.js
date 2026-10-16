import { app } from '../../scripts/app.js';
import { createLegacyDialog } from './ui/dialog.js';
import { showNodeDimensionsDialog } from './views/node-dimensions.js';

app.registerExtension({
    name: 'ComfyAssets.Extensions',
    getNodeMenuItems(node) {
        if (!node.constructor.category || !node.constructor.category.includes('ComfyAssets')) return [];
        return [null, {
            content: '🎨 Node Dimensions',
            callback: () => KikoToolsExtensions.showNodeDimensionsDialog(node),
        }];
    },
});

class KikoToolsExtensions {
    static createDialog(htmlContent, onOK, onCancel) {
        return createLegacyDialog(htmlContent, onOK, onCancel, app.ui.settings, app.canvas.canvas);
    }

    static showNodeDimensionsDialog(node) {
        return showNodeDimensionsDialog(node, app);
    }
}

window.KikoToolsExtensions = KikoToolsExtensions;
