import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { COPY_MENU_LABEL, copyResultMessage } from './ui/prompt-enhancer.js';

const NODE_CLASS = 'KikoPromptEnhancer';
const COPY_ROUTE = '/kikotools/prompt_enhancer/copy';
const TOAST_LIFE_MS = 5000;

async function copyPrompt(node) {
    const baseModel = node.widgets?.find((widget) => widget.name === 'base_model')?.value;
    const response = await api.fetchApi(COPY_ROUTE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_model: baseModel }),
    });
    const body = await response.json().catch(() => null);
    const detail = copyResultMessage(response.status, body);
    const toast = app.extensionManager?.toast;
    if (!toast) return console.info(`Kiko Prompt Enhancer: ${detail}`);
    toast.add({ severity: response.ok ? 'success' : 'warn', summary: 'Kiko Prompt Enhancer', detail, life: TOAST_LIFE_MS });
}

app.registerExtension({
    name: 'kikotools.promptEnhancer',
    getNodeMenuItems(node) {
        if (node?.comfyClass !== NODE_CLASS) return [];
        return [null, { content: COPY_MENU_LABEL, callback: () => copyPrompt(node) }];
    },
});
