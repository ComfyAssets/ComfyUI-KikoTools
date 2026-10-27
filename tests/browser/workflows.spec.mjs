import { test, expect } from '../../tools/testing/node_modules/@playwright/test/index.mjs';
import { isFixtureURL } from '../../tools/testing/network-policy.mjs';
import { startCoverage, saveCoverage } from '../../tools/testing/browser-coverage.mjs';

test.beforeEach(async ({ page, request, context, browserName, baseURL }) => {
    await startCoverage(page, browserName);
    await expect(await request.post('/__test__/reset')).toBeOK();
    page.errors = [];
    page.on('pageerror', error => page.errors.push(error.message));
    page.on('response', response => { if (response.status() >= 500) page.errors.push(`${response.status()} ${response.url()}`); });
    await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (isFixtureURL(url.href, baseURL)) return route.continue();
        page.errors.push(`Unexpected external request: ${url.origin}`);
        return route.abort();
    });
    await page.addInitScript(() => { if (!localStorage.getItem('kikotools.embedding_autocomplete.settings')) localStorage.setItem('kikotools.embedding_autocomplete.settings', JSON.stringify({ showCustomWords: false, customWordsUrl: '' })); });
});
test.afterEach(async ({ page, browserName }) => {
    await saveCoverage(page, browserName);
    expect(page.errors).toEqual([]);
});
async function openHost(page) {
    await page.goto('/__test__/');
    await expect(page.locator('body')).toHaveAttribute('data-ready', 'true');
}
async function createNode(page, name, values = {}) {
    return page.evaluate(({ name, values }) => kikoHost.createNode(name, values), { name, values });
}
async function state(request) { return (await (await request.get('/__test__/state')).json()); }

test('plugin startup registers every frontend extension and exposes real autocomplete routes', async ({ page, request }) => {
    await openHost(page);
    const manifest = await state(request);
    expect(manifest.nodes).toEqual(expect.arrayContaining(['DisplayAny', 'DisplayText', 'WidthHeightSelector', 'KikoLocalImageLoader', 'KikoSaveImage']));
    const registered = await page.evaluate(() => kikoHost.extensions.map(extension => extension.name));
    expect(registered).toHaveLength(manifest.extensions.length);
    expect(new Set(registered).size).toBe(registered.length);
    const embeddings = await (await request.get('/kikotools/autocomplete/embeddings')).json();
    expect(embeddings).toContainEqual(expect.objectContaining({ name: 'cat', path: 'portraits/cat' }));
});

test('shared loader controls follow host themes, resize and support keyboard selection', async ({ page }) => {
    let firstListing = true;
    await page.route('**/kiko_local_image_loader/images?*', async route => {
        if (firstListing) {
            firstListing = false;
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        await route.continue();
    });
    await openHost(page);
    await createNode(page, 'KikoLocalImageLoader');
    const loader = page.locator('.ca-image-browser');
    await expect(loader).toBeVisible();
    await page.evaluate(() => document.body.style.setProperty('--bg-color', '#202020'));
    await expect(loader).toHaveAttribute('data-ca-theme', 'dark');
    await page.evaluate(() => document.body.style.setProperty('--bg-color', '#fafafa'));
    await expect(loader).toHaveAttribute('data-ca-theme', 'light');
    await expect(loader.getByRole('button', { name: 'Select image cat & dog.png', exact: true })).toBeVisible();
    const toggle = loader.getByRole('switch', { name: 'Hide dot folders' });
    await toggle.focus();
    await page.keyboard.press('Space');
    await expect(toggle).not.toBeChecked();
    await expect(page.locator('.kiko-folder-name').filter({ hasText: /^\.hidden$/ })).toBeVisible();
    await loader.getByRole('button', { name: 'Select image cat & dog.png', exact: true }).focus();
    await page.keyboard.press('Enter');
    await expect(loader.locator('[data-selection]')).toContainText('cat & dog.png');
    for (const width of [320, 480, 800]) {
        await loader.evaluate((element, width) => { element.style.width = `${width}px`; }, width);
        expect(await loader.evaluate(element => element.scrollWidth - element.clientWidth)).toBeLessThanOrEqual(1);
    }
    await loader.evaluate(element => element.style.removeProperty('width'));
    await loader.getByRole('radio', { name: 'List', exact: true }).check();
    await expect(loader.locator('.kiko-cardholder')).toHaveAttribute('data-view', 'list');
    await loader.getByRole('searchbox', { name: 'Filter this page' }).fill('not-in-folder');
    await expect(loader.getByText('No matching items on this page')).toBeVisible();
    await loader.getByRole('searchbox', { name: 'Filter this page' }).fill('cat');
    await expect(loader.locator('.kiko-gallery-card')).toHaveCount(1);
});

test('a slower directory response cannot overwrite the latest folder', async ({ page, request }) => {
    await openHost(page);
    await createNode(page, 'KikoLocalImageLoader');
    await expect(page.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
    const info = await state(request);
    const original = await (await request.get(`/kiko_local_image_loader/images?directory=${encodeURIComponent(info.input)}`)).json();
    const held = [];
    await page.route('**/kiko_local_image_loader/images?*', route => {
        if (new URL(route.request().url()).searchParams.get('directory') === info.input) held.push(route);
        else return route.continue();
    });
    await page.locator('.kiko-refresh').click();
    await expect.poll(() => held.length).toBe(1);
    await page.locator('.kiko-path-input').fill(`${info.input}/sub`);
    await page.locator('.kiko-browse').click();
    await expect(page.getByAltText('forest.png', { exact: true })).toBeVisible();
    await held[0].fulfill({ json: original });
    await page.waitForTimeout(80);
    await expect(page.locator('.kiko-path-input')).toHaveValue(`${info.input}/sub`);
    await expect(page.getByAltText('cat & dog.png', { exact: true })).toHaveCount(0);
});

test('large galleries scroll instead of squeezing thumbnails and size is adjustable', async ({ page, request }) => {
    await expect(await request.post('/__test__/reset', { data: { extra_images: 52 } })).toBeOK();
    await openHost(page);
    await createNode(page, 'KikoLocalImageLoader');
    await page.locator('.kiko-folder-name').filter({ hasText: /^bulk$/ }).click();
    await expect(page.locator('.kiko-card-info-panel')).toHaveCount(50);
    const loader = page.locator('.ca-image-browser');
    await loader.evaluate(element => { element.style.width = '800px'; element.style.height = '650px'; });
    const size = loader.getByRole('slider', { name: 'Thumbnail size' });
    await expect(size).toHaveValue('224');
    const media = loader.locator('.kiko-card-media-wrapper').nth(1);
    const before = await media.boundingBox();
    expect(before.height).toBeGreaterThanOrEqual(200);
    expect(await loader.locator('.kiko-cardholder').evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
    await size.fill('320');
    await size.dispatchEvent('input');
    expect((await media.boundingBox()).height).toBeGreaterThan(before.height);
    await expect(loader.locator('.ca-range output')).toHaveText('320 px');
    await size.focus();
    await page.keyboard.press('ArrowLeft');
    await expect(size).toHaveValue('304');
    await loader.evaluate(element => { element.style.width = '320px'; });
    expect(await loader.evaluate(element => element.scrollWidth - element.clientWidth)).toBeLessThanOrEqual(1);
    await expect(media.locator('img')).toHaveCSS('object-fit', 'contain');
});

test('removing a loader cancels delayed autocomplete and detaches theme observers', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'KikoLocalImageLoader');
    await expect(page.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
    await page.evaluate(() => document.body.style.setProperty('--bg-color', '#202020'));
    await expect(page.locator('.ca-image-browser')).toHaveAttribute('data-ca-theme', 'dark');
    await page.clock.install();
    const suggestions = [];
    page.on('request', request => { if (request.url().includes('/list_directories?')) suggestions.push(request.url()); });
    await page.locator('.kiko-path-input').fill('/pending');
    await page.evaluate(id => {
        window.removedGallery = document.querySelector('.ca-image-browser');
        kikoHost.removeNode(id);
        document.body.style.setProperty('--bg-color', '#fafafa');
    }, id);
    await page.clock.fastForward(500);
    expect(suggestions).toEqual([]);
    expect(await page.evaluate(() => window.removedGallery.dataset.caTheme)).toBe('dark');
    await expect(page.locator('.ca-image-browser')).toHaveCount(0);
});

test('actual swap handlers preserve preset values and custom dimensions', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'WidthHeightSelector', { preset: '832×1216 - portrait', width: 832, height: 1216 });
    const swapped = await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        node.swapDimensions();
        return node.widgets.filter(widget => ['preset', 'width', 'height'].includes(widget.name)).map(widget => widget.value);
    }, id);
    expect(swapped).toEqual(['1216×832 - landscape', '1216', '832']);
    await createNode(page, 'EmptyLatentBatch', { preset: 'custom', width: 640, height: 960 });
    const latent = page.locator('[data-node="EmptyLatentBatch"]');
    await latent.getByRole('button', { name: /Swap/ }).click();
    await expect(latent.getByLabel('width', { exact: true })).toHaveValue('960');
    await expect(latent.getByLabel('height', { exact: true })).toHaveValue('640');
});

for (const name of ['WidthHeightSelector', 'EmptyLatentBatch']) {
test(`${name}: shared swap supports keyboard, callbacks and live themes`, async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, name, { preset: '832×1216 - portrait', width: 832, height: 1216, batch_size: 3 });
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        node.element.style.width = '220px';
        window.swapNotifications = [];
        for (const widget of node.widgets.filter(widget => ['width', 'height'].includes(widget.name))) {
            widget.callback = function (value, canvas, owner) { swapNotifications.push({ name: this.name, value, canvas: canvas === kikoHost.app.canvas, owner: owner === node }); };
        }
    }, id);
    const panel = page.locator('.ca-dimension-swap');
    const button = panel.getByRole('button', { name: 'Swap width and height', exact: true });
    await expect(button).toHaveCSS('background-color', 'rgb(8, 119, 187)');
    for (const theme of ['light', 'dark']) {
        await page.evaluate(theme => document.body.style.setProperty('--bg-color', theme === 'light' ? '#fff' : '#202020'), theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
    }
    await button.focus();
    await page.keyboard.press('Enter');
    expect(await page.evaluate(() => swapNotifications)).toEqual([
        { name: 'width', value: '1216', canvas: true, owner: true },
        { name: 'height', value: '832', canvas: true, owner: true },
    ]);
    await page.keyboard.press('Space');
    const node = page.locator(`[data-node="${name}"]`);
    await expect(node.getByLabel('width', { exact: true })).toHaveValue('832');
    await expect(node.getByLabel('height', { exact: true })).toHaveValue('1216');
    await expect(node.getByLabel('batch_size', { exact: true })).toHaveValue('3');
    expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
});

test(`${name}: swap mounting is idempotent and removal disposes its control`, async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, name, { preset: 'custom', width: 640, height: 960 });
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        node.createSwapButton();
        node.createSwapButton();
    }, id);
    await expect(page.locator('.ca-dimension-swap')).toHaveCount(1);
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        window.detachedSwap = node.swapButtonWidget.element;
        window.swapTheme = detachedSwap.dataset.caTheme;
        window.removedSwapNode = kikoHost.removeNode(id);
        detachedSwap.querySelector('button').click();
        document.body.style.setProperty('--bg-color', swapTheme === 'light' ? '#202020' : '#fff');
    }, id);
    expect(await page.evaluate(() => ({ aborted: removedSwapNode.swapScope.signal.aborted, theme: detachedSwap.dataset.caTheme, width: removedSwapNode.widgets.find(widget => widget.name === 'width').value, removed: removedSwapNode.removed }))).toEqual({ aborted: true, theme: await page.evaluate(() => swapTheme), width: '640', removed: true });
    await expect(page.locator('.ca-dimension-swap')).toHaveCount(0);
});
}

