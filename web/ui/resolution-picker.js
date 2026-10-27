const PIXELS_PER_MEGAPIXEL = 1048576;
const MIN_SIDE = 64;
const DEFAULT_STEP = 8;
const NEAREST_CHIP_TOLERANCE = 0.07;
const MAX_RATIO_TERM = 10000;
const MAX_SIDE = 8192;
const RATIO_ALIASES = { '8:5': '16:10', '5:8': '10:16', '7:3': '21:9', '3:7': '9:21' };

export function parseRatio(text) {
    if (typeof text !== 'string') return null;
    const match = /^\s*(\d+)\s*[:/x×]\s*(\d+)\s*$/i.exec(text);
    if (!match) return null;
    const [w, h] = [Number(match[1]), Number(match[2])];
    if (w < 1 || h < 1 || w > MAX_RATIO_TERM || h > MAX_RATIO_TERM) return null;
    return [w, h];
}

function gcd(a, b) {
    return b === 0 ? a : gcd(b, a % b);
}

export function reducedRatio(width, height) {
    const divisor = gcd(width, height);
    const label = `${width / divisor}:${height / divisor}`;
    return RATIO_ALIASES[label] || label;
}

export function findFamily(payload, label) {
    const families = (payload && payload.families) || [];
    return families.find((family) => family.label === label || (family.aliases || []).includes(label)) || null;
}

function chipRatio(chip) {
    const [w, h] = chip.split(':').map(Number);
    return w / h;
}

function listedIndex(list, width, height) {
    return list.findIndex(([w, h]) => w === width && h === height);
}

function nearestChip(chips, width, height) {
    const actual = width / height;
    let best = null;
    let bestError = Infinity;
    for (const chip of chips) {
        const target = chipRatio(chip);
        const error = Math.abs(actual - target) / target;
        if (error < bestError) {
            best = chip;
            bestError = error;
        }
    }
    return bestError <= NEAREST_CHIP_TOLERANCE ? best : null;
}

export function deriveSelection(payload, label, width, height) {
    const family = findFamily(payload, label);
    const chips = payload.chips || [];
    const ratioText = reducedRatio(width, height);
    if (family) {
        for (const chip of chips) {
            const entryIndex = listedIndex(family.sizes[chip] || [], width, height);
            if (entryIndex >= 0) return { family, chip, entryIndex, custom: false, ratioText };
        }
    }
    const chip = nearestChip(chips, width, height);
    return { family, chip, entryIndex: -1, custom: chip === null, ratioText };
}

function roundToStep(side, step) {
    return Math.max(Math.ceil(MIN_SIDE / step) * step, Math.round(side / step) * step);
}

export function sizesForRatio(family, [rw, rh]) {
    const seen = new Set();
    const sizes = [];
    for (const mp of family.megapixels) {
        const height = Math.sqrt((mp * PIXELS_PER_MEGAPIXEL * rh) / rw);
        const width = (height * rw) / rh;
        const size = [roundToStep(width, family.step), roundToStep(height, family.step)];
        if (size[0] > MAX_SIDE || size[1] > MAX_SIDE) continue;
        const key = size.join('x');
        if (seen.has(key)) continue;
        seen.add(key);
        sizes.push(size);
    }
    return sizes.sort((a, b) => a[0] * a[1] - b[0] * b[1]);
}

export function defaultEntry(family, chip) {
    const list = (family && family.sizes[chip]) || [];
    const target = family.default[0] * family.default[1];
    let best = null;
    for (const entry of list) {
        if (best === null || Math.abs(entry[0] * entry[1] - target) < Math.abs(best[0] * best[1] - target)) best = entry;
    }
    return best;
}

export function effectiveSize(family, width, height) {
    const step = family ? family.step : DEFAULT_STEP;
    return [roundToStep(width, step), roundToStep(height, step)];
}

export function megapixels(width, height) {
    return ((width * height) / PIXELS_PER_MEGAPIXEL).toFixed(1);
}

export function sizeOnModelChange(payload, newLabel, width, height, chip) {
    const family = findFamily(payload, newLabel);
    if (!family) return [width, height];
    const listed = Object.values(family.sizes).some((list) => listedIndex(list, width, height) >= 0);
    if (listed) return [width, height];
    return defaultEntry(family, chip) || family.default;
}

const SIZE_LABEL = /^(\d+)×(\d+) - \S+ \(\d+\.\dMP\)$/;

export function sizeLabel(width, height, ratioText) {
    return `${width}×${height} - ${ratioText} (${megapixels(width, height)}MP)`;
}

export function parseSizeLabel(text) {
    const match = typeof text === 'string' ? SIZE_LABEL.exec(text) : null;
    if (!match) return null;
    const [width, height] = [Number(match[1]), Number(match[2])];
    return width > 0 && height > 0 ? [width, height] : null;
}

export function dropdownOptions(payload, label, chip) {
    const family = findFamily(payload, label);
    if (!family) return ['custom'];
    const chips = chip && chip !== 'custom' ? [chip] : payload.chips || [];
    const labels = chips.flatMap((id) => (family.sizes[id] || []).map(([w, h]) => sizeLabel(w, h, id)));
    return ['custom', ...new Set(labels)];
}
