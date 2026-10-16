import { test, expect } from '../../tools/testing/node_modules/@playwright/test/index.mjs';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, sep } from 'node:path';

const fixture = 'http://127.0.0.1:8771';
const web = resolve(fileURLToPath(new URL('../../web/', import.meta.url)));

test.beforeEach(async ({ page, context, request, baseURL }, testInfo) => {
    const info = await (await request.get(`${baseURL}system_stats`)).json();
    expect(info.system.comfyui_version).toBe('0.39.0');
    expect(info.system.required_frontend_version).toBe('1.55.14');
    expect(info.system.comfy_package_versions.find(item => item.name === 'comfyui-frontend-package')?.installed).toBe('1.55.14');
    await testInfo.attach('host-versions.json', { body: JSON.stringify(info.system, null, 2), contentType: 'application/json' });
    await expect(await request.post(`${fixture}/__test__/reset`)).toBeOK();
    await context.route('**/*', async route => {
        const request = route.request();
        const url = new URL(request.url());
        const path = url.pathname.replace(/^\/api\//, '/');
        if (path.startsWith('/kiko_local_image_loader/') || path.startsWith('/kikotools/autocomplete/') || path === '/view') {
            const response = await route.fetch({ url: `${fixture}${path}${url.search}` });
            return route.fulfill({ response });
        }
        if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) return route.fulfill({ json: {} });
        if (path === '/extensions') {
            const response = await route.fetch();
            const extensions = (await response.json()).filter(path => path.startsWith('/extensions/kikotools/'));
            return route.fulfill({ json: extensions });
        }
        if (path.startsWith('/extensions/kikotools/')) {
            const source = resolve(web, decodeURIComponent(path.slice('/extensions/kikotools/'.length)));
            if (!source.startsWith(web + sep)) return route.abort();
            if (!/\.(js|css)$/.test(source)) return route.abort();
            return route.fulfill({ body: await readFile(source), contentType: source.endsWith('.css') ? 'text/css' : 'text/javascript' });
        }
        return route.continue();
    });
    await page.addInitScript(() => localStorage.setItem('kikotools.embedding_autocomplete.settings', JSON.stringify({ showCustomWords: false, customWordsUrl: '' })));
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.getByRole('status', { name: 'Loading ComfyUI' })).toBeHidden({ timeout: 30000 });
    await page.waitForFunction(async () => {
        const { app } = await import('/scripts/app.js');
        return !!app.graph && !!globalThis.LiteGraph?.registered_node_types?.KikoLocalImageLoader;
    });
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        app.graph.clear();
    });
});

for (const name of ['WidthHeightSelector', 'EmptyLatentBatch']) {
test(`${name}: shared swap survives renderers, zoom, themes and workflow reload`, async ({ page }, testInfo) => {
    await page.evaluate(async name => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode(name);
        app.graph.add(node);
        const preset = node.widgets.find(widget => widget.name === 'preset');
        const options = typeof preset.options.values === 'function' ? preset.options.values() : preset.options.values;
        preset.value = options.find(option => option.startsWith('832×1216'));
        preset.callback(preset.value, app.canvas, node, [0, 0], null);
        const batch = node.widgets.find(widget => widget.name === 'batch_size');
        if (batch) batch.value = 3;
        app.canvas.centerOnNode(node);
    }, name);
    const panel = page.locator('.ca-dimension-swap');
    const button = panel.getByRole('button', { name: 'Swap width and height', exact: true });
    await expect(button).toBeVisible();
    for (const renderer of [false, true, false]) {
        const before = await page.evaluate(async ({ name, renderer }) => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
            const node = app.graph._nodes.find(node => node.type === name);
            app.canvas.ds.scale = .7;
            app.canvas.centerOnNode(node);
            return node.widgets.filter(widget => ['width', 'height'].includes(widget.name)).map(widget => widget.value);
        }, { name, renderer });
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await expect(panel).toHaveCount(1);
        await button.focus();
        await page.keyboard.press('Enter');
        expect(await page.evaluate(async name => {
            const { app } = await import('/scripts/app.js');
            return app.graph._nodes.find(node => node.type === name).widgets.filter(widget => ['width', 'height'].includes(widget.name)).map(widget => widget.value);
        }, name)).toEqual([...before].reverse());
    }
    await page.evaluate(async name => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(node => node.type === name);
        node.setSize([220, 280]);
        app.canvas.ds.scale = 1;
        app.canvas.centerOnNode(node);
    }, name);
    expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
    const narrow = await button.boundingBox();
    await page.evaluate(async name => {
        const { app } = await import('/scripts/app.js');
        app.graph._nodes.find(node => node.type === name).setSize([500, 300]);
    }, name);
    await expect.poll(async () => (await button.boundingBox()).width).toBeGreaterThan(narrow.width);
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
        await page.screenshot({ path: testInfo.outputPath(`${name}-${theme}.png`) });
    }
    const restored = await page.evaluate(async name => {
        const { app } = await import('/scripts/app.js');
        const workflow = app.graph.serialize();
        const saved = workflow.nodes.find(node => node.type === name);
        const nativeCount = name === 'EmptyLatentBatch' ? 4 : 3;
        if (saved.widgets_values.slice(nativeCount).some(value => value !== '' && value != null)) throw new Error('Swap UI leaked into workflow values');
        await app.loadGraphData(workflow);
        const node = app.graph._nodes.find(node => node.type === name);
        app.canvas.centerOnNode(node);
        return { saved: saved.widgets_values.slice(0, nativeCount), restored: node.widgets.filter(widget => ['preset', 'width', 'height', 'batch_size'].includes(widget.name)).map(widget => widget.value), size: Array.from(node.size), savedSize: Array.from(saved.size) };
    }, name);
    expect(restored.restored).toEqual(restored.saved);
    expect(restored.size).toEqual(restored.savedSize);
    await expect(panel).toHaveCount(1);
    await page.evaluate(async name => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(node => node.type === name);
        window.removedSwap = node;
        app.graph.remove(node);
    }, name);
    await expect(panel).toHaveCount(0);
    expect(await page.evaluate(() => removedSwap.swapScope.signal.aborted)).toBe(true);
});
}