test('local image selection persists and the real node loads the selected PNG tensor', async ({ page, request }) => {
    await openHost(page);
    const id = await createNode(page, 'KikoLocalImageLoader');
    const image = page.getByAltText('cat & dog.png', { exact: true });
    await expect(image).toBeVisible();
    await expect.poll(() => image.evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
    const selected = page.waitForResponse(response => response.url().endsWith('/set_node_selection'));
    await image.click();
    expect((await selected).ok()).toBe(true);
    const selectedPath = `${(await state(request)).input}/cat & dog.png`;
    expect((await state(request)).selections[String(id)].image.path).toBe(selectedPath);
    const executed = await request.post('/__test__/execute/KikoLocalImageLoader', { data: { unique_id: String(id) } });
    await expect(executed).toBeOK();
    expect((await executed.json()).shape).toEqual([1, 12, 16, 3]);
    await page.reload();
    await expect(page.locator('body')).toHaveAttribute('data-ready', 'true');
    expect(await createNode(page, 'KikoLocalImageLoader')).toBe(id);
    await expect(page.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
    expect((await state(request)).selections[String(id)].image.path).toBe(selectedPath);
});

test('gallery navigates folders and saves and removes paths through the actual routes', async ({ page, request }) => {
    await openHost(page);
    await createNode(page, 'KikoLocalImageLoader');
    await page.locator('.kiko-folder-name').filter({ hasText: /^sub$/ }).click();
    await expect(page.getByAltText('forest.png', { exact: true })).toBeVisible();
    await page.locator('.kiko-save-path').click();
    await expect.poll(async () => (await state(request)).config.saved_paths).toHaveLength(1);
    const saved = (await state(request)).config.saved_paths[0];
    await page.reload();
    await expect(page.locator('body')).toHaveAttribute('data-ready', 'true');
    await createNode(page, 'KikoLocalImageLoader');
    await expect(page.locator('.kiko-path-presets option')).toHaveCount(2);
    await page.locator('.kiko-path-presets').selectOption(saved);
    await page.locator('.kiko-delete-path').click();
    await expect.poll(async () => (await state(request)).config.saved_paths).toEqual([]);
    await page.locator('.kiko-up-folder').click();
    await expect(page.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
});

test('gallery rejects disallowed folders and retries after a network error', async ({ page, request }) => {
    await openHost(page);
    const id = await createNode(page, 'KikoLocalImageLoader');
    const info = await state(request);
    await expect(page.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
    await page.locator('.kiko-path-input').fill(info.outside);
    const denied = page.waitForResponse(response => response.url().includes('/images?'));
    await page.locator('.kiko-browse').click();
    expect((await denied).status()).toBe(403);
    await expect(page.locator('.kiko-status-message')).toBeVisible();
    const deniedSelection = await request.post('/kiko_local_image_loader/set_node_selection', { data: { node_id: id, path: `${info.outside}/secret.png`, type: 'image' } });
    expect(deniedSelection.status()).toBe(403);
    expect((await state(request)).selections).toEqual({});
    await page.locator('.kiko-path-input').fill(info.input);
    await page.route('**/kiko_local_image_loader/images?*', route => route.abort('failed'), { times: 1 });
    await page.locator('.kiko-browse').click();
    await expect(page.locator('.kiko-status-message')).toHaveText('Error loading directory');
    await page.locator('.kiko-browse').click();
    await expect(page.locator('.kiko-status-message')).toBeHidden();
    await expect(page.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
});

test('real display node output renders as text and replaces previous widgets', async ({ page, request }) => {
    await openHost(page);
    const id = await createNode(page, 'DisplayText');
    const text = 'Positive prompt: <img src=x onerror="window.injected=true">\nNegative prompt: blur';
    const response = await request.post('/__test__/execute/DisplayText', { data: { text } });
    await expect(response).toBeOK();
    const data = await response.json();
    await page.evaluate(({ id, message }) => kikoHost.nodes.get(String(id)).onExecuted(message), { id, message: data.ui });
    await expect(page.getByLabel('Positive prompt', { exact: true })).toHaveValue('<img src=x onerror="window.injected=true">');
    await expect(page.getByLabel('Negative prompt', { exact: true })).toHaveValue('blur');
    expect(await page.evaluate(() => window.injected)).toBeUndefined();
    const next = await (await request.post('/__test__/execute/DisplayText', { data: { text: 'Replacement' } })).json();
    await page.evaluate(({ id, message }) => kikoHost.nodes.get(String(id)).onExecuted(message), { id, message: next.ui });
    await expect(page.locator('textarea')).toHaveCount(1);
    await expect(page.getByLabel('Text output', { exact: true })).toHaveValue('Replacement');
    await expect(page.getByLabel('Text output', { exact: true })).toHaveAttribute('readonly', '');
});

test('seed history persists across reloads and removal clears its watcher', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'SeedHistory', { seed: 42 });
    await page.getByRole('button', { name: /Generate/ }).click();
    const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('comfyui_kikotools_seed_history')));
    expect(saved).toHaveLength(1);
    expect(saved[0].seed).toBeGreaterThanOrEqual(0);
    await page.reload();
    await expect(page.locator('body')).toHaveAttribute('data-ready', 'true');
    await createNode(page, 'SeedHistory', { seed: 42 });
    expect(await page.evaluate(() => kikoHost.nodes.get('1').seedHistory[0].seed)).toBe(saved[0].seed);
    await page.getByRole('button', { name: /Clear/ }).click();
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('comfyui_kikotools_seed_history')))).toEqual([]);
    await expect.poll(() => page.evaluate(() => Boolean(kikoHost.nodes.get('1').seedValueWatcher))).toBe(true);
    expect(await page.evaluate(id => {
        const node = kikoHost.removeNode(id);
        return { watcher: node.seedValueWatcher, registered: window.seedHistoryNodes.includes(node), removed: node.removed };
    }, id)).toEqual({ watcher: null, registered: false, removed: true });
});

test('shared seed history supports keyboard selection, themes and local status feedback', async ({ page }) => {
    await openHost(page);
    await page.evaluate(() => Object.defineProperty(crypto, 'randomUUID', { value: undefined }));
    const id = await createNode(page, 'SeedHistory', { seed: 42 });
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        node.addSeedToHistory(123);
        node.addSeedToHistory(456);
    }, id);
    const panel = page.locator('.ca-seed-history');
    await expect(panel).toHaveCount(1);
    for (const theme of ['light', 'dark']) {
        await page.evaluate(theme => document.body.style.setProperty('--bg-color', theme === 'light' ? '#ffffff' : '#202020'), theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
    }
    const entry = panel.getByRole('button', { name: 'Use seed 123', exact: true });
    await entry.focus();
    await page.keyboard.press('Enter');
    await expect(entry).toHaveAttribute('aria-pressed', 'true');
    await expect(panel.getByRole('status')).toHaveText('Loaded: 123');
    expect(await page.evaluate(id => Number(kikoHost.nodes.get(String(id)).widgets.find(widget => widget.name === 'seed').value), id)).toBe(123);
    await page.evaluate(id => kikoHost.nodes.get(String(id)).addSeedToHistory(789), id);
    await expect(entry).toBeFocused();
    await panel.getByRole('button', { name: 'Generate', exact: true }).click();
    await expect(panel.getByRole('status')).toContainText('Generated:');
    await panel.getByRole('button', { name: 'Clear', exact: true }).click();
    await expect(panel.getByRole('status')).toHaveText('History cleared');
    await expect(panel.getByText('No seeds tracked')).toBeVisible();
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('comfyui_kikotools_seed_history')))).toEqual([]);
});

test('seed history auto-hide protects keyboard focus and its disclosure reopens with Space', async ({ page }) => {
    await openHost(page);
    await page.clock.install();
    const id = await createNode(page, 'SeedHistory', { seed: 42 });
    await page.evaluate(id => kikoHost.nodes.get(String(id)).addSeedToHistory(123), id);
    const panel = page.locator('.ca-seed-history');
    const entry = panel.getByRole('button', { name: 'Use seed 123', exact: true });
    await entry.focus();
    await page.clock.runFor(3000);
    await expect(entry).toBeVisible();
    await expect(entry).toBeFocused();
    await panel.getByRole('button', { name: 'Generate', exact: true }).focus();
    await page.clock.runFor(2600);
    const restore = panel.getByRole('button', { name: 'Show history', exact: true });
    await expect(restore).toHaveAttribute('aria-expanded', 'false');
    await restore.focus();
    await page.keyboard.press('Space');
    await expect(panel.getByRole('list', { name: 'Recent seeds' })).toBeVisible();
    await expect(panel.getByRole('button', { name: 'Hide history', exact: true })).toHaveAttribute('aria-expanded', 'true');
    await entry.hover();
    await page.clock.runFor(3000);
    await expect(entry).toBeVisible();
    await page.mouse.move(0, 0);
    await page.clock.runFor(2600);
    await expect(restore).toBeVisible();
});

test('seed history removal cancels delayed setup and retries and disposes theme listeners', async ({ page }) => {
    await openHost(page);
    await page.clock.install();
    const early = await createNode(page, 'SeedHistory', { seed: 42 });
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        window.removedSeedNode = node;
        window.seedSetups = 0;
        node.setupSeedWidgetCallbacks = () => window.seedSetups++;
        node.addSeedToHistory(123);
        kikoHost.removeNode(id);
    }, early);
    await page.clock.runFor(3000);
    expect(await page.evaluate(() => ({ setups: seedSetups, watcher: removedSeedNode.seedValueWatcher, hide: removedSeedNode.hideTimer, aborted: removedSeedNode.seedScope.signal.aborted }))).toEqual({ setups: 0, watcher: null, hide: null, aborted: true });
    const retry = await createNode(page, 'SeedHistory');
    await page.clock.runFor(101);
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        window.detachedSeedPanel = node.seedWidget.element;
        window.detachedSeedTheme = detachedSeedPanel.dataset.caTheme;
        window.retrySeedNode = kikoHost.removeNode(id);
        document.body.style.setProperty('--bg-color', detachedSeedTheme === 'light' ? '#202020' : '#ffffff');
    }, retry);
    await page.clock.runFor(3000);
    expect(await page.evaluate(() => ({ watcher: retrySeedNode.seedValueWatcher, setup: retrySeedNode.seedSetupTimer, theme: detachedSeedPanel.dataset.caTheme === detachedSeedTheme, registered: seedHistoryNodes.length }))).toEqual({ watcher: null, setup: null, theme: true, registered: 0 });
});

test('seed history keeps ten unique valid seeds and restores workflow history safely', async ({ page }) => {
    await openHost(page);
    await page.evaluate(() => localStorage.setItem('comfyui_kikotools_seed_history', '{broken'));
    const id = await createNode(page, 'SeedHistory', { seed: 42 });
    expect(await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        for (let seed = 0; seed < 12; seed++) node.addSeedToHistory(seed);
        node.addSeedToHistory(0);
        node.addSeedToHistory(0);
        node.addSeedToHistory('invalid');
        const data = node.serialize();
        node.clearSeedHistory();
        node.configure(data);
        return node.seedHistory.map(item => item.seed);
    }, id)).toEqual([0, 11, 10, 9, 8, 7, 6, 5, 4, 3]);
    const panel = page.locator('.ca-seed-history');
    await expect(panel.getByRole('button', { name: 'Use seed 0', exact: true })).toBeVisible();
    await page.evaluate(id => kikoHost.nodes.get(String(id)).configure({ seedHistory: [{ seed: '<img src=x onerror=alert(1)>', timestamp: 0 }] }), id);
    await expect(panel.getByText('No seeds tracked')).toBeVisible();
    await expect(panel.locator('img')).toHaveCount(0);
});

test('seed actions pass the host callback context and polling tracks manual values once', async ({ page }) => {
    await openHost(page);
    await page.clock.install();
    const id = await createNode(page, 'SeedHistory', { seed: 42 });
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        const widget = node.widgets.find(widget => widget.name === 'seed');
        window.seedCallbacks = [];
        widget.callback = function (value, canvas, owner) {
            seedCallbacks.push({ value, canvas: canvas === kikoHost.app.canvas, owner: owner === node, widget: this === widget });
        };
        node.addSeedToHistory(123);
    }, id);
    const panel = page.locator('.ca-seed-history');
    await panel.getByRole('button', { name: 'Use seed 123', exact: true }).click();
    await panel.getByRole('button', { name: 'Generate', exact: true }).click();
    expect(await page.evaluate(() => seedCallbacks)).toEqual([
        { value: 123, canvas: true, owner: true, widget: true },
        { value: expect.any(Number), canvas: true, owner: true, widget: true },
    ]);
    await page.clock.runFor(101);
    await page.evaluate(id => { kikoHost.nodes.get(String(id)).widgets.find(widget => widget.name === 'seed').value = 987; }, id);
    await page.clock.runFor(1100);
    await expect(panel.getByRole('button', { name: 'Use seed 987', exact: true })).toHaveCount(1);
    await page.evaluate(id => {
        Storage.prototype.setItem = () => { throw new DOMException('Storage unavailable', 'SecurityError'); };
        kikoHost.nodes.get(String(id)).addSeedToHistory(654);
    }, id);
    await expect(panel.getByRole('button', { name: 'Use seed 654', exact: true })).toBeVisible();
    await page.evaluate(id => { kikoHost.nodes.get(String(id)).widgets.find(widget => widget.name === 'seed').value = 555; }, id);
    await panel.getByRole('button', { name: 'Clear', exact: true }).click();
    await page.clock.runFor(1100);
    await expect(panel.getByText('No seeds tracked')).toBeVisible();
});

