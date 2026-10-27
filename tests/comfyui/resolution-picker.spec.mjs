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
    // model change in Nodes 2.0 lands on the new family's default for the derived chip
    const payload = await page.evaluate(async () => (await fetch('/kikotools/model_resolution/families')).json());
    const hunyuan = payload.families.find(family => family.label === 'HunyuanImage 2.1');
    const target = hunyuan.default[0] * hunyuan.default[1];
    const [expectedWidth, expectedHeight] = [...hunyuan.sizes['9:16']].sort(
        (a, b) => Math.abs(a[0] * a[1] - target) - Math.abs(b[0] * b[1] - target),
    )[0];
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', true);
    });
    await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(true);
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(item => item.type === 'ModelResolutionPicker');
        const widget = node.widgets.find(item => item.name === 'model');
        widget.value = 'HunyuanImage 2.1';
        widget.callback(widget.value, app.canvas, node, [0, 0], null);
    });
    await expect.poll(() => page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(item => item.type === 'ModelResolutionPicker');
        return ['width', 'height'].map(name => node.widgets.find(widget => widget.name === name).value);
    })).toEqual([expectedWidth, expectedHeight]);
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', false);
    });
    await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(false);
    await expect(panel.getByRole('button', { name: '9:16', exact: true })).toHaveAttribute('aria-pressed', 'true');
    // wired-in state disables the chips and Swap, and clears when the link goes away
    const swap = page.locator('.ca-dimension-swap').getByRole('button', { name: 'Swap width and height', exact: true });
    await expect(swap).toBeEnabled();
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(item => item.type === 'ModelResolutionPicker');
        window.wiredEntry = { name: 'width', widget: { name: 'width' }, link: 7 };
        node.inputs.push(window.wiredEntry);
        node.onConnectionsChange();
    });
    await expect(panel.locator('.ca-resolution-header')).toHaveText('Dimensions are wired in');
    await expect(swap).toBeDisabled();
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(item => item.type === 'ModelResolutionPicker');
        node.inputs.splice(node.inputs.indexOf(window.wiredEntry), 1);
        node.onConnectionsChange();
    });
    await expect(swap).toBeEnabled();
    await expect(panel.locator('.ca-resolution-header')).not.toHaveText('Dimensions are wired in');
    // the node height is fitted to the panel content: no empty space under the list, and it follows the list
    const heights = () => page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(item => item.type === 'ModelResolutionPicker');
        return { size: node.size[1], computed: node.computeSize()[1] };
    });
    await expect.poll(async () => { const h = await heights(); return Math.abs(h.size - h.computed) < 1 && h.size < 600; }).toBe(true);
    const fitted = (await heights()).size;
    await panel.getByRole('button', { name: 'Custom ratio', exact: true }).click();
    await expect.poll(async () => (await heights()).size).toBeGreaterThan(fitted);
    await panel.getByRole('button', { name: '9:16', exact: true }).click();
    await expect.poll(async () => (await heights()).size).toBe(fitted);
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
        if (saved.widgets_values.slice(5).some(value => value !== '' && value != null)) throw new Error('Picker UI leaked into workflow values');
        await app.loadGraphData(workflow);
        const node = app.graph._nodes.find(node => node.type === 'ModelResolutionPicker');
        return {
            saved: saved.widgets_values.slice(0, 5),
            restored: node.widgets.filter(widget => ['model', 'resolution', 'width', 'height', 'batch_size'].includes(widget.name)).map(widget => widget.value),
            size: Array.from(node.size),
            savedSize: Array.from(saved.size),
        };
    });
    expect(restored.restored).toEqual(restored.saved);
    expect(restored.restored[1]).toMatch(/^\d+×\d+ - 9:16 \(\d\.\dMP\)$/);
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