test('workflow timer preserves appearance and elapsed time through renderer switching and settings', async ({ page }, testInfo) => {
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const { api } = await import('/scripts/api.js');
        await app.ui.settings.setSettingValue('kikotools.workflow_timer.color', '#123456');
        const node = LiteGraph.createNode('KikoWorkflowTimer');
        app.graph.add(node);
        node.color = '#334455';
        node.bgcolor = '#556677';
        node.setSize([440, 240]);
        node.properties.elapsed_time_str = '01:02:345';
        node.onConfigure({ properties: node.properties });
        app.canvas.centerOnNode(node);
        api.dispatchEvent(new CustomEvent('execution_start'));
    });
    const panel = page.locator('.ca-workflow-timer');
    const timer = panel.getByRole('timer', { name: 'Elapsed workflow time' });
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await expect(panel).toHaveCount(1);
        await expect(timer).toHaveClass(/running/);
        await expect(timer).toHaveCSS('color', 'rgb(18, 52, 86)');
    }
    await page.evaluate(async () => {
        const { api } = await import('/scripts/api.js');
        api.dispatchEvent(new CustomEvent('execution_interrupted'));
    });
    const stopped = await timer.textContent();
    const initialFontSize = await timer.evaluate(element => parseFloat(getComputedStyle(element).fontSize));
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        app.graph._nodes.find(node => node.type === 'KikoWorkflowTimer').setSize([220, 160]);
    });
    await expect.poll(() => timer.evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeLessThan(initialFontSize);
    expect(await timer.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        app.graph._nodes.find(node => node.type === 'KikoWorkflowTimer').setSize([600, 320]);
    });
    await expect.poll(() => timer.evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThan(initialFontSize);
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        app.graph._nodes.find(node => node.type === 'KikoWorkflowTimer').setSize([440, 240]);
    });
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        await app.ui.settings.setSettingValue('kikotools.workflow_timer.color', '#0877bb');
    });
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
        await page.screenshot({ path: testInfo.outputPath(`timer-${theme}.png`) });
    }
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const workflow = app.graph.serialize();
        await app.loadGraphData(workflow);
        const node = app.graph._nodes.find(node => node.type === 'KikoWorkflowTimer');
        if (node.color !== '#334455' || node.bgcolor !== '#556677') throw new Error('Custom node colors changed');
        if (node.size[0] !== 440 || node.size[1] !== 240) throw new Error('Saved timer dimensions changed');
        app.canvas.centerOnNode(node);
    });
    await expect(timer).toHaveText(stopped);
    await page.getByRole('button', { name: 'Settings (Ctrl + ,)', exact: true }).click();
    const search = page.getByPlaceholder(/search/i);
    await expect(search).toBeVisible();
    await search.fill('Workflow Timer');
    await page.getByRole('button', { name: 'Choose timer color', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: 'Timer color', exact: true });
    await expect(dialog).toBeVisible();
    await dialog.getByLabel('Hex color', { exact: true }).fill('#4a90d9');
    await page.keyboard.press('Tab');
    await expect(timer).toHaveCSS('color', 'rgb(74, 144, 217)');
    await page.screenshot({ path: testInfo.outputPath('timer-color-picker.png') });
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
    await expect(page.getByRole('button', { name: 'Choose timer color', exact: true })).toBeFocused();
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(node => node.type === 'KikoWorkflowTimer');
        window.removedTimer = node;
        app.graph.remove(node);
    });
    await expect(panel).toHaveCount(0);
    expect(await page.evaluate(() => removedTimer.timerScope.signal.aborted)).toBe(true);
});

