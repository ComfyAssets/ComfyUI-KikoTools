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
    await testInfo.attach('host-versions.json', { body: JSON.stringify(info.system, null, 2), contentType: 'application/json' });
    await expect(await request.post(`${fixture}/__test__/reset`)).toBeOK();
    await context.route('**/*', async route => {
        const request = route.request();
        const url = new URL(request.url());
        const path = url.pathname.replace(/^\/api\//, '/');
        if (path.startsWith('/kiko_local_image_loader/')) {
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

test('actual host preserves the widget through renderer changes, theme changes and save/reload', async ({ page }, testInfo) => {
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
        await page.screenshot({ path: testInfo.outputPath(renderer ? 'nodes2.png' : 'classic.png') });
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
