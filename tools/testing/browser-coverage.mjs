import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
const repositoryRoot = fileURLToPath(new URL('../../', import.meta.url));

export async function startCoverage(page, browserName) {
    if (process.env.KIKO_JS_COVERAGE && browserName === 'chromium') {
        await page.coverage.startJSCoverage({ resetOnNavigation: false });
    }
}
export async function saveCoverage(page, browserName) {
    if (!process.env.KIKO_JS_COVERAGE || browserName !== 'chromium') return;
    const entries = await page.coverage.stopJSCoverage();
    const result = [];
    for (const entry of entries) {
        const match = entry.url.match(/\/extensions\/kikotools\/([a-z0-9_-]+\.js)(?:\?.*)?$/i);
        if (match) result.push({ ...entry, url: pathToFileURL(join(repositoryRoot, 'web', match[1])).href });
    }
    mkdirSync(process.env.KIKO_JS_COVERAGE, { recursive: true });
    writeFileSync(join(process.env.KIKO_JS_COVERAGE, `browser-${randomUUID()}.json`), JSON.stringify({ result }));
}