test('seed history survives renderer switching, resizing and workflow reload', async ({ page }, testInfo) => {
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode('SeedHistory');
        app.graph.add(node);
        node.setSize([380, 560]);
        for (let seed = 100; seed < 110; seed++) node.addSeedToHistory(seed);
        app.canvas.centerOnNode(node);
    });
    const panel = page.locator('.ca-seed-history');
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await expect(panel).toHaveCount(1);
        await panel.getByRole('button', { name: 'Use seed 105', exact: true }).focus();
        await page.keyboard.press('Enter');
        await expect(panel.getByRole('button', { name: 'Use seed 105', exact: true })).toHaveAttribute('aria-pressed', 'true');
        await expect(panel.getByRole('status')).toHaveText('Loaded: 105');
        expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true);
    }
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        app.graph._nodes.find(node => node.type === 'SeedHistory').setSize([280, 350]);
    });
    const list = panel.getByRole('list', { name: 'Recent seeds' });
    await expect.poll(() => list.evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
    const smallHeight = await list.evaluate(element => element.clientHeight);
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        app.graph._nodes.find(node => node.type === 'SeedHistory').setSize([420, 650]);
    });
    await expect.poll(() => list.evaluate(element => element.clientHeight)).toBeGreaterThan(smallHeight);
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
        await page.screenshot({ path: testInfo.outputPath(`seed-${theme}.png`) });
    }
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const workflow = app.graph.serialize();
        const saved = workflow.nodes.find(node => node.type === 'SeedHistory');
        if (saved.widgets_values[0] !== 105 || saved.widgets_values.slice(2).some(value => value !== '' && value != null)) throw new Error('History UI leaked into serialized widget values');
        await app.loadGraphData(workflow);
        const node = app.graph._nodes.find(node => node.type === 'SeedHistory');
        if (node.size[0] !== saved.size[0] || node.size[1] !== saved.size[1]) throw new Error('Saved node size changed');
        app.canvas.centerOnNode(node);
    });
    await expect(panel).toHaveCount(1);
    await expect(panel.getByRole('button', { name: 'Use seed 105', exact: true })).toBeVisible();
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes.find(node => node.type === 'SeedHistory');
        window.removedSeedNode = node;
        app.graph.remove(node);
    });
    await expect(panel).toHaveCount(0);
    expect(await page.evaluate(() => removedSeedNode.seedScope.signal.aborted && removedSeedNode.seedValueWatcher === null)).toBe(true);
});

test('saved-image window survives real renderer switching and is removed with its owner', async ({ page, request }, testInfo) => {
    const result = await request.post(`${fixture}/__test__/execute/KikoSaveImage`, { data: { filename_prefix: 'Real host viewer' } });
    await expect(result).toBeOK();
    const message = (await result.json()).ui;
    const id = await page.evaluate(async message => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode('KikoSaveImage');
        app.graph.add(node);
        node.onExecuted(message);
        app.canvas.centerOnNode(node);
        return node.id;
    }, message);
    const viewer = page.getByRole('dialog', { name: 'Saved images', exact: true });
    await expect(viewer).toBeVisible();
    await expect.poll(() => viewer.locator('img').evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await expect(viewer).toHaveCount(1);
        await viewer.getByTitle('Close', { exact: true }).click();
        await page.getByRole('button', { name: 'Show images', exact: true }).click();
        await expect(viewer).toBeVisible();
        expect(await page.evaluate(async id => {
            const { app } = await import('/scripts/app.js');
            return app.graph.serialize().nodes.find(node => String(node.id) === String(id)).widgets_values.includes('Show images');
        }, id)).toBe(false);
    }
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await expect(viewer).toHaveAttribute('data-ca-theme', theme);
        const info = await viewer.locator('.kiko-image-info').boundingBox();
        const content = await viewer.locator('.kiko-viewer-container').boundingBox();
        expect(info.y + info.height).toBeLessThanOrEqual(content.y + content.height);
        await page.screenshot({ path: testInfo.outputPath(`viewer-${theme}.png`) });
    }
    await page.evaluate(async id => {
        const { app } = await import('/scripts/app.js');
        app.graph.remove(app.graph.getNodeById(id));
    }, id);
    await expect(viewer).toHaveCount(0);
});

