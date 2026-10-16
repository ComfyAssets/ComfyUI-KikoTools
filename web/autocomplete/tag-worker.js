import { parseTagList } from './tags.js';
self.onmessage = ({ data }) => {
    try { self.postMessage({ tags: parseTagList(data) }); }
    catch (error) { self.postMessage({ error: error.message }); }
};
