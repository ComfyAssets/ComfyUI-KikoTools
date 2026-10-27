import { test, expect } from '../../tools/testing/node_modules/@playwright/test/index.mjs';
import { installHost } from './host-setup.mjs';

installHost(test, expect);

test('resolution picker survives renderers, swap, themes and workflow reload', async ({ page }, testInfo) => {
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode('ModelResolutionPicker');
        app.graph.add(node);
        app.canvas.centerOnNode(node);
    });
    const panel = page.locator('.ca-resolution-picker');
    await expect(panel.getByRole('button', { name: '1:1', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await panel.getByRole('button', { name: '16:9', exact: true }).click();
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await expect(panel).toHaveCount(1);
        await page.locator('.ca-dimension-swap').getByRole('button', { name: 'Swap width and height', exact: true }).click();
    }
    // three swaps from 16:9
    await expect(panel.getByRole('button', { name: '9:16', exact: true })).toHaveAttribute('aria-pressed', 'true');
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
        await page.screenshot({ path: testInfo.outputPath(`ModelResolutionPicker-${theme}.png`) });
    }
    const restored = await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const workflow = app.graph.serialize();
        const saved = workflow.nodes.find(node => node.type === 'ModelResolutionPicker');
        if (saved.widgets_values.slice(4).some(value => value !== '' && value != null)) throw new Error('Picker UI leaked into workflow values');
        await app.loadGraphData(workflow);
        const node = app.graph._nodes.find(node => node.type === 'ModelResolutionPicker');
        return {
            saved: saved.widgets_values.slice(0, 4),
            restored: node.widgets.filter(widget => ['model', 'width', 'height', 'batch_size'].includes(widget.name)).map(widget => widget.value),
            size: Array.from(node.size),
            savedSize: Array.from(saved.size),
        };
    });
    expect(restored.restored).toEqual(restored.saved);
    expect(restored.size).toEqual(restored.savedSize);
    await expect(panel.getByRole('button', { name: '9:16', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(node => node.type === 'ModelResolutionPicker');
        window.removedPicker = node;
        app.graph.remove(node);
    });
    await expect(panel).toHaveCount(0);
    expect(await page.evaluate(() => removedPicker.resolutionScope.signal.aborted)).toBe(true);
});
