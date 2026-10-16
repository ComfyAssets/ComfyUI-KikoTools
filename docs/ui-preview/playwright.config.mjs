import { defineConfig, devices } from '../../tools/testing/node_modules/@playwright/test/index.mjs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('./', import.meta.url));

export default defineConfig({
    testDir: './tests',
    outputDir: '../../tools/testing/test-results/ui-preview',
    workers: 1,
    forbidOnly: Boolean(process.env.CI),
    retries: 0,
    use: {
        baseURL: 'http://127.0.0.1:8769',
        viewport: { width: 1440, height: 1050 },
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
    },
    webServer: {
        command: 'python3 -m http.server 8769 --bind 127.0.0.1',
        cwd: root,
        url: 'http://127.0.0.1:8769/',
        reuseExistingServer: false,
    },
    projects: [
        { name: 'chromium', use: { browserName: 'chromium' } },
        { name: 'firefox', use: { browserName: 'firefox' } },
        { name: 'webkit', use: { browserName: 'webkit' } },
        { name: 'touch', use: { ...devices['Pixel 7'], browserName: 'chromium' } },
    ],
});
