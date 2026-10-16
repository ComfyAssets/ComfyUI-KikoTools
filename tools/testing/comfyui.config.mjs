import { defineConfig } from './node_modules/@playwright/test/index.mjs';
import { fileURLToPath } from 'node:url';

if (!process.env.KIKO_COMFY_URL) throw new Error('Set KIKO_COMFY_URL to a local ComfyUI instance');
const host = new URL(process.env.KIKO_COMFY_URL);
if (!['127.0.0.1', 'localhost', '[::1]'].includes(host.hostname)) throw new Error('The ComfyUI smoke suite only accepts a loopback host');

export default defineConfig({
    testDir: '../../tests/comfyui',
    outputDir: './test-results/comfyui',
    timeout: 60000,
    workers: 1,
    forbidOnly: Boolean(process.env.CI),
    retries: 0,
    use: { baseURL: host.href, browserName: 'chromium', viewport: { width: 1600, height: 1100 }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
    webServer: {
        command: 'node tools/testing/start-browser-server.mjs --port 8771',
        cwd: fileURLToPath(new URL('../../', import.meta.url)),
        url: 'http://127.0.0.1:8771/__test__/',
        reuseExistingServer: false,
        gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
    },
});