test('actual host preserves the widget through renderer changes, theme changes and save/reload', async ({ page, request }, testInfo) => {
    await expect(await request.post(`${fixture}/__test__/reset`, { data: { extra_images: 52 } })).toBeOK();
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', false);
        const node = LiteGraph.createNode('KikoLocalImageLoader');
        node.pos = [250, 140];
        app.graph.add(node);
        app.canvas.centerOnNode(node);
    });
    const loader = page.locator('.ca-image-browser');
    await expect(loader).toBeVisible();
    await expect(loader.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await expect(loader).toHaveCount(1);
        await expect(loader).toBeVisible();
        await loader.getByRole('button', { name: 'Select image cat & dog.png', exact: true }).click();
        await expect(loader.locator('[data-selection]')).toHaveText('cat & dog.png');
        const node = await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            return app.graph.serialize().nodes.find(node => node.type === 'KikoLocalImageLoader');
        });
        expect(node).toBeTruthy();
        expect(node.widgets_values || []).not.toContainEqual(expect.objectContaining({ className: 'ca-image-browser' }));
        await loader.getByRole('button', { name: 'Open folder bulk', exact: true }).click();
        await expect(loader.locator('.kiko-card-info-panel')).toHaveCount(50);
        const media = await loader.locator('.kiko-card-media-wrapper').nth(1).boundingBox();
        expect(media.height / media.width).toBeCloseTo(1, 1);
        expect(media.height).toBeGreaterThan(150);
        expect(await loader.locator('.kiko-cardholder').evaluate(element => element.clientHeight)).toBeGreaterThanOrEqual(await loader.locator('.kiko-card-media-wrapper').nth(1).evaluate(element => element.offsetHeight));
        expect(await loader.locator('.kiko-cardholder').evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
        await page.screenshot({ path: testInfo.outputPath(renderer ? 'nodes2.png' : 'classic.png') });
        await loader.getByRole('button', { name: 'Open folder ..', exact: true }).click();
        await expect(loader.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
    }
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await expect(loader).toHaveAttribute('data-ca-theme', theme);
    }
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const workflow = app.graph.serialize();
        await app.loadGraphData(workflow);
        app.canvas.centerOnNode(app.graph._nodes[0]);
    });
    await expect(loader).toHaveCount(1);
    await expect(loader.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        app.graph.remove(app.graph._nodes[0]);
    });
    await expect(loader).toHaveCount(0);
});

test('Node Dimensions applies and persists across Classic and Nodes 2.0', async ({ page }, testInfo) => {
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode('WidthHeightSelector');
        app.graph.add(node);
        node.pos = [300, 250];
        app.canvas.centerOnNode(node);
    });
    const dialog = page.getByRole('dialog', { name: 'Node Dimensions', exact: true });
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
            app.canvas.centerOnNode(app.graph._nodes[0]);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        const point = await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            const node = app.graph._nodes[0];
            const canvas = app.canvas.canvas.getBoundingClientRect();
            return { x: canvas.left + (node.pos[0] + app.canvas.ds.offset[0] + 60) * app.canvas.ds.scale, y: canvas.top + (node.pos[1] + app.canvas.ds.offset[1] - 15) * app.canvas.ds.scale };
        });
        await page.mouse.click(point.x, point.y, { button: 'right' });
        await page.getByText('🎨 Node Dimensions', { exact: true }).click();
        await expect(dialog).toBeVisible();
        await dialog.getByLabel('Width (px)', { exact: true }).fill('900');
        await dialog.getByLabel('Height (px)', { exact: true }).fill('600');
        await page.keyboard.press('Enter');
        await expect(dialog).toHaveCount(0);
        expect(await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            return Array.from(app.graph._nodes[0].size);
        })).toEqual([900, 600]);
        await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            window.KikoToolsExtensions.showNodeDimensionsDialog(app.graph._nodes[0]);
        });
        await dialog.getByLabel('Width (px)', { exact: true }).fill('1200');
        await page.keyboard.press('Escape');
        expect(await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            return Array.from(app.graph._nodes[0].size);
        })).toEqual([900, 600]);
    }
    const size = await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const workflow = app.graph.serialize();
        await app.loadGraphData(workflow);
        app.canvas.centerOnNode(app.graph._nodes[0]);
        window.KikoToolsExtensions.showNodeDimensionsDialog(app.graph._nodes[0]);
        return Array.from(app.graph._nodes[0].size);
    });
    expect(size).toEqual([900, 600]);
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await expect(dialog).toHaveAttribute('data-ca-theme', theme);
        await page.screenshot({ path: testInfo.outputPath(`node-dimensions-${theme}.png`) });
    }
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        app.graph.remove(app.graph._nodes[0]);
    });
    await expect(dialog).toHaveCount(0);
});

