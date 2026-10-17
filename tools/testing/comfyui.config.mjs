import { defineConfig } from './node_modules/@playwright/test/index.mjs';
import { fileURLToPath } from 'node:url';

const managed = Boolean(process.env.KIKO_COMFY_ROOT);
const hostURL = process.env.KIKO_COMFY_URL || (managed ? 'http://127.0.0.1:8189/' : null);
if (!hostURL) throw new Error('Set KIKO_COMFY_URL for an existing host or KIKO_COMFY_ROOT for a managed host');
const host = new URL(hostURL);
if (!['http:', 'https:'].includes(host.protocol) || !['127.0.0.1', 'localhost', '[::1]'].includes(host.hostname)) throw new Error('The ComfyUI smoke suite only accepts a loopback host');
if (managed && (host.protocol !== 'http:' || host.hostname !== '127.0.0.1' || !host.port)) throw new Error('A managed host needs an HTTP 127.0.0.1 URL with an explicit port');
const servers = [{
    command: 'node tools/testing/start-browser-server.mjs --port 8771',
    cwd: fileURLToPath(new URL('../../', import.meta.url)),
    url: 'http://127.0.0.1:8771/__test__/', reuseExistingServer: false,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
}];
if (managed) servers.unshift({
    command: 'node tools/testing/comfyui-host.mjs',
    cwd: fileURLToPath(new URL('../../', import.meta.url)),
    url: new URL('system_stats', host).href, timeout: 120000, reuseExistingServer: false,
    env: { KIKO_COMFY_PORT: host.port },
    gracefulShutdown: { signal: 'SIGTERM', timeout: 10000 },
});

export default defineConfig({
    testDir: '../../tests/comfyui',
    outputDir: './test-results/comfyui',
    timeout: 60000,
    workers: 1,
    forbidOnly: Boolean(process.env.CI),
    retries: 0,
    use: { baseURL: host.href, browserName: 'chromium', viewport: { width: 1600, height: 1100 }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
    webServer: servers,
    projects: [
        { name: 'classic-start', metadata: { initialRenderer: false } },
        { name: 'nodes2-start', metadata: { initialRenderer: true } },
    ],
});
