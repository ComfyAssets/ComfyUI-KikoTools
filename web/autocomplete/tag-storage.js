export function tagCache(value) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('kikotools-autocomplete', 1);
        request.onupgradeneeded = () => request.result.createObjectStore('tags');
        request.onerror = () => reject(request.error);
        let blocked = false;
        request.onblocked = () => { blocked = true; reject(new Error('Tag storage is blocked by another browser tab.')); };
        request.onsuccess = () => {
            const db = request.result;
            if (blocked) { db.close(); return; }
            db.onversionchange = () => db.close();
            const transaction = db.transaction('tags', value === undefined ? 'readonly' : 'readwrite');
            const store = transaction.objectStore('tags');
            const result = value === undefined ? store.get('active') : store.put(value, 'active');
            transaction.oncomplete = () => { db.close(); resolve(result.result); };
            transaction.onabort = transaction.onerror = () => { db.close(); reject(transaction.error || new Error('Could not access tag storage.')); };
        };
    });
}

export function parseTagFile(text, signal) {
    return new Promise((resolve, reject) => {
        if (signal.aborted) { reject(new DOMException('Import cancelled.', 'AbortError')); return; }
        const worker = new Worker(new URL('./tag-worker.js', import.meta.url), { type: 'module' });
        const finish = (callback, value) => {
            worker.terminate();
            signal.removeEventListener('abort', abort);
            callback(value);
        };
        const abort = () => finish(reject, new DOMException('Import cancelled.', 'AbortError'));
        signal.addEventListener('abort', abort, { once: true });
        worker.onmessage = ({ data }) => data.error ? finish(reject, new Error(data.error)) : finish(resolve, data.tags);
        worker.onerror = () => finish(reject, new Error('Could not parse tag file.'));
        worker.postMessage(text);
    });
}