for (const name of ['DisplayText', 'DisplayAny']) {
    test(`${name}: shared output persists through renderers, themes and legacy reload`, async ({ page }, testInfo) => {
        const output = name === 'DisplayText'
            ? 'Positive prompt: A blue cabin beside a quiet lake, soft morning light, detailed reflections.\nNegative prompt: blur, noise, watermark'
            : Array.from({ length: 45 }, (_, index) => `Line ${index}: tensor / diagnostic output`).join('\n');
        await page.evaluate(async ({ name, output }) => {
            const { app } = await import('/scripts/app.js');
            const node = LiteGraph.createNode(name);
            app.graph.add(node);
            node.setSize([560, 520]);
            const mode = node.widgets.find(widget => widget.name === 'mode');
            if (mode) mode.value = 'tensor shape';
            node.onExecuted({ text: [output] });
            app.canvas.centerOnNode(node);
            window.displayCopies = [];
            Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async text => window.displayCopies.push(text) } });
        }, { name, output });
        const panel = page.locator('.ca-text-output');
        await expect(panel).toHaveCount(1);
        for (const renderer of [false, true, false]) {
            await page.evaluate(async renderer => {
                const { app } = await import('/scripts/app.js');
                await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
                app.canvas.ds.scale = .85;
                app.canvas.centerOnNode(app.graph._nodes[0]);
            }, renderer);
            await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
            await expect(panel).toBeVisible();
            await expect(panel).toHaveCount(1);
            await panel.getByRole('button', { name: name === 'DisplayText' ? 'Copy negative' : 'Copy value', exact: true }).focus();
            await page.keyboard.press('Enter');
            await expect(panel.getByRole('status')).toHaveText('Copied.');
        }
        expect(await page.evaluate(() => window.displayCopies)).toEqual(Array(3).fill(name === 'DisplayText' ? 'blur, noise, watermark' : output));
        const restored = await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            const workflow = app.graph.serialize();
            const saved = workflow.nodes[0];
            await app.loadGraphData(workflow);
            app.canvas.centerOnNode(app.graph._nodes[0]);
            return { snapshot: saved.kikoDisplay, size: Array.from(app.graph._nodes[0].size), mode: app.graph._nodes[0].widgets.find(widget => widget.name === 'mode')?.value };
        });
        expect(restored.snapshot).toEqual({ version: 1, text: output });
        expect(restored.size).toEqual([560, 520]);
        if (name === 'DisplayAny') {
            expect(restored.mode).toBe('tensor shape');
            await expect(panel.getByLabel('Value output', { exact: true })).toHaveValue(output);
        } else {
            await expect(panel.getByLabel('Positive prompt', { exact: true })).toHaveValue('A blue cabin beside a quiet lake, soft morning light, detailed reflections.');
            await expect(panel.getByLabel('Negative prompt', { exact: true })).toHaveValue('blur, noise, watermark');
        }
        for (const theme of ['light', 'dark']) {
            await page.evaluate(async theme => {
                const { app } = await import('/scripts/app.js');
                await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
            }, theme);
            await expect(panel).toHaveAttribute('data-ca-theme', theme);
            await page.screenshot({ path: testInfo.outputPath(`${name}-${theme}.png`) });
        }
        await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            app.graph._nodes[0].setSize([280, 520]);
            app.canvas.centerOnNode(app.graph._nodes[0]);
        });
        expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
        await page.evaluate(async name => {
            const { app } = await import('/scripts/app.js');
            const workflow = app.graph.serialize();
            delete workflow.nodes[0].kikoDisplay;
            workflow.nodes[0].widgets_values = name === 'DisplayText'
                ? ['✓ Positive Prompt', 'legacy positive', null, '✗ Negative Prompt', 'legacy negative', null]
                : ['tensor shape', 'legacy first', 'legacy second', null];
            await app.loadGraphData(workflow);
            app.canvas.centerOnNode(app.graph._nodes[0]);
        }, name);
        await expect(panel).toHaveCount(1);
        if (name === 'DisplayText') {
            await expect(panel.getByLabel('Positive prompt', { exact: true })).toHaveValue('legacy positive');
            await expect(panel.getByLabel('Negative prompt', { exact: true })).toHaveValue('legacy negative');
        } else {
            await expect(panel.getByLabel('Value output', { exact: true })).toHaveValue('legacy first\nlegacy second');
            expect(await page.evaluate(async () => {
                const { app } = await import('/scripts/app.js');
                return app.graph._nodes[0].widgets.find(widget => widget.name === 'mode').value;
            })).toBe('tensor shape');
        }
        await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            const node = app.graph._nodes[0];
            window.removedDisplay = node;
            app.graph.remove(node);
        });
        await expect(panel).toHaveCount(0);
        expect(await page.evaluate(() => window.removedDisplay.displayOutput.scope.signal.aborted)).toBe(true);
    });
}


