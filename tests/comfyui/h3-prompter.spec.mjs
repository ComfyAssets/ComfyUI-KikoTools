import { test, expect } from '../../tools/testing/node_modules/@playwright/test/index.mjs';
import { installHost } from './host-setup.mjs';

installHost(test, expect);

const LONG_PROMPT = Array.from({ length: 40 }, (_, i) => `Sentence ${i} of a long prompt about the subject.`).join(' ');
const LONG_NOTES = Array.from({ length: 30 }, (_, i) => `Note line ${i} about the picture.`).join(' ');

// Box heights of the panel, its prompt box and its notes box, and the node height.
async function layout(page) {
    return page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(item => item.type === 'KikoH3ReferencePrompter');
        const panel = document.querySelector('.ca-h3-prompter');
        const box = selector => panel.querySelector(selector).getBoundingClientRect().height / app.canvas.ds.scale;
        return {
            node: node.size[1],
            text: box('.ca-h3-text'),
            notes: box('.ca-h3-notes-text'),
            overflow: panel.scrollHeight - panel.clientHeight,
        };
    });
}

for (const vueNodes of [false, true]) {
    test(`H3 prompter keeps its text boxes readable and grows with the node (vue nodes ${vueNodes})`, async ({ page }) => {
        await page.evaluate(async vueNodes => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', vueNodes);
        }, vueNodes);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(vueNodes);
        await page.evaluate(async ({ prompt, notes }) => {
            const { app } = await import('/scripts/app.js');
            const node = LiteGraph.createNode('KikoH3ReferencePrompter');
            app.graph.add(node);
            app.canvas.centerOnNode(node);
            node.onExecuted({ h3_prompts: [prompt], h3_notes: [notes] });
        }, { prompt: LONG_PROMPT, notes: LONG_NOTES });
        const panel = page.locator('.ca-h3-prompter');
        await expect(panel.locator('.ca-h3-text')).toHaveText(LONG_PROMPT);
        // A long prompt gets a readable box, and nothing spills out of the panel.
        await expect.poll(async () => (await layout(page)).text).toBeGreaterThanOrEqual(200);
        await expect.poll(async () => (await layout(page)).overflow).toBeLessThanOrEqual(1);

        // The node grew, so bring it back into view before clicking inside it.
        await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            app.canvas.ds.scale = 0.7;
            app.canvas.centerOnNode(app.graph._nodes.find(item => item.type === 'KikoH3ReferencePrompter'));
            app.canvas.setDirty(true, true);
        });
        await panel.locator('.ca-h3-notes summary').click();
        await expect.poll(async () => (await layout(page)).notes).toBeGreaterThanOrEqual(100);
        await expect.poll(async () => (await layout(page)).text).toBeGreaterThanOrEqual(120);
        await expect.poll(async () => (await layout(page)).overflow).toBeLessThanOrEqual(1);

        // Making the node taller gives the prompt box more room. Both renderers share
        // the extra height with the draft's own text box, so the panel gets about half.
        const before = await layout(page);
        await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            const node = app.graph._nodes.find(item => item.type === 'KikoH3ReferencePrompter');
            node.setSize([node.size[0], node.size[1] + 300]);
            app.canvas.setDirty(true, true);
        });
        await expect.poll(async () => (await layout(page)).text).toBeGreaterThanOrEqual(before.text + (vueNodes ? 60 : 120));
        await expect.poll(async () => (await layout(page)).overflow).toBeLessThanOrEqual(1);
    });
}

// A workflow saved before the draft became a socket-only input stores the draft
// as the first widget value; loading it must not shift the other values.
const LEGACY_VALUES = ['old draft', 'hf: legacy-model', 'character', 'outfit', 'pose', 42, 'fixed', 0.55, 384, 1024, true];

test('H3 prompter has no draft text box and loads workflows saved with one', async ({ page }) => {
    const values = await page.evaluate(async legacy => {
        const { app } = await import('/scripts/app.js');
        const fresh = LiteGraph.createNode('KikoH3ReferencePrompter');
        const freshWidgets = fresh.widgets.map(widget => widget.name);
        app.graph.add(fresh);
        const freshSaved = fresh.serialize().widgets_values;
        const workflow = {
            last_node_id: 1, last_link_id: 0, links: [], groups: [], config: {}, extra: {}, version: 0.4,
            nodes: [{
                id: 1, type: 'KikoH3ReferencePrompter', pos: [0, 0], size: [460, 600], flags: {}, order: 0, mode: 0,
                inputs: [{ name: 'prompt', type: 'STRING', widget: { name: 'prompt' }, link: null }],
                outputs: [], properties: {}, widgets_values: legacy,
            }],
        };
        await app.loadGraphData(workflow, true, false);
        const node = app.graph._nodes.find(item => item.type === 'KikoH3ReferencePrompter');
        const value = name => node.widgets.find(widget => widget.name === name)?.value;
        return {
            freshWidgets,
            freshSaved,
            socket: node.inputs.some(input => input.name === 'prompt'),
            loaded: ['model', 'role_1', 'role_2', 'role_3', 'seed', 'temperature', 'describe_tokens', 'write_tokens', 'keep_loaded'].map(value),
            saved: node.serialize().widgets_values,
        };
    }, LEGACY_VALUES);
    expect(values.freshWidgets).not.toContain('prompt');
    expect(values.freshSaved).toEqual(['hf: legacy-model', 'auto', 'auto', 'auto', 0, 'randomize', 0.7, 512, 1536, false].map((value, index) => (index === 0 ? values.freshSaved[0] : value)));
    expect(values.socket).toBe(true);
    expect(values.loaded).toEqual(['hf: legacy-model', 'character', 'outfit', 'pose', 42, 0.55, 384, 1024, true]);
    expect(values.saved).toEqual(LEGACY_VALUES.slice(1));
});