test('workflow timer responds to execution events and detaches removed nodes', async ({ page }) => {
    await page.clock.install();
    await openHost(page);
    const id = await createNode(page, 'KikoWorkflowTimer');
    await page.evaluate(() => kikoHost.emit('execution_start'));
    await page.clock.runFor(1234);
    await expect(page.locator('.kiko-timer-display')).not.toHaveText('00:00:000');
    await page.evaluate(() => kikoHost.emit('execution_interrupted'));
    await expect(page.locator('.kiko-timer-display')).not.toHaveClass(/running/);
    const stopped = await page.locator('.kiko-timer-display').textContent();
    await page.clock.runFor(500);
    await expect(page.locator('.kiko-timer-display')).toHaveText(stopped);
    expect(await page.evaluate(id => kikoHost.removeNode(id).removed, id)).toBe(true);
    await page.evaluate(() => { kikoHost.emit('execution_start'); kikoHost.emit('executing', null); });
    await expect(page.locator('.kiko-timer-display')).toHaveCount(0);
});

async function showTimerColorSetting(page) {
    await page.evaluate(() => {
        const id = 'kikotools.workflow_timer.color';
        const definition = kikoHost.settingDefinitions.get(id);
        const setValue = value => {
            kikoHost.app.ui.settings.setSettingValue(id, value);
            const replacement = definition.type(definition.name, setValue, value);
            timerColorSetting.replaceWith(replacement);
            window.timerColorSetting = replacement;
        };
        window.timerColorSetting = definition.type(definition.name, setValue, kikoHost.settings.get(id));
        document.body.append(timerColorSetting);
    });
}

test('shared workflow timer follows themes, saved color and reduced motion', async ({ page }) => {
    await openHost(page);
    await page.evaluate(() => kikoHost.app.ui.settings.setSettingValue('kikotools.workflow_timer.color', '#ff9966'));
    const id = await createNode(page, 'KikoWorkflowTimer');
    const panel = page.locator('.ca-workflow-timer');
    await expect(panel).toBeVisible();
    const timer = panel.getByRole('timer', { name: 'Elapsed workflow time' });
    await expect(timer).toHaveCSS('color', 'rgb(255, 153, 102)');
    for (const theme of ['light', 'dark']) {
        await page.evaluate(theme => document.body.style.setProperty('--bg-color', theme === 'light' ? '#ffffff' : '#202020'), theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
    }
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.evaluate(() => kikoHost.emit('execution_start'));
    await expect(timer).toHaveCSS('animation-name', 'none');
    await page.evaluate(() => kikoHost.emit('execution_interrupted'));
    await expect(timer).toHaveCSS('animation-name', 'none');
    await page.evaluate(id => kikoHost.nodes.get(String(id)).onConfigure({ properties: { elapsed_time_str: '02:03:456' } }), id);
    await expect(timer).toHaveText('02:03:456');
    expect(await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        const saved = { properties: { other: 'kept' } };
        node.onSerialize(saved);
        node.properties.elapsed_time_str = 'changed after saving';
        return saved.properties;
    }, id)).toEqual({ other: 'kept', elapsed_time_str: '02:03:456' });
});

test('workflow timers join active execution and apply live appearance until every end event', async ({ page }) => {
    await openHost(page);
    await page.clock.install();
    await createNode(page, 'KikoWorkflowTimer');
    await page.evaluate(() => kikoHost.emit('execution_start'));
    await page.clock.runFor(1200);
    await createNode(page, 'KikoWorkflowTimer');
    const displays = page.locator('.kiko-timer-display');
    await expect(displays.nth(1)).toHaveClass(/running/);
    await expect.poll(() => displays.evaluateAll(elements => new Set(elements.map(element => element.textContent)).size)).toBe(1);
    await page.evaluate(() => {
        kikoHost.app.ui.settings.setSettingValue('kikotools.workflow_timer.color', '#123456');
        kikoHost.app.ui.settings.setSettingValue('kikotools.workflow_timer.glow', false);
    });
    for (const display of await displays.all()) {
        await expect(display).toHaveCSS('color', 'rgb(18, 52, 86)');
        await expect(display).toHaveClass(/no-glow/);
    }
    for (const event of ['executing', 'execution_error', 'execution_interrupted']) {
        await page.evaluate(() => kikoHost.emit('execution_start'));
        await page.clock.runFor(1234);
        await page.evaluate(event => kikoHost.emit(event, null), event);
        await expect(displays.nth(0)).not.toHaveClass(/running/);
        const stopped = await displays.nth(0).textContent();
        await page.clock.runFor(1000);
        await expect(displays.nth(1)).toHaveText(stopped);
        expect(await page.evaluate(() => kikoHost.app.graph._nodes.map(node => node.properties.elapsed_time_str))).toEqual([stopped, stopped]);
    }
});

test('timer color controls validate hex, support keyboard sliders and presets and close with Escape', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'KikoWorkflowTimer');
    await showTimerColorSetting(page);
    const trigger = page.getByRole('button', { name: 'Choose timer color', exact: true });
    await trigger.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog', { name: 'Timer color', exact: true });
    await expect(dialog).toBeVisible();
    const hex = dialog.getByLabel('Hex color', { exact: true });
    await hex.fill('not-a-color');
    await hex.press('Tab');
    await expect(hex).toHaveAttribute('aria-invalid', 'true');
    expect(await page.evaluate(() => kikoHost.settings.get('kikotools.workflow_timer.color'))).toBe('#0877bb');
    await hex.fill('112233');
    await hex.press('Tab');
    await expect(dialog).toBeVisible();
    await expect(hex).toHaveAttribute('aria-invalid', 'false');
    await expect(page.locator('.kiko-timer-display')).toHaveCSS('color', 'rgb(17, 34, 51)');
    await dialog.getByRole('button', { name: 'Use color #4A90D9', exact: true }).focus();
    await page.keyboard.press('Space');
    await expect(dialog.getByRole('button', { name: 'Use color #4A90D9', exact: true })).toHaveAttribute('aria-pressed', 'true');
    const before = await hex.inputValue();
    const hue = dialog.getByRole('slider', { name: 'Hue', exact: true });
    await hue.hover();
    expect(await hex.inputValue()).toBe(before);
    await hue.focus();
    await page.keyboard.press('ArrowRight');
    expect(await hex.inputValue()).not.toBe(before);
    await expect(hue).toHaveAttribute('aria-valuetext', /degrees/);
    for (const label of ['Saturation', 'Brightness']) {
        const slider = dialog.getByRole('slider', { name: label, exact: true });
        await slider.focus();
        await page.keyboard.press('End');
        await expect(slider).toHaveValue('100');
    }
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
    await trigger.click();
    await dialog.getByRole('button', { name: 'Done', exact: true }).click();
    await expect(trigger).toBeFocused();
});

test('timer removal releases polling and color setting removal closes and disposes its dialog', async ({ page }) => {
    await openHost(page);
    await page.clock.install();
    await page.evaluate(() => {
        window.timerIntervals = new Set();
        const start = window.setInterval;
        const stop = window.clearInterval;
        window.setInterval = (...args) => { const id = start(...args); timerIntervals.add(id); return id; };
        window.clearInterval = id => { timerIntervals.delete(id); stop(id); };
    });
    const first = await createNode(page, 'KikoWorkflowTimer');
    const second = await createNode(page, 'KikoWorkflowTimer');
    await page.evaluate(() => kikoHost.emit('execution_start'));
    expect(await page.evaluate(() => timerIntervals.size)).toBe(1);
    await page.evaluate(id => kikoHost.removeNode(id), first);
    expect(await page.evaluate(() => timerIntervals.size)).toBe(1);
    await page.evaluate(id => { window.removedTimer = kikoHost.removeNode(id); }, second);
    expect(await page.evaluate(() => ({ intervals: timerIntervals.size, aborted: removedTimer.timerScope?.signal.aborted }))).toEqual({ intervals: 0, aborted: true });
    await showTimerColorSetting(page);
    await page.getByRole('button', { name: 'Choose timer color', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Timer color', exact: true })).toBeVisible();
    await page.evaluate(() => {
        window.detachedTimerPicker = timerColorSetting;
        timerColorSetting.remove();
    });
    await expect(page.getByRole('dialog', { name: 'Timer color', exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => detachedTimerPicker.scope.signal.aborted)).toBe(true);
    await page.evaluate(() => document.body.append(detachedTimerPicker));
    await page.getByRole('button', { name: 'Choose timer color', exact: true }).click();
    await expect(page.getByRole('dialog', { name: 'Timer color', exact: true })).toHaveCount(1);
});

test('autocomplete inserts embedding paths from the real plugin endpoint and cleans up its widget', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'TextInput', { text: '' });
    await expect.poll(() => page.evaluate(() => window.kikotools.autocomplete.embeddings.length)).toBe(2);
    const prompt = page.getByLabel('text', { exact: true });
    await prompt.fill('embedding:ca');
    const suggestions = page.locator('.kikotools-autocomplete-suggestions');
    await expect(suggestions).toBeVisible();
    await expect(suggestions).toContainText('cat');
    await prompt.press('ArrowDown');
    await prompt.press('Enter');
    await expect(prompt).toHaveValue(/embedding:portraits\/cat/);
    await expect(suggestions).toBeHidden();
    expect(await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        const entry = node.widgets.find(widget => widget.name === 'text');
        kikoHost.removeNode(id);
        return window.kikotools.autocomplete.activeWidgets.has(entry);
    }, id)).toBe(false);
});

test('real image save output opens a preview, closes, and reuses the viewer on execution', async ({ page, request }) => {
    await openHost(page);
    const id = await createNode(page, 'KikoSaveImage', { format: 'PNG', quality: 90 });
    const response = await request.post('/__test__/execute/KikoSaveImage', { data: { filename_prefix: 'Browser image' } });
    await expect(response).toBeOK();
    const result = await response.json();
    expect(result.ui.kiko_enhanced).toHaveLength(1);
    const execute = () => page.evaluate(({ id, message }) => kikoHost.nodes.get(String(id)).onExecuted(message), { id, message: result.ui });
    await execute();
    const viewer = page.locator('kiko-image-viewer');
    await expect(viewer).toBeVisible();
    await expect(viewer.locator('img')).toHaveCount(1);
    await expect.poll(() => viewer.locator('img').evaluate(image => image.complete && image.naturalWidth > 0)).toBe(true);
    await viewer.getByTitle('Close', { exact: true }).click();
    await expect(viewer).toBeHidden();
    await execute();
    await expect(viewer).toHaveCount(1);
    await expect(viewer).toBeVisible();
    await viewer.getByTitle('Minimize', { exact: true }).click();
    await expect(viewer.locator('.kiko-viewer-container')).toBeHidden();
});

async function savedImageResult(page, request, count = 1) {
    const id = await createNode(page, 'KikoSaveImage', { format: 'PNG', quality: 90 });
    const response = await request.post('/__test__/execute/KikoSaveImage', { data: { filename_prefix: 'Window test' } });
    await expect(response).toBeOK();
    const message = (await response.json()).ui;
    message.kiko_enhanced = Array.from({ length: count }, () => ({ ...message.kiko_enhanced[0] }));
    await page.evaluate(({ id, message }) => kikoHost.nodes.get(String(id)).onExecuted(message), { id, message });
    return { id, message };
}

test('shared saved-image window follows themes and supports keyboard close and reopen', async ({ page, request }) => {
    await openHost(page);
    const { id } = await savedImageResult(page, request);
    const viewer = page.getByRole('dialog', { name: 'Saved images', exact: true });
    await expect(viewer).toBeVisible();
    await page.evaluate(() => document.body.style.setProperty('--bg-color', '#fafafa'));
    await expect(viewer).toHaveAttribute('data-ca-theme', 'light');
    await viewer.getByTitle('Minimize', { exact: true }).click();
    await expect(viewer.locator('.kiko-viewer-container')).toBeHidden();
    await viewer.getByTitle('Restore', { exact: true }).click();
    await expect(viewer.locator('.kiko-viewer-container')).toBeVisible();
    await viewer.getByTitle('Close', { exact: true }).focus();
    await page.keyboard.press('Escape');
    await expect(viewer).toBeHidden();
    await page.locator(`[data-node="KikoSaveImage"]`).getByRole('button', { name: 'Show images', exact: true }).click();
    await expect(viewer).toBeVisible();
    expect(await page.evaluate(id => kikoHost.nodes.get(String(id)).kikoViewer.isConnected, id)).toBe(true);
});