test('embedding suggestions survive real renderers, zoom, themes and workflow reload', async ({ page }, testInfo) => {
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode('TextInput');
        app.graph.add(node);
        node.setSize([550, 350]);
        app.canvas.centerOnNode(node);
    });
    await expect.poll(() => page.evaluate(() => window.kikotools.autocomplete.embeddings.length)).toBe(2);
    const prompt = page.locator('textarea:visible');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    for (const [renderer, zoom] of [[false, .65], [true, 1.1], [false, .9]]) {
        await page.evaluate(async ({ renderer, zoom }) => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
            app.canvas.ds.scale = zoom;
            app.canvas.centerOnNode(app.graph._nodes[0]);
        }, { renderer, zoom });
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await prompt.fill('embedding:ca');
        await expect(list).toBeVisible();
        await prompt.press('ArrowDown');
        await expect(list.getByRole('option', { selected: true })).toHaveCount(1);
        await expect(prompt).toBeFocused();
        const box = await list.boundingBox();
        expect(box.x).toBeGreaterThanOrEqual(0);
        expect(box.y).toBeGreaterThanOrEqual(0);
        expect(box.x + box.width).toBeLessThanOrEqual(1600);
        expect(box.y + box.height).toBeLessThanOrEqual(1100);
        await prompt.press('Enter');
        await expect(prompt).toHaveValue('embedding:portraits/cat, ');
        await prompt.fill('<lora:in');
        await list.getByRole('option').click();
        await expect(prompt).toHaveValue('<lora:styles/ink:1.0>, ');
    }
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        await app.loadGraphData(app.graph.serialize());
        app.canvas.centerOnNode(app.graph._nodes[0]);
    });
    await expect(prompt).toHaveValue('<lora:styles/ink:1.0>, ');
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await prompt.fill('em');
        await prompt.press('ArrowDown');
        await expect(list).toHaveAttribute('data-ca-theme', theme);
        await page.screenshot({ path: testInfo.outputPath(`suggestions-${theme}.png`) });
        await prompt.press('Escape');
    }
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes[0];
        window.removedCompletionWidget = node.widgets.find(widget => widget.inputEl);
        app.graph.remove(node);
    });
    await expect(list).toBeHidden();
    expect(await page.evaluate(() => window.kikotools.autocomplete.activeWidgets.has(window.removedCompletionWidget))).toBe(false);
});

test('embedding settings use the real host launcher and preserve preferences', async ({ page }, testInfo) => {
    await page.getByRole('button', { name: 'Settings (Ctrl + ,)', exact: true }).click();
    const search = page.getByPlaceholder(/search/i);
    await search.fill('Embedding Autocomplete');
    const trigger = page.getByRole('button', { name: 'Open Settings', exact: true });
    await trigger.click();
    const dialog = page.getByRole('dialog', { name: 'Embedding Autocomplete Settings', exact: true });
    await expect(dialog).toBeVisible();
    for (const theme of ['light', 'dark']) {
        await page.evaluate(async theme => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.ColorPalette', theme);
        }, theme);
        await expect(dialog).toHaveAttribute('data-ca-theme', theme);
        await page.screenshot({ path: testInfo.outputPath(`settings-${theme}.png`) });
    }
    await dialog.getByRole('switch', { name: 'Show LoRAs', exact: true }).uncheck();
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await expect(trigger).toBeFocused();
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('kikotools.embedding_autocomplete.settings')).showLoras)).toBe(false);
    await trigger.click();
    await expect(dialog.getByRole('switch', { name: 'Show LoRAs', exact: true })).not.toBeChecked();
    await dialog.getByRole('switch', { name: 'Show LoRAs', exact: true }).check();
    await page.keyboard.press('Escape');
    expect(await page.evaluate(() => window.kikotools.autocomplete.settings.showLoras)).toBe(false);
});

