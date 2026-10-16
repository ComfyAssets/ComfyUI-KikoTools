export function normalizeHex(value) {
    return typeof value === 'string' && /^#?[\da-f]{6}$/i.test(value)
        ? `#${value.replace(/^#/, '').toLowerCase()}` : null;
}

export function hexToHsv(hex) {
    const [r, g, b] = hex.slice(1).match(/../g).map(value => parseInt(value, 16) / 255);
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const delta = max - min;
    let h = 0;
    if (delta) {
        if (max === r) h = (g - b) / delta + (g < b ? 6 : 0);
        else if (max === g) h = (b - r) / delta + 2;
        else h = (r - g) / delta + 4;
    }
    return { h: h * 60, s: max ? delta / max * 100 : 0, v: max * 100 };
}

export function hsvToHex(h, s, v) {
    h = ((h % 360) + 360) % 360;
    s = Math.max(0, Math.min(100, s)) / 100;
    v = Math.max(0, Math.min(100, v)) / 100;
    const c = v * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = v - c;
    const channels = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x]
        : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return '#' + channels.map(value => Math.round((value + m) * 255).toString(16).padStart(2, '0')).join('');
}