test('saved-image ownership transfers safely and deletion cleans up only the owner window', async ({ page, request }) => {
    await openHost(page);
    const first = await savedImageResult(page, request);
    const second = await savedImageResult(page, request);
    expect(await page.evaluate(id => Boolean(kikoHost.nodes.get(String(id)).kikoViewer), second.id)).toBe(true);
    await page.evaluate(id => kikoHost.removeNode(id), first.id);
    await expect(page.locator('kiko-image-viewer')).toBeVisible();
    await page.evaluate(id => kikoHost.removeNode(id), second.id);
    await expect(page.locator('kiko-image-viewer')).toHaveCount(0);
});

test('saved-image window moves and resizes by keyboard and remains inside a shrinking viewport', async ({ page, request }) => {
    await page.setViewportSize({ width: 1200, height: 900 });
    await openHost(page);
    await savedImageResult(page, request);
    const viewer = page.locator('kiko-image-viewer');
    const move = viewer.getByRole('button', { name: 'Move image viewer with arrow keys', exact: true });
    await move.focus();
    const before = await viewer.boundingBox();
    await page.keyboard.press('ArrowLeft');
    expect((await viewer.boundingBox()).x).toBeLessThan(before.x);
    const resize = viewer.getByRole('button', { name: 'Resize image viewer with arrow keys', exact: true });
    await resize.focus();
    await page.keyboard.press('ArrowRight');
    expect((await viewer.boundingBox()).width).toBeGreaterThan(before.width);
    const imageBefore = await viewer.locator('img').boundingBox();
    await page.keyboard.press('ArrowDown');
    expect((await viewer.locator('img').boundingBox()).height).toBeGreaterThan(imageBefore.height);
    const info = await viewer.locator('.kiko-image-info').boundingBox();
    const content = await viewer.locator('.kiko-viewer-container').boundingBox();
    expect(info.y + info.height).toBeLessThanOrEqual(content.y + content.height);
    await page.setViewportSize({ width: 360, height: 500 });
    await expect.poll(async () => {
        const rect = await viewer.boundingBox();
        return rect.x >= 0 && rect.y >= 0 && rect.x + rect.width <= 361 && rect.y + rect.height <= 501;
    }).toBe(true);
});

test('saved-image batch selection downloads and resets for new execution results', async ({ page, request }) => {
    await openHost(page);
    const { id, message } = await savedImageResult(page, request, 2);
    const viewer = page.locator('kiko-image-viewer');
    const choices = viewer.getByRole('checkbox');
    await expect(choices).toHaveCount(2);
    await choices.first().check();
    await expect(viewer.locator('.selected-count')).toHaveText('1');
    await viewer.getByRole('button', { name: 'Select all', exact: true }).click();
    await expect(choices.nth(1)).toBeChecked();
    const download = page.waitForEvent('download');
    await viewer.getByRole('button', { name: /Download image 1:/ }).click();
    expect((await download).suggestedFilename()).toBe(message.kiko_enhanced[0].filename);
    await page.evaluate(({ id, message }) => kikoHost.nodes.get(String(id)).onExecuted(message), { id, message: { kiko_enhanced: [message.kiko_enhanced[0]] } });
    expect(await viewer.evaluate(element => element.selectedImages.size)).toBe(0);
    await expect(viewer.getByRole('checkbox')).toHaveCount(0);
});

test('saved-image window pointer handles drag resize and cancel without losing reachability', async ({ page, request }) => {
    await page.setViewportSize({ width: 1200, height: 900 });
    await openHost(page);
    await savedImageResult(page, request);
    const viewer = page.locator('kiko-image-viewer');
    const before = await viewer.boundingBox();
    const handle = await viewer.locator('[data-window-move]').boundingBox();
    await page.mouse.move(handle.x + 20, handle.y + 15);
    await page.mouse.down();
    await page.mouse.move(handle.x - 100, handle.y + 35, { steps: 4 });
    await page.mouse.up();
    const moved = await viewer.boundingBox();
    expect(moved.x).toBeLessThan(before.x);
    await expect(viewer).not.toHaveClass(/ca-dragging/);
    const resize = await viewer.locator('[data-window-resize]').boundingBox();
    await page.mouse.move(resize.x + 12, resize.y + 12);
    await page.mouse.down();
    await page.mouse.move(resize.x + 60, resize.y + 15, { steps: 4 });
    await page.mouse.up();
    expect((await viewer.boundingBox()).width).toBeGreaterThan(moved.width);
    const next = await viewer.locator('[data-window-move]').boundingBox();
    await page.mouse.move(next.x + 20, next.y + 15);
    await page.mouse.down();
    await viewer.dispatchEvent('pointercancel');
    await expect(viewer).not.toHaveClass(/ca-dragging/);
    await page.mouse.up();
});

test('delayed selected-image opens stop on close replacement and owner removal', async ({ page, request }) => {
    await openHost(page);
    const { id, message } = await savedImageResult(page, request, 2);
    await page.clock.install();
    await page.evaluate(() => {
        window.openedImages = [];
        window.open = url => { window.openedImages.push(url); return {}; };
        const viewer = document.querySelector('kiko-image-viewer');
        viewer.handleBulkAction('select-all');
        viewer.handleBulkAction('open-all');
    });
    await page.clock.runFor(200);
    expect(await page.evaluate(() => window.openedImages.length)).toBe(2);
    for (const action of ['close', 'replace', 'remove']) {
        await page.evaluate(({ id, message, action }) => {
            const node = kikoHost.nodes.get(String(id));
            node.onExecuted(message);
            const viewer = document.querySelector('kiko-image-viewer');
            viewer.handleBulkAction('select-all');
            viewer.handleBulkAction('open-all');
            if (action === 'close') viewer.close();
            if (action === 'replace') node.onExecuted(message);
            if (action === 'remove') kikoHost.removeNode(id);
        }, { id, message, action });
        await page.clock.runFor(500);
        expect(await page.evaluate(() => window.openedImages.length)).toBe(2);
    }
});

test('Display Any renders real multiline output and restores serialized values without duplicate widgets', async ({ page, request }) => {
    await openHost(page);
    const id = await createNode(page, 'DisplayAny');
    const response = await request.post('/__test__/execute/DisplayAny', { data: { input: Array.from({ length: 45 }, (_, index) => `Line ${index}`).join('\n') } });
    await expect(response).toBeOK();
    const result = await response.json();
    await page.evaluate(({ id, message }) => kikoHost.nodes.get(String(id)).onExecuted(message), { id, message: result.ui });
    await expect(page.locator('textarea')).toHaveCount(1);
    expect(await page.locator('textarea').evaluateAll(elements => elements.map(element => element.value).join('\n'))).toBe(result.ui.text[0]);
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        node.configure({ widgets_values: ['Restored value'] });
        node.onConfigure?.();
    }, id);
    await expect(page.locator('textarea')).toHaveCount(1);
    await expect(page.getByLabel('Value output', { exact: true })).toHaveValue('Restored value');
});

test('gallery pagination sorting and hidden-folder controls use real directory pages', async ({ page, request }) => {
    await expect(await request.post('/__test__/reset', { data: { extra_images: 52 } })).toBeOK();
    await openHost(page);
    await createNode(page, 'KikoLocalImageLoader');
    const folder = name => page.locator('.kiko-folder-name').filter({ hasText: new RegExp(`^${name}$`) });
    await expect(folder('sub')).toBeVisible();
    await expect(folder('\\.hidden')).toHaveCount(0);
    await page.locator('.kiko-hide-dot-folders').uncheck();
    await expect(folder('\\.hidden')).toBeVisible();
    await folder('bulk').click();
    await expect(page.locator('.kiko-card-info-panel')).toHaveCount(50);
    await expect(page.locator('.kiko-card-info-panel').first()).toHaveText('0000.png');
    await page.locator('.kiko-sort-order').selectOption('desc');
    await expect(page.locator('.kiko-card-info-panel').first()).toHaveText('0051.png');
    await page.locator('.kiko-pagination').getByRole('button', { name: '2', exact: true }).click();
    await expect(page.locator('.kiko-card-info-panel')).toHaveCount(2);
    await expect(page.getByAltText('0000.png', { exact: true })).toBeVisible();
    await page.locator('.kiko-pagination').getByRole('button', { name: '◀', exact: true }).click();
    await expect(page.locator('.kiko-card-info-panel')).toHaveCount(50);
    await page.locator('.kiko-pagination').getByRole('button', { name: '▶', exact: true }).click();
    await expect(page.locator('.kiko-card-info-panel')).toHaveCount(2);
});

test('gallery directory autocomplete handles keyboard selection escape and navigation', async ({ page, request }) => {
    await openHost(page);
    await createNode(page, 'KikoLocalImageLoader');
    await expect(page.getByAltText('cat & dog.png', { exact: true })).toBeVisible();
    const input = page.locator('.kiko-path-input');
    const dropdown = page.locator('.kiko-autocomplete-dropdown');
    const directory = (await state(request)).input;
    await input.fill(`${directory}/su`);
    await expect(dropdown).toBeVisible();
    await expect(dropdown.locator('.folder-name')).toContainText('sub');
    await input.press('ArrowDown');
    await expect(dropdown.locator('.selected')).toHaveCount(1);
    await input.press('ArrowUp');
    await expect(dropdown.locator('.selected')).toHaveCount(0);
    await input.press('Escape');
    await expect(dropdown).toBeHidden();
    await input.fill(`${directory}/su`);
    await expect(dropdown).toBeVisible();
    await input.press('ArrowDown');
    await input.press('Tab');
    await expect(input).toBeFocused();
    await expect(input).toHaveValue(`${directory}/sub/`);
    await expect(dropdown).toBeHidden();
    await input.press('Enter');
    await expect(page.getByAltText('forest.png', { exact: true })).toBeVisible();
});

async function openDimensions(page) {
    await page.evaluate(() => {
        const node = kikoHost.app.graph._nodes.at(-1);
        node.computeSize = () => [180, 120];
        node.setSize = size => { node.size = size; node.applied = (node.applied || 0) + 1; };
        const opener = document.createElement('button');
        opener.textContent = 'Edit dimensions';
        opener.onclick = () => kikoHost.extensions.find(item => item.name === 'ComfyAssets.Extensions').getNodeMenuItems(node)[1].callback();
        document.body.append(opener);
    });
    await page.getByRole('button', { name: 'Edit dimensions', exact: true }).click();
    return page.getByRole('dialog', { name: 'Node Dimensions', exact: true });
}

test('Node Dimensions validates, applies once and enforces content minimums', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'WidthHeightSelector');
    const dialog = await openDimensions(page);
    await expect(dialog).toBeVisible();
    await page.getByRole('button', { name: 'Edit dimensions', exact: true }).evaluate(element => element.focus());
    await expect(dialog.getByLabel('Width (px)', { exact: true })).toBeFocused();
    for (const value of ['', '-1', '1.5']) {
        await dialog.getByLabel('Width (px)', { exact: true }).fill(value);
        await dialog.getByRole('button', { name: 'Apply', exact: true }).click();
        await expect(dialog.getByText('Enter positive whole numbers for width and height.')).toBeVisible();
        expect(await page.evaluate(() => kikoHost.app.graph._nodes.at(-1).applied || 0)).toBe(0);
    }
    await dialog.getByLabel('Width (px)', { exact: true }).fill('1');
    await dialog.getByLabel('Height (px)', { exact: true }).fill('10');
    await page.keyboard.press('Enter');
    await expect(dialog).toHaveCount(0);
    expect(await page.evaluate(() => ({ size: kikoHost.app.graph._nodes.at(-1).size, applied: kikoHost.app.graph._nodes.at(-1).applied }))).toEqual({ size: [180, 120], applied: 1 });
    await expect(page.getByRole('button', { name: 'Edit dimensions', exact: true })).toBeFocused();
});

test('Node Dimensions follows themes, fits narrow screens and cleans up on removal', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'WidthHeightSelector');
    const dialog = await openDimensions(page);
    for (const [color, theme] of [['#fafafa', 'light'], ['#202020', 'dark']]) {
        await page.evaluate(color => document.body.style.setProperty('--bg-color', color), color);
        await expect(dialog).toHaveAttribute('data-ca-theme', theme);
    }
    await page.setViewportSize({ width: 320, height: 480 });
    expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
    await page.evaluate(() => window.KikoToolsExtensions.showNodeDimensionsDialog(kikoHost.app.graph._nodes.at(-1)));
    await expect(dialog).toHaveCount(1);
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await page.getByRole('button', { name: 'Edit dimensions', exact: true }).click();
    await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await page.getByRole('button', { name: 'Edit dimensions', exact: true }).click();
    await page.evaluate(() => kikoHost.app.graph._nodes.at(-1).onRemoved());
    await expect(dialog).toHaveCount(0);
    expect(await page.evaluate(() => kikoHost.app.graph._nodes.at(-1).applied || 0)).toBe(0);
});