test('embedding tag files import through real settings and complete canonical tags in both renderers', async ({ page }, testInfo) => {
    await page.getByRole('button', { name: 'Settings (Ctrl + ,)', exact: true }).click();
    await page.getByPlaceholder(/search/i).fill('Embedding Autocomplete');
    await page.getByRole('button', { name: 'Open Settings', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: 'Embedding Autocomplete Settings', exact: true });
    const input = process.env.KIKO_TAG_CSV || { name: 'tags.csv', mimeType: 'text/csv', buffer: Buffer.from('highres,5,100,"high_res,high_resolution"\nblue_eyes,0,90,azure') };
    await dialog.getByLabel('Tag list file', { exact: true }).setInputFiles(input);
    await expect(dialog.getByRole('status')).toContainText('tags ready', { timeout: 15000 });
    await testInfo.attach('import-status.txt', { body: await dialog.getByRole('status').innerText(), contentType: 'text/plain' });
    await dialog.getByRole('switch', { name: 'Show Custom Words', exact: true }).check();
    await dialog.getByText('Triggers, matching and insertion', { exact: true }).click();
    await dialog.getByRole('switch', { name: 'Replace underscores with spaces', exact: true }).uncheck();
    await page.screenshot({ path: testInfo.outputPath('tag-import.png') });
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await page.keyboard.press('Escape');
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode('TextInput');
        app.graph.add(node);
        node.setSize([550, 350]);
        app.canvas.centerOnNode(node);
    });
    const prompt = page.locator('textarea:visible');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
            app.canvas.centerOnNode(app.graph._nodes[0]);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await prompt.fill('high_resolution');
        await expect(list.getByRole('option').first()).toContainText('highres');
        await prompt.press('ArrowDown');
        await prompt.press('Tab');
        await expect(prompt).toHaveValue('highres, ');
    }
});

test('embedding Unicode and emoticon completion preserves prompt boundaries in both renderers', async ({ page }) => {
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const { parseTagList } = await import('/extensions/kikotools/autocomplete/tags.js');
        const autocomplete = window.kikotools.autocomplete;
        autocomplete.customWords = parseTagList('日本語,0,10,にほんご\nheart,0,20,<3');
        Object.assign(autocomplete.settings, { showCustomWords: true, showEmbeddings: false, showLoras: false });
        const node = LiteGraph.createNode('TextInput');
        app.graph.add(node);
        node.setSize([550, 350]);
        app.canvas.centerOnNode(node);
    });
    const prompt = page.locator('textarea:visible');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
            app.canvas.centerOnNode(app.graph._nodes[0]);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await prompt.focus();
        await expect(prompt).toHaveAttribute('aria-autocomplete', 'list');
        for (const [query, result] of [['sky, 日本', 'sky, 日本語, '], ['sky, <3', 'sky, heart, ']]) {
            await prompt.fill(query);
            await expect(list.getByRole('option')).toHaveCount(1);
            await prompt.press('ArrowDown');
            await prompt.press('Tab');
            await expect(prompt).toHaveValue(result);
        }
    }
});

test('Custom Colors preserves node colors across renderers and workflow reload', async ({ page }, testInfo) => {
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode('EmptyLatentImage');
        app.graph.add(node);
        node.bgcolor = '#123456';
        app.canvas.centerOnNode(node);
    });
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            const node = app.graph._nodes[0];
            const menu = app.collectNodeMenuItems(node).find(item => item?.content === '🫶 Custom Colors');
            menu.submenu.options.find(item => item.content === '🫶 Custom Full').callback();
        });
        const dialog = page.getByRole('dialog', { name: 'Custom full color', exact: true });
        await expect(dialog).toBeVisible();
        await dialog.getByLabel('Hex color', { exact: true }).fill('#112233');
        await dialog.getByLabel('Hex color', { exact: true }).press('Tab');
        if (renderer) {
            for (const [color, theme] of [['#fff', 'light'], ['#202020', 'dark']]) {
                await page.evaluate(color => document.body.style.setProperty('--bg-color', color), color);
                await expect(dialog).toHaveAttribute('data-ca-theme', theme);
                await page.screenshot({ path: testInfo.outputPath(`custom-colors-${theme}.png`) });
            }
        }
        await page.keyboard.press('Escape');
        await expect(page.locator('ca-color-picker')).toHaveCount(0);
        expect(await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            const workflow = app.graph.serialize();
            await app.loadGraphData(workflow);
            const node = app.graph._nodes[0];
            return { color: node.color, bgcolor: node.bgcolor };
        })).toEqual({ color: '#253647', bgcolor: '#112233' });
    }
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = app.graph._nodes[0];
        app.collectNodeMenuItems(node).find(item => item?.content === '🫶 Custom Colors').submenu.options[0].callback();
        app.graph.remove(node);
    });
    await expect(page.locator('dialog.ca-color-dialog')).toHaveCount(0);
});

