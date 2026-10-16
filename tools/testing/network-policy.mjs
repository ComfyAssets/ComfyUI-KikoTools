export function isFixtureURL(raw, baseURL) {
    const url = new URL(raw);
    return url.origin === new URL(baseURL).origin && ['http:', 'https:', 'blob:'].includes(url.protocol);
}
