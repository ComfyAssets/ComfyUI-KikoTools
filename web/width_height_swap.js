import { app } from '../../scripts/app.js';
import { bindDimensionPresets, extractResolutionFromPreset, swapDimensions } from './ui/dimensions.js';
import { mountDimensionSwap } from './ui/dimension-swap.js';

app.registerExtension({
    name: 'comfyassets.WidthHeightSelector',
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== 'WidthHeightSelector') return;
        nodeType.prototype.createSwapButton = function () { return mountDimensionSwap(this, app); };
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            this.extractResolutionFromPreset = extractResolutionFromPreset;
            this.swapDimensions = () => swapDimensions(this, app);
            bindDimensionPresets(this, app);
            this.createSwapButton();
            return result;
        };
    },
});
