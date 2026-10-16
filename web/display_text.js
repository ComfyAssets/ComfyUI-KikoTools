import { app } from '../../scripts/app.js';
import { registerDisplayNode } from './controllers/display-node.js';

app.registerExtension({
    name: 'ComfyAssets.DisplayText',
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === 'DisplayText') registerDisplayNode(nodeType, app, 'text');
    },
});