test('legacy dialog helpers preserve values, cancellation and manual close', async ({ page }) => {
    await openHost(page);
    await page.evaluate(() => {
        window.dialogCalls = [];
        window.openLegacy = () => window.legacyDialog = window.KikoToolsExtensions.createDialog('<label>Legacy value<input value="before"></label>', (dialog, values) => window.dialogCalls.push([dialog.tagName, values]), () => window.dialogCalls.push('cancel'));
        window.openLegacy();
    });
    await page.getByLabel('Legacy value').fill('after');
    await page.keyboard.press('Enter');
    expect(await page.evaluate(() => window.dialogCalls)).toEqual([['DIALOG', ['after']]]);
    await page.evaluate(() => window.openLegacy());
    await page.keyboard.press('Escape');
    await page.evaluate(() => { window.openLegacy(); window.legacyDialog.close(); });
    expect(await page.evaluate(() => window.dialogCalls)).toEqual([['DIALOG', ['after']], 'cancel']);
    await page.evaluate(() => window.openLegacy());
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    expect(await page.evaluate(() => window.dialogCalls)).toEqual([['DIALOG', ['after']], 'cancel', 'cancel']);
});

test('dimension dialogs preserve node hooks and restrict menu ownership', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'WidthHeightSelector');
    const result = await page.evaluate(() => {
        const extension = kikoHost.extensions.find(item => item.name === 'ComfyAssets.Extensions');
        const missing = extension.getNodeMenuItems({ constructor: {} });
        const other = extension.getNodeMenuItems({ constructor: { category: 'Other' } });
        const node = kikoHost.app.graph._nodes.at(-1);
        const original = function (...args) { window.removedArgs = [this === node, ...args]; return 'removed'; };
        node.onRemoved = original;
        const dialog = window.KikoToolsExtensions.showNodeDimensionsDialog(node);
        window.detachedApply = dialog.querySelector('button[type="submit"]');
        const returned = node.onRemoved('a', 2);
        return { missing, other, returned, restored: node.onRemoved === original, args: window.removedArgs };
    });
    expect(result).toEqual({ missing: [], other: [], returned: 'removed', restored: true, args: [true, 'a', 2] });
    await page.evaluate(() => window.detachedApply.click());
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await page.evaluate(() => window.KikoToolsExtensions.createDialog('<label>Choice<select><option>chosen</option></select></label>'));
    await page.getByRole('button', { name: 'OK', exact: true }).click();
    await page.evaluate(() => window.KikoToolsExtensions.createDialog('No fields'));
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toHaveCount(0);
});


test('legacy selects retain Enter confirmation', async ({ page }) => {
    await openHost(page);
    await page.evaluate(() => window.KikoToolsExtensions.createDialog('<label for="legacy-choice">Choice</label><select id="legacy-choice"><option>chosen</option></select>', (dialog, values) => window.selectedLegacy = values));
    await page.evaluate(() => {
        window.leakedDialogKeys = 0;
        document.addEventListener('keydown', () => window.leakedDialogKeys++);
    });
    await page.getByLabel('Choice', { exact: true }).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect(await page.evaluate(() => window.selectedLegacy)).toEqual(['chosen']);
    expect(await page.evaluate(() => window.leakedDialogKeys)).toBe(0);
});


for (const name of ['DisplayText', 'DisplayAny']) {
    test(`${name}: shared output follows themes, resizes, copies and preserves empty output`, async ({ page }) => {
        await openHost(page);
        const id = await createNode(page, name, name === 'DisplayAny' ? { mode: 'tensor shape' } : {});
        await page.evaluate(id => {
            const node = kikoHost.nodes.get(String(id));
            node.onExecuted({ text: ['first\nsecond <b>literal</b>'] });
            window.copiedOutput = [];
            Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async text => window.copiedOutput.push(text) } });
        }, id);
        const panel = page.locator('.ca-text-output');
        await expect(panel).toBeVisible();
        for (const [color, theme] of [['#fafafa', 'light'], ['#202020', 'dark']]) {
            await page.evaluate(color => document.body.style.setProperty('--bg-color', color), color);
            await expect(panel).toHaveAttribute('data-ca-theme', theme);
        }
        const field = panel.getByRole('textbox');
        await expect(field).toHaveAttribute('readonly', '');
        await expect(field).toHaveValue('first\nsecond <b>literal</b>');
        await field.focus();
        await page.keyboard.press('ControlOrMeta+A');
        expect(await field.evaluate(element => element.value.substring(element.selectionStart, element.selectionEnd))).toBe('first\nsecond <b>literal</b>');
        await panel.getByRole('button', { name: /Copy/ }).focus();
        await page.keyboard.press('Enter');
        await expect(panel.getByRole('status')).toHaveText('Copied.');
        expect(await page.evaluate(() => window.copiedOutput)).toEqual(['first\nsecond <b>literal</b>']);
        for (const width of [240, 450, 800]) {
            await panel.evaluate((element, width) => { element.style.width = `${width}px`; element.style.height = '400px'; }, width);
            expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
        }
        await page.evaluate(id => kikoHost.nodes.get(String(id)).onExecuted({ text: [''] }), id);
        await expect(panel.getByRole('textbox')).toHaveValue('');
        await expect(panel.getByRole('status')).toBeEmpty();
        const snapshot = await page.evaluate(id => {
            const node = kikoHost.nodes.get(String(id));
            const data = {};
            node.onSerialize(data);
            node.onExecuted({ text: ['replacement'] });
            node.configure(data);
            return data;
        }, id);
        expect(snapshot.kikoDisplay).toEqual({ version: 1, text: '' });
        await expect(panel.getByRole('textbox')).toHaveValue('');
        await page.evaluate(id => kikoHost.removeNode(id), id);
        await expect(panel).toHaveCount(0);
    });
}

test('display prompt copy feedback handles failure, replacement and removal safely', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'DisplayText');
    await page.evaluate(id => {
        kikoHost.nodes.get(String(id)).onExecuted({ text: ['Positive prompt: sun\nNegative prompt: rain'] });
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: () => Promise.reject(new Error('denied')) } });
    }, id);
    const panel = page.locator('.ca-text-output');
    await panel.getByRole('button', { name: 'Copy negative', exact: true }).click();
    await expect(panel.getByRole('status')).toContainText('Could not copy');
    await expect(panel.getByRole('textbox', { name: 'Negative prompt', exact: true })).toHaveValue('rain');
    await page.evaluate(() => { navigator.clipboard.writeText = () => new Promise(resolve => window.finishCopy = resolve); });
    await panel.getByRole('button', { name: 'Copy positive', exact: true }).click();
    await page.evaluate(id => {
        kikoHost.nodes.get(String(id)).onExecuted({ text: ['new output'] });
        window.finishCopy();
    }, id);
    await expect(panel.getByRole('status')).toBeEmpty();
    await panel.getByRole('button', { name: 'Copy text', exact: true }).click();
    await page.evaluate(id => { kikoHost.removeNode(id); window.finishCopy(); }, id);
    await expect(panel).toHaveCount(0);
});

test('display adapters preserve lifecycle context, arguments, results and saved snapshots', async ({ page }) => {
    await openHost(page);
    const result = await page.evaluate(async () => {
        const calls = [];
        let node;
        class HookNode {
            constructor() { this.widgets = []; this.size = [600, 500]; this.inputs = []; }
            addDOMWidget(name, type, element) { document.body.append(element); const widget = { name, element }; this.widgets.push(widget); return widget; }
            setSize(size) { this.size = size; }
            setDirtyCanvas() {}
            onNodeCreated(...args) { calls.push(['created', this === node, args]); return 'created-result'; }
            onExecuted(...args) { calls.push(['executed', this === node, args]); return 'executed-result'; }
            configure(...args) { calls.push(['configure', this === node, args]); return 'configure-result'; }
            onSerialize(...args) { calls.push(['serialize', this === node, args.length]); args[0].external = 'retained'; return 'serialize-result'; }
            onRemoved(...args) { calls.push(['removed', this === node, args]); return 'removed-result'; }
        }
        await kikoHost.extensions.find(extension => extension.name === 'ComfyAssets.DisplayAny').beforeRegisterNodeDef(HookNode, { name: 'DisplayAny' }, kikoHost.app);
        node = new HookNode();
        const created = node.onNodeCreated('creation');
        const executed = node.onExecuted({ text: ['first'] }, 'execution');
        const data = {};
        const serialized = node.onSerialize(data, 'serialization');
        const configured = node.configure({ kikoDisplay: { version: 1, text: 'restored' } }, 'configuration');
        const removed = node.onRemoved('removal');
        node.onExecuted({ text: ['too late'] });
        return { created, executed, serialized, configured, removed, data, text: node.displayOutput.text, calls, disposed: node.displayOutput.scope.signal.aborted, size: node.size };
    });
    expect(result).toMatchObject({ created: 'created-result', executed: 'executed-result', serialized: 'serialize-result', configured: 'configure-result', removed: 'removed-result', data: { external: 'retained', kikoDisplay: { version: 1, text: 'first' } }, text: 'restored', disposed: true, size: [600, 500] });
    expect(result.calls.slice(0, 5)).toEqual([
        ['created', true, ['creation']],
        ['executed', true, [{ text: ['first'] }, 'execution']],
        ['serialize', true, 2],
        ['configure', true, [{ kikoDisplay: { version: 1, text: 'restored' } }, 'configuration']],
        ['removed', true, ['removal']],
    ]);
});

test('display copy feedback expires and malformed execution messages retain the latest output', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'DisplayText');
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        node.onExecuted({ text: ['latest'] });
        for (const message of [null, {}, { text: [] }, { text: [12] }]) node.onExecuted(message);
        Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => {} } });
    }, id);
    const panel = page.locator('.ca-text-output');
    await expect(panel.getByRole('textbox')).toHaveValue('latest');
    await panel.getByRole('button', { name: 'Copy text', exact: true }).click();
    await expect(panel.getByRole('status')).toHaveText('Copied.');
    await expect(panel.getByRole('status')).toBeEmpty({ timeout: 4000 });
});

async function mountAutocompleteSettings(page) {
    await page.evaluate(() => {
        const table = document.createElement('table');
        table.id = 'autocomplete-test-settings';
        const body = document.createElement('tbody');
        body.append(kikoHost.settingDefinitions.get('kikotools.embeddingAutocomplete').type());
        table.append(body);
        document.body.append(table);
    });
    await page.getByRole('button', { name: 'Open Settings', exact: true }).click();
    return page.getByRole('dialog', { name: 'Embedding Autocomplete Settings', exact: true });
}

test('autocomplete shared settings save preferences, cancel edits and follow themes', async ({ page }) => {
    await openHost(page);
    await page.evaluate(() => Object.assign(window.kikotools.autocomplete.settings, { quickTrigger: 'keep', maxSuggestions: 7, insertOnTab: false }));
    const dialog = await mountAutocompleteSettings(page);
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole('switch', { name: 'Enable Autocomplete', exact: true })).toBeChecked();
    await dialog.getByRole('switch', { name: 'Show LoRAs', exact: true }).uncheck();
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Open Settings', exact: true })).toBeFocused();
    expect(await page.evaluate(() => window.kikotools.autocomplete.settings.showLoras)).toBe(true);
    await page.getByRole('button', { name: 'Open Settings', exact: true }).click();
    await page.evaluate(() => document.querySelector('#autocomplete-test-settings button').click());
    await expect(dialog).toHaveCount(1);
    for (const [color, theme] of [['#fafafa', 'light'], ['#202020', 'dark']]) {
        await page.evaluate(color => document.body.style.setProperty('--bg-color', color), color);
        await expect(dialog).toHaveAttribute('data-ca-theme', theme);
    }
    await page.setViewportSize({ width: 320, height: 480 });
    expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
    await dialog.getByRole('switch', { name: 'Show LoRAs', exact: true }).uncheck();
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('kikotools.embedding_autocomplete.settings')))).toMatchObject({ showLoras: false, quickTrigger: 'keep', maxSuggestions: 7, insertOnTab: false });
    await page.getByRole('button', { name: 'Open Settings', exact: true }).click();
    await expect(dialog.getByRole('switch', { name: 'Show LoRAs', exact: true })).not.toBeChecked();
    await page.evaluate(() => document.getElementById('autocomplete-test-settings').remove());
    await expect(dialog).toHaveCount(0);
});

