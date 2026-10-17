import { spawn, execFileSync } from 'node:child_process';
import { mkdir, mkdtemp, realpath, rm, symlink, access, open } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import runtime from './comfyui-runtime.json' with { type: 'json' };

const repositoryRoot = fileURLToPath(new URL('../../', import.meta.url));

export async function launchComfyHost({ checkout, repository = repositoryRoot,
    python = process.env.KIKO_TEST_PYTHON || 'python', port = 8189, pins = runtime,
    logPath = join(repositoryRoot, 'tools/testing/test-results/comfyui-host.log'), forwardOutput = true }) {
    if (!checkout) throw new Error('Set KIKO_COMFY_ROOT to the pinned ComfyUI checkout');
    if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Use an unprivileged ComfyUI port');
    checkout = await realpath(checkout);
    repository = await realpath(repository);
    await access(join(checkout, 'main.py'));
    await access(join(repository, '__init__.py'));
    const git = args => execFileSync('git', ['-C', checkout, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
    if (git(['rev-parse', 'HEAD']) !== pins.revision) throw new Error(`ComfyUI revision must be ${pins.revision}`);
    try { git(['diff', '--quiet', 'HEAD', '--']); }
    catch { throw new Error('ComfyUI checkout has modified tracked files'); }
    const stateDirectory = await mkdtemp(join(tmpdir(), 'kiko-comfy-host-'));
    let log, child;
    try {
        for (const directory of ['user', 'input', 'output', 'temp', 'custom_nodes']) await mkdir(join(stateDirectory, directory));
        await symlink(repository, join(stateDirectory, 'custom_nodes/kikotools'), 'junction');
        await mkdir(dirname(logPath), { recursive: true });
        const handle = await open(logPath, 'w');
        log = handle.createWriteStream();
        child = spawn(python, [join(checkout, 'main.py'), '--cpu', '--offline',
            '--listen', '127.0.0.1', '--port', String(port), '--base-directory', stateDirectory,
            '--user-directory', join(stateDirectory, 'user'), '--database-url', 'sqlite:///:memory:',
            '--disable-all-custom-nodes', '--whitelist-custom-nodes', 'kikotools'], {
            cwd: checkout, stdio: ['ignore', 'pipe', 'pipe'],
            env: { ...process.env, PYTHONUNBUFFERED: '1', HF_HUB_OFFLINE: '1', TRANSFORMERS_OFFLINE: '1' },
        });
    } catch (error) {
        log?.end();
        await rm(stateDirectory, { recursive: true, force: true });
        throw error;
    }
    let error, stopping = false;
    for (const [stream, output] of [[child.stdout, process.stdout], [child.stderr, process.stderr]]) {
        stream.on('data', chunk => { log.write(chunk); if (forwardOutput) output.write(chunk); });
    }
    child.on('error', value => { error = value; log.write(`ComfyUI failed to start: ${value.message}\n`); });
    const finished = new Promise(resolve => child.once('close', (code, signal) => resolve({ code, signal })))
        .then(async result => {
            const code = error ? 1 : result.code ?? (stopping ? 0 : 1);
            log.write(`ComfyUI stopped: exit=${code}, signal=${result.signal || 'none'}\n`);
            await new Promise(resolve => log.end(resolve));
            await rm(stateDirectory, { recursive: true, force: true });
            return { ...result, code, error };
        });
    return { child, stateDirectory, finished, async stop() {
        stopping = true;
        if (child.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
        const deadline = setTimeout(() => child.kill('SIGKILL'), 5000);
        deadline.unref();
        try { return await finished; }
        finally { clearTimeout(deadline); }
    } };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
    try {
        const host = await launchComfyHost({ checkout: process.env.KIKO_COMFY_ROOT,
            port: Number(process.env.KIKO_COMFY_PORT || 8189) });
        const stop = () => { host.stop().catch(error => { console.error(error.message); process.exitCode = 1; }); };
        process.once('SIGINT', stop);
        process.once('SIGTERM', stop);
        const result = await host.finished;
        process.removeListener('SIGINT', stop);
        process.removeListener('SIGTERM', stop);
        if (result.code) console.error(`ComfyUI host exited with status ${result.code}; see tools/testing/test-results/comfyui-host.log`);
        process.exitCode = result.code;
    } catch (error) { console.error(error.message); process.exitCode = 1; }
}
