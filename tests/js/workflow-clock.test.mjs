import test from 'node:test';
import assert from 'node:assert/strict';
import { WorkflowClock, formatElapsed } from '../../web/ui/workflow-clock.js';
import { normalizeHex, hexToHsv, hsvToHex } from '../../web/ui/color.js';

function fixture() {
    let now = 0;
    const intervals = new Map();
    const settings = new Map();
    const clock = new WorkflowClock({ getSettingValue: id => settings.get(id) }, {
        Date: { now: () => now },
        setInterval(callback) { const id = Symbol(); intervals.set(id, callback); return id; },
        clearInterval(id) { intervals.delete(id); },
    });
    const node = () => ({ properties: {}, timerDisplay: {
        textContent: '',
        style: { setProperty(name, value) { this[name] = value; } },
        classList: { values: new Set(), toggle(name, enabled) { enabled ? this.values.add(name) : this.values.delete(name); } },
    } });
    return { clock, settings, intervals, node, advance(ms) { now += ms; for (const callback of intervals.values()) callback(); } };
}

test('elapsed formatting handles minutes, milliseconds and invalid durations', () => {
    assert.equal(formatElapsed(0), '00:00:000');
    assert.equal(formatElapsed(-1), '00:00:000');
    assert.equal(formatElapsed(NaN), '00:00:000');
    assert.equal(formatElapsed(61234.7), '01:01:234');
    assert.equal(formatElapsed(3600000), '60:00:000');
});

test('one clock synchronizes late joining nodes and persists the final duration', () => {
    const f = fixture();
    const first = f.node();
    f.clock.registerNode(first);
    f.clock.start();
    f.advance(1200);
    f.clock.start();
    const second = f.node();
    f.clock.registerNode(second);
    assert.equal(f.intervals.size, 1);
    assert.equal(first.timerDisplay.textContent, '00:01:200');
    assert.equal(second.timerDisplay.textContent, first.timerDisplay.textContent);
    assert.equal(second.timerDisplay.classList.values.has('running'), true);
    f.advance(34);
    f.clock.stop();
    f.clock.stop();
    assert.equal(f.intervals.size, 0);
    assert.equal(f.clock.intervalId, null);
    for (const node of [first, second]) {
        assert.equal(node.properties.elapsed_time_str, '00:01:234');
        assert.equal(node.timerDisplay.classList.values.has('running'), false);
    }
});

test('removing the final node releases polling while late nodes can rejoin an active run', () => {
    const f = fixture();
    f.clock.start();
    assert.equal(f.intervals.size, 0);
    f.advance(1000);
    const first = f.node();
    f.clock.registerNode(first);
    assert.equal(first.timerDisplay.textContent, '00:01:000');
    assert.equal(f.intervals.size, 1);
    f.clock.unregisterNode(first);
    assert.equal(f.intervals.size, 0);
    f.advance(1000);
    const next = f.node();
    f.clock.registerNode(next);
    assert.equal(next.timerDisplay.textContent, '00:02:000');
    f.clock.stop();
    f.clock.start();
    assert.equal(next.timerDisplay.textContent, '00:00:000');
    f.clock.unregisterNode(next);
    assert.equal(f.intervals.size, 0);
});

test('configured colors and glow update during a run and saved durations restore', () => {
    const f = fixture();
    const node = f.node();
    node.properties.elapsed_time_str = '02:03:456';
    f.clock.registerNode(node);
    assert.equal(node.timerDisplay.textContent, '02:03:456');
    assert.equal(node.timerDisplay.style['--ca-timer-color'], '#0877bb');
    f.clock.start();
    f.settings.set('kikotools.workflow_timer.color', '#Ff9966');
    f.settings.set('kikotools.workflow_timer.glow', false);
    f.clock.refresh();
    assert.equal(node.timerDisplay.style['--ca-timer-color'], '#ff9966');
    assert.equal(node.timerDisplay.classList.values.has('no-glow'), true);
    f.settings.set('kikotools.workflow_timer.color', 'invalid');
    f.clock.refresh();
    assert.equal(node.timerDisplay.style['--ca-timer-color'], '#0877bb');
});

test('hex colors normalize strictly and HSV conversion round trips representative colors', () => {
    assert.equal(normalizeHex('Ff9966'), '#ff9966');
    for (const invalid of ['', '#xyzxyz', '#12345', null, {}, '#ffffff; color:red']) assert.equal(normalizeHex(invalid), null);
    for (const hex of ['#000000', '#ffffff', '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#00ffff', '#ff00ff', '#ff9966', '#0877bb']) {
        const { h, s, v } = hexToHsv(hex);
        assert.equal(hsvToHex(h, s, v), hex);
    }
    assert.equal(hsvToHex(360, 100, 100), '#ff0000');
    assert.equal(hsvToHex(-120, 100, 100), '#0000ff');
    assert.equal(hsvToHex(0, 120, -1), '#000000');
});
