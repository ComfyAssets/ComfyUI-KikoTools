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
