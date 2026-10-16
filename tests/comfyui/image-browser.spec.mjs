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
        if (path.startsWith('/kiko_local_image_loader/') || path === '/view') {
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