test('autocomplete settings report storage failure and keep the previous preferences', async ({ page }) => {
    await openHost(page);
    const dialog = await mountAutocompleteSettings(page);
    await dialog.getByRole('switch', { name: 'Enable Autocomplete', exact: true }).uncheck();
    await page.evaluate(() => { window.restoreAutocompleteStorage = Storage.prototype.setItem; Storage.prototype.setItem = () => { throw new Error('blocked'); }; });
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog.getByRole('status')).toContainText('Could not save');
    expect(await page.evaluate(() => window.kikotools.autocomplete.settings.enabled)).toBe(true);
    await page.evaluate(() => Storage.prototype.setItem = window.restoreAutocompleteStorage);
    await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(dialog).toHaveCount(0);
});

test('autocomplete suggestions retain focus, expose selection, and survive unrelated removal', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput', { text: '' });
    const other = await createNode(page, 'TextInput', { text: '' });
    await expect.poll(() => page.evaluate(() => window.kikotools.autocomplete.embeddings.length)).toBe(2);
    const prompt = page.getByLabel('text', { exact: true }).first();
    await prompt.fill('em');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    await expect(list.getByRole('option')).toHaveCount(2);
    await prompt.press('ArrowDown');
    const selected = list.getByRole('option', { selected: true });
    await expect(selected).toHaveCount(1);
    await expect(prompt).toHaveAttribute('aria-activedescendant', await selected.getAttribute('id'));
    await expect(prompt).toBeFocused();
    await page.evaluate(other => kikoHost.removeNode(other), other);
    await expect(list).toBeVisible();
    await prompt.press('Tab');
    await expect(prompt).toHaveValue(/embedding:/);
    await expect(list).toBeHidden();
    await expect(prompt).not.toHaveAttribute('aria-activedescendant');
    await prompt.fill('<lora:in');
    await expect(list).toBeVisible();
    await list.getByRole('option').click();
    await expect(prompt).toHaveValue('<lora:styles/ink:1.0>, ');
    await expect(prompt).toBeFocused();
});

test('autocomplete respects composition, read-only fields, custom words and keyboard preferences', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput', { text: '' });
    const prompt = page.getByLabel('text', { exact: true });
    await page.evaluate(() => {
        Object.assign(window.kikotools.autocomplete.settings, { showEmbeddings: false, showLoras: false, showCustomWords: true, insertOnEnter: false });
        window.kikotools.autocomplete.customWords = [{ name: 'blue_sky', value: 'blue_sky', display: 'blue_sky', type: 'custom' }];
    });
    await expect(prompt).toHaveAttribute('aria-autocomplete', 'list');
    await prompt.fill('blue');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    await expect(list).toBeVisible();
    await prompt.press('ArrowDown');
    await prompt.dispatchEvent('keydown', { key: 'Enter', isComposing: true });
    await expect(prompt).toHaveValue('blue');
    await prompt.press('Enter');
    await expect(prompt).not.toHaveValue('blue sky, ');
    await prompt.fill('blue');
    await prompt.press('ArrowDown');
    await prompt.press('Tab');
    await expect(prompt).toHaveValue('blue sky, ');
    await prompt.fill('blue');
    await prompt.press('Escape');
    await expect(list).toBeHidden();
    await prompt.evaluate(element => { element.readOnly = true; element.dispatchEvent(new Event('input', { bubbles: true })); });
    await expect(list).toBeHidden();
});

test('autocomplete restores existing attributes and lifecycle hooks on detach', async ({ page }) => {
    await openHost(page);
    const result = await page.evaluate(() => {
        const autocomplete = window.kikotools.autocomplete;
        const input = document.createElement('textarea');
        input.setAttribute('aria-controls', 'original-controls');
        input.setAttribute('aria-autocomplete', 'none');
        input.readOnly = true;
        const calls = [];
        const widget = { inputEl: input, onRemoved(...args) { calls.push([this === widget, args]); return 'widget-result'; } };
        const node = { onRemoved(...args) { calls.push([this === node, args]); return 'node-result'; } };
        const original = widget.onRemoved;
        autocomplete.attachToWidget(widget, node);
        const ignored = !autocomplete.activeWidgets.has(widget);
        input.readOnly = false;
        autocomplete.attachToWidget(widget, node);
        autocomplete.attachToWidget(widget, node);
        const value = widget.onRemoved('widget-arg', 7);
        const restored = widget.onRemoved === original;
        autocomplete.attachToWidget(widget, node);
        const removed = node.onRemoved('node-arg');
        autocomplete.detachFromWidget(widget);
        autocomplete.detachFromWidget(widget);
        return { ignored, value, removed, restored, calls, controls: input.getAttribute('aria-controls'), autocomplete: input.getAttribute('aria-autocomplete'), popup: input.hasAttribute('aria-haspopup'), active: autocomplete.activeWidgets.has(widget) };
    });
    expect(result).toEqual({ ignored: true, value: 'widget-result', removed: 'node-result', restored: true, calls: [[true, ['widget-arg', 7]], [true, ['node-arg']]], controls: 'original-controls', autocomplete: 'none', popup: false, active: false });
});

test('autocomplete popup fits narrow viewports and cleanup cancels pending refresh', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput', { text: '' });
    await expect.poll(() => page.evaluate(() => window.kikotools.autocomplete.embeddings.length)).toBe(2);
    await page.setViewportSize({ width: 320, height: 480 });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const prompt = page.getByLabel('text', { exact: true });
    await prompt.fill('em');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    const box = await list.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(320);
    expect(box.y + box.height).toBeLessThanOrEqual(480);
    await prompt.dispatchEvent('blur');
    await page.waitForTimeout(40);
    await expect(list).toBeVisible();
    await page.evaluate(() => {
        const autocomplete = window.kikotools.autocomplete;
        window.lateAutocompleteFetches = 0;
        autocomplete.fetchResources = () => window.lateAutocompleteFetches++;
        autocomplete.fetchResourcesDebounced();
        autocomplete.cleanup();
    });
    await expect(list).toHaveCount(0);
    await page.waitForTimeout(550);
    expect(await page.evaluate(() => window.lateAutocompleteFetches)).toBe(0);
    await expect(prompt).not.toHaveAttribute('aria-haspopup');
});

test('autocomplete binds replacement renderer fields without changing native widget ownership', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'TextInput', { text: '' });
    await expect.poll(() => page.evaluate(() => window.kikotools.autocomplete.embeddings.length)).toBe(2);
    await page.evaluate(id => {
        const wrapper = document.createElement('div');
        wrapper.setAttribute('node-id', String(id));
        const label = document.createElement('label');
        label.htmlFor = 'replacement-prompt';
        label.textContent = 'text';
        const textarea = document.createElement('textarea');
        textarea.id = 'replacement-prompt';
        wrapper.append(label, textarea);
        document.body.append(wrapper);
    }, id);
    const prompt = page.locator('#replacement-prompt');
    await prompt.fill('embedding:ca');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    await expect(list).toBeVisible();
    await prompt.press('ArrowDown');
    await prompt.press('Enter');
    await expect(prompt).toHaveValue('embedding:portraits/cat, ');
    await prompt.fill('embedding:ca');
    await expect(list).toBeVisible();
    await page.evaluate(() => {
        window.removedRendererBridge = window.kikotools.autocomplete.currentWidget;
        document.getElementById('replacement-prompt').parentElement.remove();
    });
    await expect(prompt).toHaveCount(0);
    await expect(list).toBeHidden();
    expect(await page.evaluate(() => window.kikotools.autocomplete.activeWidgets.has(window.removedRendererBridge))).toBe(false);
    const native = page.getByLabel('text', { exact: true });
    await native.fill('embedding:ca');
    await expect(list).toBeVisible();
    await native.press('ArrowDown');
    await native.press('Tab');
    await expect(native).toHaveValue('embedding:portraits/cat, ');
});

test('autocomplete starts a new query without carrying over the previous selection', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput', { text: '' });
    await expect.poll(() => page.evaluate(() => window.kikotools.autocomplete.embeddings.length)).toBe(2);
    const prompt = page.getByLabel('text', { exact: true });
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    await prompt.fill('embedding:ca');
    await prompt.press('ArrowDown');
    await prompt.press('ArrowDown');
    await expect(list.getByRole('option', { selected: true })).toContainText('forest');
    await prompt.fill('embedding:ca');
    await prompt.press('ArrowDown');
    await expect(list.getByRole('option', { selected: true })).toContainText('cat');
});

test('autocomplete keyboard selection ignores a stationary pointer over a new result list', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput', { text: '' });
    await expect.poll(() => page.evaluate(() => window.kikotools.autocomplete.embeddings.length)).toBe(2);
    const prompt = page.getByLabel('text', { exact: true });
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    await prompt.fill('embedding:ca');
    await list.getByRole('option').first().hover();
    await prompt.fill('embedding:ca');
    await page.waitForTimeout(50);
    await expect(list.getByRole('option', { selected: true })).toHaveCount(0);
    await prompt.press('ArrowDown');
    await prompt.press('Enter');
    await expect(prompt).toHaveValue('embedding:portraits/cat, ');
});

test('autocomplete delayed attachment cannot revive a removed node and teardown restores host hooks', async ({ page }) => {
    await openHost(page);
    await page.evaluate(async () => {
        const id = await kikoHost.createNode('TextInput', { text: '' });
        window.quicklyRemovedPrompt = kikoHost.nodes.get(String(id)).widgets.find(widget => widget.inputEl);
        kikoHost.removeNode(id);
    });
    await page.waitForTimeout(70);
    expect(await page.evaluate(() => window.kikotools.autocomplete.activeWidgets.has(window.quicklyRemovedPrompt))).toBe(false);
    expect(await page.evaluate(() => {
        const wrapped = kikoHost.app.graph.add;
        const stringWidget = kikoHost.widgets.STRING;
        window.kikotools.autocomplete.cleanup();
        return { graphRestored: kikoHost.app.graph.add !== wrapped, widgetRestored: kikoHost.widgets.STRING !== stringWidget };
    })).toEqual({ graphRestored: true, widgetRestored: true });
});

test('autocomplete tag import preserves aliases and ranking across reload and failed imports', async ({ page }) => {
    await openHost(page);
    const dialog = await mountAutocompleteSettings(page);
    await dialog.getByRole('switch', { name: 'Show Custom Words', exact: true }).check();
    await dialog.getByRole('switch', { name: 'Show Embeddings', exact: true }).uncheck();
    await dialog.getByRole('switch', { name: 'Show LoRAs', exact: true }).uncheck();
    await dialog.getByLabel('Tag list file', { exact: true }).setInputFiles({ name: 'tags.csv', mimeType: 'text/csv', buffer: Buffer.from('blue_sky,0,100,azure\nblue_eyes,0,900,"blue_eye,bright_eyes"') });
    await expect(dialog.getByRole('status')).toContainText('2 tags ready');
    await dialog.getByText('Triggers, matching and insertion', { exact: true }).click();
    await dialog.getByRole('switch', { name: 'Replace underscores with spaces', exact: true }).uncheck();
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await createNode(page, 'TextInput', { text: '' });
    const prompt = page.getByLabel('text', { exact: true });
    await expect(prompt).toHaveAttribute('aria-autocomplete', 'list');
    await prompt.focus();
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
    await prompt.fill('blue');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    await expect(list.getByRole('option').first()).toContainText('blue_eyes');
    await prompt.fill('azure');
    await prompt.press('ArrowDown');
    await prompt.press('Tab');
    await expect(prompt).toHaveValue('blue_sky, ');
    await page.reload();
    await expect.poll(() => page.evaluate(() => window.kikotools?.autocomplete.customWords.length)).toBe(2);
    const reopened = await mountAutocompleteSettings(page);
    await expect(reopened.getByText('2 tags loaded', { exact: true })).toBeVisible();
    await expect(reopened.getByText('Current source: tags.csv', { exact: true })).toBeVisible();
    await reopened.getByLabel('Tag list file', { exact: true }).setInputFiles({ name: 'bad.csv', mimeType: 'text/csv', buffer: Buffer.from('bad,0,not-a-count,') });
    await expect(reopened.getByRole('status')).toContainText('Could not load');
    await reopened.getByRole('button', { name: 'Cancel', exact: true }).click();
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords.length)).toBe(2);
});

