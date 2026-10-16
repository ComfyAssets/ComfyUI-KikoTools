import { app } from '../../scripts/app.js';
import { registerDisplayNode } from './controllers/display-node.js';

app.registerExtension({
    name: 'ComfyAssets.DisplayAny',
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === 'DisplayAny') registerDisplayNode(nodeType, app, 'any');
    },
});