test('Follow Execution honors live settings and host menus in both renderers', async ({ page }, testInfo) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.evaluate(async () => {
        const { app } = await import('/scripts/app.js');
        const node = LiteGraph.createNode('EmptyLatentImage');
        app.graph.add(node);
        await app.ui.settings.setSettingValue('kikotools.follow_execution.auto_start', false);
    });
    for (const renderer of [false, true, false]) {
        await page.evaluate(async renderer => {
            const { app } = await import('/scripts/app.js');
            await app.ui.settings.setSettingValue('Comfy.VueNodes.Enabled', renderer);
        }, renderer);
        await expect.poll(() => page.evaluate(() => LiteGraph.vueNodesMode)).toBe(renderer);
        await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            app.graph._nodes[0].pos[0] += 10000;
            await app.ui.settings.setSettingValue('kikotools.follow_execution.enabled', true);
        });
        const canvas = page.locator('#graph-canvas');
        await canvas.click({ button: 'right', position: { x: 800, y: 500 } });
        await expect(page.getByText('🫶 Follow execution', { exact: true })).toBeVisible();
        await expect(page.getByText('🫶 Go to node', { exact: true })).toBeVisible();
        await page.screenshot({ path: testInfo.outputPath(renderer ? 'follow-execution-nodes2.png' : 'follow-execution-classic.png') });
        await canvas.click({ position: { x: 100, y: 800 } });
        await expect(page.getByText('🫶 Follow execution', { exact: true })).toBeHidden();
        const result = await page.evaluate(async () => {
            const { app } = await import('/scripts/app.js');
            const { api } = await import('/scripts/api.js');
            const node = app.graph._nodes[0];
            const original = app.canvas.centerOnNode;
            const centered = [];
            app.canvas.centerOnNode = function (node) { centered.push(node.id); return original.apply(this, arguments); };
            const set = (key, value) => app.ui.settings.setSettingValue(`kikotools.follow_execution.${key}`, value);
            const menu = () => app.collectCanvasMenuItems(app.canvas);
            const toggle = () => menu().find(item => /🫶 (Stop following execution|Follow execution)/.test(item?.content)).callback();
            const emit = () => api.dispatchEvent(new CustomEvent('executing', { detail: String(node.id) }));
            const progress = nodes => api.dispatchEvent(new CustomEvent('progress_state', { detail: { prompt_id: 'follow-execution-test', nodes } }));
            try {
                await set('enabled', true);
                await set('auto_start', false);
                progress({});
                await new Promise(requestAnimationFrame);
                const extension = app.extensions.find(item => item.name === 'kikotools.followExecution');
                await extension.setup();
                await extension.setup();
                toggle();
                emit();
                const manual = centered.length;
                await set('enabled', false);
                emit();
                const disabled = centered.length;
                await set('enabled', true);
                emit();
                const reenabled = centered.length;
                await set('auto_start', true);
                api.dispatchEvent(new CustomEvent('execution_start', { detail: { prompt_id: 'follow-execution-test' } }));
                emit();
                const autoStart = centered.length;
                toggle();
                emit();
                const stopped = centered.length;
                progress({ [node.id]: { state: 'running', value: 0, max: 1, node_id: String(node.id), prompt_id: 'follow-execution-test' } });
                await new Promise(requestAnimationFrame);
                const showItem = menu().find(item => item?.content === '🫶 Show executing node');
                if (!showItem) throw new Error(JSON.stringify({ running: app.runningNodeId, menus: menu().map(item => item?.content) }));
                showItem.callback();
                const show = centered.length;
                menu().find(item => item?.content === '🫶 Go to node').submenu.options
                    .find(item => item.content === 'EmptyLatentImage').submenu.options[0].callback();
                const goTo = centered.length;
                await set('show_goto_node', false);
                const hideGoTo = !menu().some(item => item?.content === '🫶 Go to node');
                await set('show_goto_node', true);
                await set('enabled', false);
                progress({});
                api.dispatchEvent(new CustomEvent('executing', { detail: null }));
                return { manual, disabled, reenabled, autoStart, stopped, show, goTo, hideGoTo };
            } finally {
                app.canvas.centerOnNode = original;
            }
        });
        expect(result).toEqual({ manual: 1, disabled: 1, reenabled: 1, autoStart: 2, stopped: 2, show: 3, goTo: 4, hideGoTo: true });
    }
    expect(errors).toEqual([]);
});