test('autocomplete restores advanced preferences and stages URL tags until save', async ({ page }) => {
    await openHost(page);
    await page.route('**/__test__/tags.csv', route => route.fulfill({ body: 'tag,category,post_count,aliases\nblue_eyes,0,120,azure' }));
    const dialog = await mountAutocompleteSettings(page);
    await dialog.getByLabel('Tag list URL', { exact: true }).fill(new URL('/__test__/tags.csv', page.url()).href);
    await dialog.getByRole('button', { name: 'Load URL', exact: true }).click();
    await expect(dialog.getByRole('status')).toContainText('1 tags ready');
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords.length)).toBe(0);
    await dialog.getByText('Triggers, matching and insertion', { exact: true }).click();
    await dialog.getByLabel('Embedding trigger', { exact: true }).fill('emb:');
    await dialog.getByLabel('LoRA trigger', { exact: true }).fill('l:');
    await dialog.getByLabel('Quick embedding trigger', { exact: true }).fill('zz');
    await dialog.getByLabel('Maximum suggestions', { exact: true }).fill('8');
    await dialog.getByLabel('Minimum characters', { exact: true }).fill('3');
    await dialog.getByRole('switch', { name: 'Group by directory', exact: true }).uncheck();
    await dialog.getByRole('switch', { name: 'Insert on Enter', exact: true }).uncheck();
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    expect(await page.evaluate(() => ({ ...window.kikotools.autocomplete.settings }))).toMatchObject({ embeddingTrigger: 'emb:', loraTrigger: 'l:', quickTrigger: 'zz', maxSuggestions: 8, minChars: 3, sortByDirectory: false, insertOnEnter: false });
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords[0].frequency)).toBe(120);
});

test('autocomplete cancelling a staged import leaves the cached source unchanged', async ({ page }) => {
    await openHost(page);
    const dialog = await mountAutocompleteSettings(page);
    await dialog.getByLabel('Tag list file', { exact: true }).setInputFiles({ name: 'staged.csv', mimeType: 'text/csv', buffer: Buffer.from('blue_eyes,0,10,azure') });
    await expect(dialog.getByRole('status')).toContainText('1 tags ready');
    await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords)).toEqual([]);
    expect(await page.evaluate(async () => (await import('/extensions/kikotools/autocomplete/tag-storage.js')).tagCache())).toBeUndefined();
});

test('autocomplete reports tag download and cache errors without losing the current settings', async ({ page }) => {
    await openHost(page);
    const dialog = await mountAutocompleteSettings(page);
    await dialog.getByRole('button', { name: 'Load URL', exact: true }).click();
    await expect(dialog.getByRole('status')).toContainText('Enter a valid');
    await page.route('**/__test__/bad-tags.csv', route => route.fulfill({ status: 404, body: 'Missing' }));
    await dialog.getByLabel('Tag list URL', { exact: true }).fill(new URL('/__test__/bad-tags.csv', page.url()).href);
    await dialog.getByRole('button', { name: 'Load URL', exact: true }).click();
    await expect(dialog.getByRole('status')).toContainText('404');
    await dialog.getByLabel('Tag list file', { exact: true }).setInputFiles({ name: 'valid.csv', mimeType: 'text/csv', buffer: Buffer.from('blue_eyes,0,10,azure') });
    await expect(dialog.getByRole('status')).toContainText('1 tags ready');
    await dialog.getByRole('switch', { name: 'Enable Autocomplete', exact: true }).uncheck();
    await page.evaluate(() => {
        window.originalTagDBOpen = indexedDB.open.bind(indexedDB);
        indexedDB.open = () => { throw new DOMException('Storage denied', 'SecurityError'); };
    });
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog.getByRole('status')).toContainText('Could not save tag list');
    expect(await page.evaluate(() => window.kikotools.autocomplete.settings.enabled)).toBe(true);
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords.length)).toBe(0);
    expect(await page.evaluate(() => window.kikotools.autocomplete.settings.tagSource)).toBeUndefined();
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('kikotools.embedding_autocomplete.settings')).tagSource)).toBeUndefined();
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('kikotools.embedding_autocomplete.settings')).enabled)).toBe(true);
    await page.evaluate(() => indexedDB.open = window.originalTagDBOpen);
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords.length)).toBe(1);
});

test('autocomplete cancels pending tag downloads when its settings close', async ({ page }) => {
    await openHost(page);
    let held;
    await page.route('**/__test__/slow-tags.csv', route => { held = route; });
    const dialog = await mountAutocompleteSettings(page);
    await dialog.getByLabel('Tag list URL', { exact: true }).fill(new URL('/__test__/slow-tags.csv', page.url()).href);
    await dialog.getByRole('button', { name: 'Load URL', exact: true }).click();
    await expect.poll(() => Boolean(held)).toBe(true);
    await expect(dialog.getByRole('button', { name: 'Save Settings', exact: true })).toBeDisabled();
    await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
    await held.fulfill({ body: 'blue_eyes,0,10,azure' });
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords.length)).toBe(0);
    expect(await page.evaluate(() => window.kikotools.autocomplete.pendingFetches.size)).toBe(0);
});

test('autocomplete imports 300000 tags off the UI thread and bounds broad matches', async ({ page }) => {
    await openHost(page);
    const dialog = await mountAutocompleteSettings(page);
    const text = Array.from({ length: 300000 }, (_, i) => `tag_${i},0,${i},alias_${i}`).join('\n');
    await page.evaluate(() => { window.tagImportTicks = 0; window.tagImportTimer = setInterval(() => window.tagImportTicks++, 10); });
    await dialog.getByLabel('Tag list file', { exact: true }).setInputFiles({ name: 'large.csv', mimeType: 'text/csv', buffer: Buffer.from(text) });
    await expect(dialog.getByRole('status')).toContainText('300,000 tags ready', { timeout: 15000 });
    expect(await page.evaluate(() => { clearInterval(window.tagImportTimer); return window.tagImportTicks; })).toBeGreaterThan(1);
    await dialog.getByRole('switch', { name: 'Show Custom Words', exact: true }).check();
    await dialog.getByRole('button', { name: 'Save Settings', exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await createNode(page, 'TextInput', { text: '' });
    const prompt = page.getByLabel('text', { exact: true });
    await expect(prompt).toHaveAttribute('aria-autocomplete', 'list');
    await prompt.fill('alias_299999');
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    await expect(list.getByRole('option')).toHaveCount(1);
    await expect(list.getByRole('option')).toContainText('tag_299999');
    await prompt.fill('tag_');
    await expect(list.getByRole('option')).toHaveCount(20);
});

test('autocomplete legacy URL loads retain the newest valid list when older requests finish late', async ({ page }) => {
    await openHost(page);
    let held;
    await page.route('**/__test__/old-tags.txt', route => { held = route; });
    await page.route('**/__test__/new-tags.txt', route => route.fulfill({ body: 'blue_sky,10\nblue_eyes,200' }));
    await page.evaluate(() => { window.oldTagLoad = window.kikotools.autocomplete.loadCustomWords('/__test__/old-tags.txt'); });
    await expect.poll(() => Boolean(held)).toBe(true);
    expect(await page.evaluate(() => window.kikotools.autocomplete.loadCustomWords('/__test__/new-tags.txt'))).toBe(2);
    await held.fulfill({ body: 'obsolete,1000' });
    expect(await page.evaluate(() => window.oldTagLoad)).toBe(0);
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords.map(tag => tag.name))).toEqual(['blue_eyes', 'blue_sky']);
    expect(await page.evaluate(() => window.kikotools.autocomplete.loadCustomWords('file:///tmp/tags.csv'))).toBe(0);
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWords.length)).toBe(2);
    expect(await page.evaluate(() => window.kikotools.autocomplete.customWordsError)).toContain('HTTP or HTTPS');
});

test('autocomplete shares one removable node hook across widgets in any cleanup order', async ({ page }) => {
    await openHost(page);
    const result = await page.evaluate(() => {
        const autocomplete = window.kikotools.autocomplete;
        const restored = [];
        const calls = [];
        const make = () => {
            const original = function (...args) { calls.push([this === node, args]); return 'original-result'; };
            const node = { onRemoved: original };
            const widgets = [0, 1, 2].map(() => ({ inputEl: document.createElement('textarea') }));
            widgets.forEach(widget => autocomplete.attachToWidget(widget, node));
            return { node, original, widgets };
        };
        for (const order of [[0, 1, 2], [2, 0, 1]]) {
            const { node, original, widgets } = make();
            const hook = node.onRemoved;
            autocomplete.detachFromWidget(widgets[order[0]]);
            restored.push(node.onRemoved === hook);
            autocomplete.detachFromWidget(widgets[order[1]]);
            autocomplete.detachFromWidget(widgets[order[2]]);
            restored.push(node.onRemoved === original);
        }
        const active = make();
        const removal = active.node.onRemoved('removed', 7);
        restored.push(active.node.onRemoved === active.original, active.widgets.every(widget => !autocomplete.activeWidgets.has(widget)));
        const final = make();
        autocomplete.cleanup();
        restored.push(final.node.onRemoved === final.original);
        return { restored, removal, calls };
    });
    expect(result).toEqual({ restored: Array(7).fill(true), removal: 'original-result', calls: [[true, ['removed', 7]]] });
});

test('autocomplete inserts Unicode and punctuation aliases at the correct prompt boundary', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput', { text: '' });
    const prompt = page.getByLabel('text', { exact: true });
    await expect(prompt).toHaveAttribute('aria-autocomplete', 'list');
    await page.evaluate(async () => {
        const autocomplete = window.kikotools.autocomplete;
        const { parseTagList } = await import('/extensions/kikotools/autocomplete/tags.js');
        autocomplete.customWords = parseTagList('日本語,0,10,にほんご\nheart,0,20,<3\nhatsune_miku_(vocaloid),4,100,miku/vocaloid\n🎨🎨,0,1,\n(o_o),0,1,');
        Object.assign(autocomplete.settings, { showCustomWords: true, showEmbeddings: false, showLoras: false, replaceUnderscores: false });
    });
    const list = page.getByRole('listbox', { name: 'Prompt completions', exact: true });
    for (const [query, label, value] of [
        ['日本', '日本語', '日本語, '],
        ['にほん', '日本語', '日本語, '],
        ['sky, <3', 'heart', 'sky, heart, '],
        ['miku/vocal', 'hatsune_miku_(vocaloid)', 'hatsune_miku_(vocaloid), '],
        ['sky, (日本:1.2)', '日本語', 'sky, (日本語:1.2)'],
        ['🎨🎨', '🎨🎨', '🎨🎨, '],
        ['(o_o)', '(o_o)', '(o_o), '],
    ]) {
        await prompt.fill(query);
        if (query.includes(':1.2')) await prompt.evaluate(element => { element.setSelectionRange(element.value.indexOf(':1.2'), element.value.indexOf(':1.2')); element.dispatchEvent(new Event('input', { bubbles: true })); });
        await expect(list.getByRole('option').first()).toContainText(label);
        await prompt.press('ArrowDown');
        await prompt.press('Tab');
        await expect(prompt).toHaveValue(value);
    }
});

test('autocomplete stops an oversized URL stream before it reaches the parser', async ({ page }) => {
    await openHost(page);
    const result = await page.evaluate(async () => {
        const autocomplete = window.kikotools.autocomplete;
        let cancelled = false, sent = false;
        const original = autocomplete.fetchWithAbort;
        autocomplete.fetchWithAbort = async () => new Response(new ReadableStream({
            pull(controller) { if (!sent) { sent = true; controller.enqueue(new Uint8Array(32 * 1024 * 1024 + 1).fill(97)); } else controller.close(); },
            cancel() { cancelled = true; },
        }, { highWaterMark: 0 }));
        let error;
        try { await autocomplete.fetchTagList('/__test__/oversized-tags.csv'); }
        catch (failure) { error = failure.message; }
        finally { autocomplete.fetchWithAbort = original; }
        return { cancelled, error };
    });
    expect(result.cancelled).toBe(true);
    expect(result.error).toMatch(/large/i);
});

async function openCustomColor(page, kind = 'Full') {
    await page.evaluate(kind => {
        const extension = kikoHost.extensions.find(item => item.name === 'kikotools.customColors');
        const node = kikoHost.app.graph._nodes[0];
        extension.getNodeMenuItems(node)[1].submenu.options.find(item => item.content === `🫶 Custom ${kind}`).callback();
    }, kind);
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.locator('ca-color-picker')).toHaveCSS('display', 'none');
}

