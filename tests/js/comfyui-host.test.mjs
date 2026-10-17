import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtemp, writeFile, mkdir, readFile, realpath, rm, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { once } from 'node:events';
import { launchComfyHost } from '../../tools/testing/comfyui-host.mjs';

async function fixture(t, program) {
    const directory = await mkdtemp(join(tmpdir(), 'kiko-host-test-'));
    t.after(() => rm(directory, { recursive: true, force: true }));
    const checkout = join(directory, 'host');
    const repository = join(directory, 'plugin');
    await mkdir(checkout);
    await mkdir(repository);
    await writeFile(join(repository, '__init__.py'), '');
    await writeFile(join(checkout, 'main.py'), program);
    const git = args => execFileSync('git', ['-C', checkout, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
    git(['init', '--quiet']);
    git(['add', 'main.py']);
    git(['-c', 'user.name=Kiko Tests', '-c', 'user.email=tests@example.invalid', 'commit', '--quiet', '-m', 'fixture']);
    return { checkout, repository, python: process.execPath, port: 8199,
        pins: { revision: git(['rev-parse', 'HEAD']) }, logPath: join(directory, 'host.log'), forwardOutput: false };
}

const idle = `console.log('ready'); setInterval(() => {}, 1000);`;

test('managed ComfyUI host uses disposable CPU/offline state and preserves source directories', async t => {
    const options = await fixture(t, idle);
    const host = await launchComfyHost(options);
    t.after(() => host.stop());
    await once(host.child.stdout, 'data');
    const args = host.child.spawnargs;
    for (const flag of ['--cpu', '--offline', '--disable-all-custom-nodes']) assert.ok(args.includes(flag));
    assert.equal(args[args.indexOf('--base-directory') + 1], host.stateDirectory);
    assert.equal(args[args.indexOf('--listen') + 1], '127.0.0.1');
    assert.equal(args[args.indexOf('--whitelist-custom-nodes') + 1], 'kikotools');
    assert.equal(await realpath(join(host.stateDirectory, 'custom_nodes/kikotools')), await realpath(options.repository));
    await access(join(host.stateDirectory, 'user'));
    await host.stop();
    await assert.rejects(access(host.stateDirectory), { code: 'ENOENT' });
    await access(join(options.checkout, 'main.py'));
    await access(join(options.repository, '__init__.py'));
});

test('managed ComfyUI host rejects a mismatched or modified upstream checkout', async t => {
    const options = await fixture(t, idle);
    await assert.rejects(launchComfyHost({ ...options, pins: { revision: '0'.repeat(40) } }), /revision/i);
    await writeFile(join(options.checkout, 'main.py'), 'modified');
    await assert.rejects(launchComfyHost(options), /modified|dirty/i);
});

test('managed ComfyUI host preserves crash diagnostics, exit status and cleanup', async t => {
    const options = await fixture(t, `console.error('startup failed'); process.exit(7);`);
    const host = await launchComfyHost(options);
    const result = await host.finished;
    assert.equal(result.code, 7);
    assert.match(await readFile(options.logPath, 'utf8'), /startup failed/);
    await assert.rejects(access(host.stateDirectory), { code: 'ENOENT' });
});

test('managed ComfyUI host reports spawn failures and releases its temporary state', async t => {
    const options = await fixture(t, idle);
    const host = await launchComfyHost({ ...options, python: join(options.checkout, 'missing-python') });
    const result = await host.finished;
    assert.equal(result.code, 1);
    assert.match(result.error.message, /ENOENT/);
    await assert.rejects(access(host.stateDirectory), { code: 'ENOENT' });
});

test('managed ComfyUI host fails before spawning when its log cannot be opened', async t => {
    const options = await fixture(t, `require('node:fs').writeFileSync(process.argv[1] + '.started', 'yes');`);
    await assert.rejects(launchComfyHost({ ...options, logPath: options.checkout }), /EISDIR|directory/i);
    await assert.rejects(access(join(options.checkout, 'main.py.started')), { code: 'ENOENT' });
});
