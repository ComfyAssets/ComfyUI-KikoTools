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
    await page.addInitScript(() => localStorage.setItem('kikotools.embedding_autocomplete.settings', JSON.stringify({ showCustomWords: false, customWordsUrl: '' })));
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

test('actual swap handlers preserve preset values and custom dimensions', async ({ page }) => {
    await openHost(page);
    const id = await createNode(page, 'WidthHeightSelector', { preset: '832×1216 - portrait', width: 832, height: 1216 });
    const swapped = await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        node.onMouseDown({ canvasX: 475, canvasY: 140 });
        return node.widgets.map(widget => widget.value);
    }, id);
    expect(swapped).toEqual(['1216×832 - landscape', '1216', '832']);
    await createNode(page, 'EmptyLatentBatch', { preset: 'custom', width: 640, height: 960 });
    await page.getByRole('button', { name: /Swap W/ }).click();
    const latent = page.locator('[data-node="EmptyLatentBatch"]');
    await expect(latent.getByLabel('width')).toHaveValue('960');
    await expect(latent.getByLabel('height')).toHaveValue('640');
});

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
    await expect(page.getByLabel('text_positive')).toHaveValue('<img src=x onerror="window.injected=true">');
    await expect(page.getByLabel('text_negative')).toHaveValue('blur');
    expect(await page.evaluate(() => window.injected)).toBeUndefined();
    const next = await (await request.post('/__test__/execute/DisplayText', { data: { text: 'Replacement' } })).json();
    await page.evaluate(({ id, message }) => kikoHost.nodes.get(String(id)).onExecuted(message), { id, message: next.ui });
    await expect(page.locator('textarea')).toHaveCount(1);
    await expect(page.getByLabel('text_display')).toHaveValue('Replacement');
    await expect(page.getByLabel('text_display')).toHaveAttribute('readonly', '');
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

test('Display Any renders real multiline output and restores serialized values without duplicate widgets', async ({ page, request }) => {
    await openHost(page);
    const id = await createNode(page, 'DisplayAny');
    const response = await request.post('/__test__/execute/DisplayAny', { data: { input: Array.from({ length: 45 }, (_, index) => `Line ${index}`).join('\n') } });
    await expect(response).toBeOK();
    const result = await response.json();
    await page.evaluate(({ id, message }) => kikoHost.nodes.get(String(id)).onExecuted(message), { id, message: result.ui });
    await expect(page.locator('textarea')).toHaveCount(3);
    expect(await page.locator('textarea').evaluateAll(elements => elements.map(element => element.value).join('\n'))).toBe(result.ui.text[0]);
    await page.evaluate(id => {
        const node = kikoHost.nodes.get(String(id));
        node.configure({ widgets_values: ['Restored value'] });
        node.onConfigure();
    }, id);
    await expect(page.locator('textarea')).toHaveCount(1);
    await expect(page.getByLabel('display_0')).toHaveValue('Restored value');
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