test('custom colors share the themed picker and preserve full, title, background and selection behavior', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput');
    await createNode(page, 'TextInput');
    await page.evaluate(() => {
        const [first, second] = kikoHost.app.graph._nodes;
        first.bgcolor = '#123456';
        first.setColorOption = function (value) { Object.assign(this, value); };
        kikoHost.app.canvas.selected_nodes = { [first.id]: first, [second.id]: second };
        window.LGraphCanvas = { active_canvas: kikoHost.app.canvas };
    });
    await openCustomColor(page);
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByLabel('Hex color', { exact: true })).toHaveValue('#123456');
    for (const [color, theme] of [['#fff', 'light'], ['#202020', 'dark']]) {
        await page.evaluate(color => document.body.style.setProperty('--bg-color', color), color);
        await expect(dialog).toHaveAttribute('data-ca-theme', theme);
    }
    await dialog.getByLabel('Hex color', { exact: true }).fill('#112233');
    await dialog.getByLabel('Hex color', { exact: true }).press('Tab');
    expect(await page.evaluate(() => kikoHost.app.graph._nodes.map(({ color, bgcolor }) => ({ color, bgcolor })))).toEqual([
        { color: '#253647', bgcolor: '#112233' }, { color: '#253647', bgcolor: '#112233' },
    ]);
    await dialog.getByRole('button', { name: 'Done', exact: true }).click();
    await expect(page.locator('ca-color-picker')).toHaveCount(0);
    await page.evaluate(() => { kikoHost.app.canvas.selected_nodes = {}; });
    for (const kind of ['Title', 'BG']) {
        await openCustomColor(page, kind);
        await dialog.getByRole('button', { name: 'Use color #0877BB', exact: true }).click();
        await page.keyboard.press('Escape');
        await expect(page.locator('ca-color-picker')).toHaveCount(0);
    }
    expect(await page.evaluate(() => kikoHost.app.graph._nodes.map(({ color, bgcolor }) => ({ color, bgcolor })))).toEqual([
        { color: '#0877bb', bgcolor: '#0877bb' }, { color: '#253647', bgcolor: '#112233' },
    ]);
});

test('custom colors replace open pickers, preserve removal hooks and release detached dialogs', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'TextInput');
    await openCustomColor(page);
    await openCustomColor(page, 'Title');
    await expect(page.locator('dialog')).toHaveCount(1);
    expect(await page.evaluate(id => kikoHost.removeNode(id).removed, id)).toBe(true);
    await expect(page.locator('dialog')).toHaveCount(0);
    await expect(page.locator('ca-color-picker')).toHaveCount(0);
});

test('custom colors retain group application and menu setting filters', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput');
    await page.evaluate(() => {
        window.testGroup = { color: '#abc', setColorOption(value) { this.color = value.groupcolor; } };
        kikoHost.app.canvas.setDirty = () => { window.groupDirtied = true; };
        kikoHost.app.canvas.graph_mouse = [5, 10];
        kikoHost.app.canvas.graph = { getGroupOnPos: (x, y) => x === 5 && y === 10 ? testGroup : null };
        const extension = kikoHost.extensions.find(item => item.name === 'kikotools.customColors');
        extension.getCanvasMenuItems(kikoHost.app.canvas)[1].submenu.options[0].callback();
    });
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByLabel('Hex color', { exact: true })).toHaveValue('#AABBCC');
    await dialog.getByRole('button', { name: 'Use color #0877BB', exact: true }).click();
    expect(await page.evaluate(() => [testGroup.color, groupDirtied])).toEqual(['#0877bb', true]);
    await dialog.getByRole('button', { name: 'Done', exact: true }).click();
    expect(await page.evaluate(() => {
        const extension = kikoHost.extensions.find(item => item.name === 'kikotools.customColors');
        const node = kikoHost.app.graph._nodes[0];
        for (const key of ['show_full', 'show_title', 'show_bg']) kikoHost.settings.set(`kikotools.custom_colors.${key}`, false);
        const empty = [extension.getNodeMenuItems(node), extension.getCanvasMenuItems(kikoHost.app.canvas)];
        kikoHost.settings.set('kikotools.custom_colors.enabled', false);
        return [...empty, extension.getNodeMenuItems(node), extension.getCanvasMenuItems(kikoHost.app.canvas)];
    })).toEqual([[], [], [], []]);
});

test('custom colors keep unshaded fallback colors and restore keyboard focus', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput');
    await page.evaluate(() => {
        kikoHost.settings.set('kikotools.custom_colors.auto_shade', false);
        const opener = document.createElement('button');
        opener.textContent = 'Open custom colors';
        opener.onclick = () => {
            const extension = kikoHost.extensions.find(item => item.name === 'kikotools.customColors');
            extension.getNodeMenuItems(kikoHost.app.graph._nodes[0])[1].submenu.options[0].callback();
        };
        document.body.append(opener);
    });
    const opener = page.getByRole('button', { name: 'Open custom colors', exact: true });
    await opener.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Use color #0877BB', exact: true }).click();
    expect(await page.evaluate(() => {
        const node = kikoHost.app.graph._nodes[0];
        return [node.color, node.bgcolor];
    })).toEqual(['#0877bb', '#0877bb']);
    await page.keyboard.press('Escape');
    await expect(opener).toBeFocused();
    await expect(page.locator('ca-color-picker')).toHaveCount(0);
    await opener.click();
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Done', exact: true }).click();
    await expect(opener).toBeFocused();
});

test('custom colors handle absent settings, empty canvas menus, legacy groups and detached openers', async ({ page }) => {
    await openHost(page);
    await createNode(page, 'TextInput');
    expect(await page.evaluate(() => {
        const extension = kikoHost.extensions.find(item => item.name === 'kikotools.customColors');
        kikoHost.settings.delete('kikotools.custom_colors.enabled');
        return [extension.getCanvasMenuItems({}), extension.getCanvasMenuItems({ graph_mouse: [0, 0], graph: { getGroupOnPos: () => null } }), extension.getNodeMenuItems(kikoHost.app.graph._nodes[0])[1].submenu.options.length];
    })).toEqual([[], [], 3]);
    await page.evaluate(() => {
        const extension = kikoHost.extensions.find(item => item.name === 'kikotools.customColors');
        window.testGroup = { color: '#000000' };
        kikoHost.app.canvas.setDirty = () => {};
        const focusTarget = document.createElement('button');
        focusTarget.textContent = 'Canvas focus target';
        kikoHost.app.canvas.canvas = focusTarget;
        const temporaryOpener = document.createElement('button');
        document.body.append(temporaryOpener, focusTarget);
        temporaryOpener.focus();
        extension.getCanvasMenuItems({ graph_mouse: [0, 0], graph: { getGroupOnPos: () => testGroup } })[1].submenu.options[0].callback();
        temporaryOpener.remove();
    });
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Use color #FFFFFF', exact: true }).click();
    expect(await page.evaluate(() => testGroup.color)).toBe('#ffffff');
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button', { name: 'Canvas focus target', exact: true })).toBeFocused();
    await page.evaluate(() => {
        delete kikoHost.app.canvas.selected_nodes;
        const extension = kikoHost.extensions.find(item => item.name === 'kikotools.customColors');
        class BareNode {}
        extension.beforeRegisterNodeDef(BareNode);
        new BareNode().onRemoved();
    });
    await openCustomColor(page);
    await dialog.getByRole('button', { name: 'Use color #000000', exact: true }).click();
    expect(await page.evaluate(() => kikoHost.app.graph._nodes[0].color)).toBe('#141414');
    await dialog.getByRole('button', { name: 'Use color #FFFFFF', exact: true }).click();
    expect(await page.evaluate(() => kikoHost.app.graph._nodes[0].color)).toBe('#ffffff');
    await page.keyboard.press('Escape');
});

test('Follow Execution honors live settings, manual controls and repeated setup', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'TextInput');
    expect(await page.evaluate(async id => {
        const { app, extensions } = kikoHost;
        const extension = extensions.find(item => item.name === 'kikotools.followExecution');
        const node = app.graph._nodes[0];
        node.getTitle = () => node.title;
        const centered = [];
        app.canvas.centerOnNode = node => centered.push(node.id);
        app.runningNodeId = id;
        const set = (name, value) => app.ui.settings.setSettingValue(`kikotools.follow_execution.${name}`, value);
        set('enabled', true);
        extension.getCanvasMenuItems()[1].callback();
        kikoHost.emit('executing', id);
        const afterManual = centered.length;
        set('enabled', false);
        kikoHost.emit('executing', id);
        const afterDisable = centered.length;
        set('enabled', true);
        kikoHost.emit('executing', id);
        const afterEnable = centered.length;
        set('auto_start', true);
        for (let i = 0; i < 3; i++) await extension.setup();
        kikoHost.emit('execution_start');
        kikoHost.emit('executing', id);
        const afterRepeatedSetup = centered.length;
        extension.getCanvasMenuItems()[1].callback();
        kikoHost.emit('executing', id);
        const afterStop = centered.length;
        extension.getCanvasMenuItems().find(item => item?.content === '🫶 Show executing node').callback();
        const afterShow = centered.length;
        kikoHost.emit('executing', 'missing');
        kikoHost.emit('executing', null);
        return { afterManual, afterDisable, afterEnable, afterRepeatedSetup, afterStop, afterShow, final: centered.length };
    }, id)).toEqual({ afterManual: 2, afterDisable: 2, afterEnable: 2, afterRepeatedSetup: 3, afterStop: 3, afterShow: 4, final: 4 });
});

test('Follow Execution retains safe sorted navigation menus and setting filters', async ({ page }) => {
    await openHost(page);
    for (let i = 0; i < 4; i++) await createNode(page, 'TextInput');
    expect(await page.evaluate(() => {
        const { app, extensions } = kikoHost;
        const extension = extensions.find(item => item.name === 'kikotools.followExecution');
        app.ui.settings.setSettingValue('kikotools.follow_execution.enabled', true);
        ['constructor', '__proto__', 'toString', 'constructor'].forEach((type, index) => {
            const node = app.graph._nodes[index];
            Object.assign(node, { type, pos: [40 - index * 10, 0], getTitle: () => type });
        });
        const menu = extension.getCanvasMenuItems().find(item => item?.content === '🫶 Go to node');
        const types = menu.submenu.options.map(item => item.content);
        const constructors = menu.submenu.options[1].submenu.options;
        constructors[0].callback();
        const centered = app.centeredNode;
        app.ui.settings.setSettingValue('kikotools.follow_execution.show_goto_node', false);
        const hiddenGoTo = !extension.getCanvasMenuItems().some(item => item?.content === '🫶 Go to node');
        app.ui.settings.setSettingValue('kikotools.follow_execution.enabled', false);
        return { types, centered, hiddenGoTo, disabled: extension.getCanvasMenuItems() };
    })).toEqual({ types: ['__proto__', 'constructor', 'toString'], centered: 4, hiddenGoTo: true, disabled: [] });
});

test('resolution picker renders chips from the families route and writes sizes to native widgets', async ({ page, request }) => {
    await openHost(page);
    const payload = await (await request.get('/kikotools/model_resolution/families')).json();
    expect(payload.default).toBe('SDXL');
    await createNode(page, 'ModelResolutionPicker', { model: 'SDXL', width: 1024, height: 1024, batch_size: 1 });
    const panel = page.locator('.ca-resolution-picker');
    await expect(panel.getByRole('button', { name: '1:1', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(panel.locator('.ca-resolution-header')).toHaveText('1024 × 1024 · 1:1 · 1.0 MP');
    await panel.getByRole('button', { name: '3:2', exact: true }).click();
    const node = page.locator('[data-node="ModelResolutionPicker"]');
    await expect(node.getByLabel('width', { exact: true })).toHaveValue('1216');
    await expect(node.getByLabel('height', { exact: true })).toHaveValue('832');
    await expect(panel.getByRole('button', { name: '1216 × 832', exact: true })).toHaveAttribute('aria-pressed', 'true');
    await expect(panel.getByRole('button', { name: '21:9', exact: true })).toBeEnabled();
    for (const theme of ['light', 'dark']) {
        await page.evaluate(theme => document.body.style.setProperty('--bg-color', theme === 'light' ? '#fff' : '#202020'), theme);
        await expect(panel).toHaveAttribute('data-ca-theme', theme);
    }
    expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
});

test('resolution picker mounting is idempotent and removal disposes its scope', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'ModelResolutionPicker', { model: 'SDXL', width: 1024, height: 1024, batch_size: 1 });
    await page.evaluate(id => { const node = kikoHost.nodes.get(String(id)); node.createSwapButton(); node.createSwapButton(); }, id);
    await expect(page.locator('.ca-resolution-picker')).toHaveCount(1);
    await expect(page.locator('.ca-dimension-swap')).toHaveCount(1);
    const aborted = await page.evaluate(id => { const node = kikoHost.nodes.get(String(id)); kikoHost.removeNode(id); return node.resolutionScope.signal.aborted; }, id);
    expect(aborted).toBe(true);
    await expect(page.locator('.ca-resolution-picker')).toHaveCount(0);
});
