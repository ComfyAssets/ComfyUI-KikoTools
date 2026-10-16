import { test, expect } from '../../../tools/testing/node_modules/@playwright/test/index.mjs';

test.beforeEach(async ({ page }) => {
    await page.goto('/');
});

test('theme preview updates native color scheme and both product samples together', async ({ page }) => {
    await page.getByRole('radio', { name: 'Light', exact: true }).check();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
    await expect(page.locator('html')).toHaveCSS('color-scheme', 'light');
    const samples = page.locator('[data-product-sample]');
    expect(await samples.count()).toBe(2);
    const backgrounds = await samples.evaluateAll(elements => elements.map(el => getComputedStyle(el).backgroundColor));
    expect(new Set(backgrounds).size).toBe(1);
    await page.getByRole('radio', { name: 'Dark', exact: true }).check();
    await expect(page.locator('html')).toHaveCSS('color-scheme', 'dark');
});

test('gallery selection, filtering and layout controls operate on sample content', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Select alpine-lake.png' })).toBeVisible();
    await page.getByRole('button', { name: 'Select alpine-lake.png' }).click();
    await expect(page.getByRole('button', { name: 'Select alpine-lake.png' })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[data-selection]')).toContainText('alpine-lake.png');
    await page.getByRole('radio', { name: 'List', exact: true }).check();
    await expect(page.locator('[data-gallery]')).toHaveAttribute('data-view', 'list');
    await page.getByLabel('Filter sample files').fill('dune');
    await expect(page.locator('[data-gallery] button')).toHaveCount(1);
    await page.getByLabel('Filter sample files').fill('missing');
    await expect(page.getByText('No matching sample files.')).toBeVisible();
});

test('prompt rows support editing, disabling, removing and reset', async ({ page }) => {
    await page.getByRole('button', { name: '+ Add row', exact: true }).click();
    await page.getByLabel('Prompt row 2', { exact: true }).fill('A quiet lake at dawn');
    await page.getByRole('switch', { name: 'Row 2', exact: true }).uncheck();
    await expect(page.getByLabel('Prompt row 2', { exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Remove row 1', exact: true }).click();
    await expect(page.getByLabel('Prompt row 1', { exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: 'Reset', exact: true }).click();
    await expect(page.getByLabel('Prompt row 1', { exact: true })).toBeEnabled();
    await expect(page.getByLabel('Prompt row 1', { exact: true })).toHaveValue('');
    await expect(page.getByRole('button', { name: 'Reset', exact: true })).toBeDisabled();
});

test('switches support keyboard and error example has an actionable recovery', async ({ page }) => {
    const toggle = page.getByRole('switch', { name: 'Hide dot folders' });
    await toggle.focus();
    await page.keyboard.press('Space');
    await expect(toggle).not.toBeChecked();
    await expect(toggle).toBeFocused();
    await expect(toggle).toHaveCSS('outline-style', 'solid');
    await page.getByRole('button', { name: 'Show error example' }).click();
    await expect(page.getByRole('alert')).toContainText('Folder unavailable');
    await page.getByRole('button', { name: 'Retry' }).click();
    await expect(page.getByRole('alert')).not.toBeVisible();
});

test('node controls resize without horizontal overflow and range supports keyboard', async ({ page }) => {
    for (const width of [320, 460, 800]) {
        await page.getByLabel('Preview node width').fill(String(width));
        await page.getByLabel('Preview node width').dispatchEvent('input');
        expect((await page.locator('[data-loader]').boundingBox()).width).toBeLessThanOrEqual(width);
        const overflow = await page.locator('[data-loader]').evaluate(el => el.scrollWidth - el.clientWidth);
        expect(overflow).toBeLessThanOrEqual(1);
    }
    await page.setViewportSize({ width: 375, height: 850 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1);
    await page.screenshot({ path: test.info().outputPath('narrow.png'), fullPage: true });
    const size = page.getByLabel('Thumbnail size');
    await size.focus();
    await page.keyboard.press('ArrowRight');
    await expect(size).toHaveValue('152');
});

test('text, accent and error treatments have measurable contrast in both themes', async ({ page }) => {
    const luminance = color => {
        const channels = color.match(/[\d.]+/g).slice(0, 3).map(Number).map(value => {
            const channel = value / 255;
            return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
        });
        return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    };
    for (const theme of ['Light', 'Dark']) {
        await page.getByRole('radio', { name: theme, exact: true }).check();
        for (const selector of ['.ca-node', '.ca-primary', '.ca-danger', '.ca-muted-sample']) {
            const colors = await page.locator(selector).first().evaluate(el => {
                const style = getComputedStyle(el);
                return [style.color, style.backgroundColor];
            });
            const [a, b] = colors.map(luminance).sort((x, y) => y - x);
            expect((a + 0.05) / (b + 0.05), `${theme} ${selector}`).toBeGreaterThanOrEqual(4.5);
        }
        await page.screenshot({ path: test.info().outputPath(`${theme.toLowerCase()}.png`), fullPage: true });
    }
});
