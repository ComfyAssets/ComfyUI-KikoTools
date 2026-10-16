import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";
import { createScope } from './ui/core.js';
import { createSuggestionView } from './ui/autocomplete-suggestions.js';
import { watchRendererTextareas } from './ui/text-widget-adapter.js';
import { createAutocompleteLauncher } from './views/autocomplete-settings.js';
import { searchTags, tagQuery } from './autocomplete/tags.js';
import { parseTagFile, tagCache } from './autocomplete/tag-storage.js';
import { readTagResponse } from './autocomplete/tag-download.js';

// KikoEmbeddingAutocomplete - Provides autocomplete for embeddings and LoRAs in text widgets
class KikoEmbeddingAutocomplete {
    constructor() {
        this.scope = createScope();
        this.widgetCleanups = new Set();
        this.nodeHooks = new WeakMap();
        this.pendingFrames = new Set();
        this.embeddings = [];
        this.loras = [];
        this.customWords = [];
        this.settings = {
            enabled: true,
            showEmbeddings: true,
            showLoras: true,
            showCustomWords: true,
            embeddingTrigger: "embedding:",
            loraTrigger: "<lora:",
            quickTrigger: "em",
            minChars: 2,
            maxSuggestions: 20,
            sortByDirectory: true,
            customWordsUrl: "https://gist.githubusercontent.com/pythongosssss/1d3efa6050356a08cea975183088159a/raw/a18fb2f94f9156cf4476b0c24a09544d6c0baec6/danbooru-tags.txt",
            autoInsertComma: true,
            replaceUnderscores: true,
            insertOnTab: true,
            insertOnEnter: true
        };

        // Load settings from localStorage
        this.loadSettings();

        // Track active widgets with proper cleanup
        this.widgetCleanupMap = new WeakMap();
        this.activeWidgets = new WeakSet();

        // Track pending fetch requests for cleanup
        this.pendingFetches = new Set();

        // Debounce resource fetching
        this.fetchResourcesDebounced = this.debounce(() => this.fetchResources(), 500);
        this.fetchResourcesDebounced();

        // Load custom words if URL is set
        if ((this.settings.tagSource || this.settings.customWordsUrl) && this.settings.showCustomWords) {
            this.restoreCustomWords();
        }

        // Single suggestion container for all widgets
        this.suggestionContainer = null;
        this.currentWidget = null;

        // Cleanup on page unload
        this.scope.listen(window, 'beforeunload', () => this.cleanup());
        this.scope.listen(window, 'resize', () => this.hideSuggestions());
        this.scope.listen(window, 'scroll', () => this.hideSuggestions());
        watchRendererTextareas(this.scope, app.graph, this);
    }

    debounce(func, wait) {
        let timeout;
        const debounced = (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => { if (!this.scope.signal.aborted) func(...args); }, wait);
        };
        debounced.cancel = () => clearTimeout(timeout);
        return debounced;
    }

    nextFrame(callback) {
        if (this.scope.signal.aborted) return;
        const frame = requestAnimationFrame(() => {
            this.pendingFrames.delete(frame);
            if (!this.scope.signal.aborted) callback();
        });
        this.pendingFrames.add(frame);
    }

    cleanup() {
        this.fetchResourcesDebounced.cancel();
        for (const frame of this.pendingFrames) cancelAnimationFrame(frame);
        this.pendingFrames.clear();
        this.settingsDialog?.close('removed');
        for (const cleanup of [...this.widgetCleanups]) cleanup();
        for (const controller of this.pendingFetches) controller.abort();
        this.pendingFetches.clear();
        this.scope.dispose();
        this.suggestionContainer = null;
        this.suggestionView = null;
    }

    loadSettings() {
        try {
            const stored = localStorage.getItem("kikotools.embedding_autocomplete.settings");
            if (stored) {
                Object.assign(this.settings, JSON.parse(stored));
            }
        } catch (error) {
            console.error("[KikoTools] Error loading autocomplete settings:", error);
        }
    }

    saveSettings() {
        try {
            localStorage.setItem("kikotools.embedding_autocomplete.settings", JSON.stringify(this.settings));
            return true;
        } catch (error) {
            console.error("[KikoTools] Error saving autocomplete settings:", error);
            return false;
        }
    }

    async fetchWithAbort(url, options = {}) {
        const controller = new AbortController();
        this.pendingFetches.add(controller);

        try {
            const response = await fetch(url, {
                ...options,
                signal: AbortSignal.any([controller.signal, this.scope.signal, ...(options.signal ? [options.signal] : [])])
            });
            this.pendingFetches.delete(controller);
            return response;
        } catch (error) {
            this.pendingFetches.delete(controller);
            if (error.name === 'AbortError') {
                return null;
            }
            throw error;
        }
    }

    async fetchResources() {
        try {
            // Fetch embeddings
            if (this.settings.showEmbeddings) {
                await this.fetchEmbeddings();
            }

            // Fetch LoRAs
            if (this.settings.showLoras) {
                await this.fetchLoras();
            }

        } catch (error) {
            console.error("[KikoTools] Error fetching resources:", error);
        }
    }

    async fetchEmbeddings() {
        // Try custom endpoint first
        try {
            const response = await this.fetchWithAbort("/kikotools/autocomplete/embeddings");
            if (response && response.ok) {
                const embeddingsData = await response.json();
                this.embeddings = embeddingsData.map(item => {
                    const fullPath = item.path || item.file_name || item.model_name;
                    const nameOnly = item.name || fullPath.split('/').pop();

                    return {
                        name: nameOnly,
                        fullPath: fullPath,
                        type: "embedding",
                        display: `embedding:${fullPath}`,
                        value: `embedding:${fullPath}`
                    };
                });
                return;
            }
        } catch (e) {
            // Custom endpoint failed, try fallback
        }

        // Fallback to ComfyUI API
        try {
            const embeddingsResponse = await api.getEmbeddings();

            let allEmbeddings = [];

            // Handle paginated response
            if (embeddingsResponse && embeddingsResponse.items && Array.isArray(embeddingsResponse.items)) {
                allEmbeddings = [...embeddingsResponse.items];
                const totalPages = embeddingsResponse.total_pages || 1;

                // Fetch remaining pages
                for (let page = 2; page <= totalPages && page <= 10; page++) { // Limit to 10 pages
                    try {
                        const pageData = await api.getEmbeddings(page);
                        if (pageData && pageData.items) {
                            allEmbeddings.push(...pageData.items);
                        }
                    } catch (err) {
                        break;
                    }
                }

                this.embeddings = allEmbeddings.map(item => {
                    let fullPath = "";

                    if (typeof item === 'string') {
                        fullPath = item;
                    } else if (item && typeof item === 'object') {
                        fullPath = item.file_name || item.model_name || item.name || item.filename;
                    }

                    const cleanPath = String(fullPath || "").replace(/\.(pt|safetensors|ckpt|bin)$/i, '');
                    const nameOnly = cleanPath.split('/').pop() || cleanPath;

                    if (cleanPath && cleanPath !== "undefined") {
                        return {
                            name: nameOnly,
                            fullPath: cleanPath,
                            type: "embedding",
                            display: `embedding:${cleanPath}`,
                            value: `embedding:${cleanPath}`
                        };
                    }
                    return null;
                }).filter(item => item !== null);
            }
            // Handle object format (old API)
            else if (embeddingsResponse && typeof embeddingsResponse === 'object' && !Array.isArray(embeddingsResponse)) {
                const keys = Object.keys(embeddingsResponse);

                if (!keys.includes('items') && !keys.includes('total')) {
                    this.embeddings = keys.map(fullPath => {
                        const cleanPath = fullPath.replace(/\.(pt|safetensors|ckpt|bin)$/i, '');
                        const nameOnly = cleanPath.split('/').pop() || cleanPath;
                        return {
                            name: nameOnly,
                            fullPath: cleanPath,
                            type: "embedding",
                            display: `embedding:${cleanPath}`,
                            value: `embedding:${cleanPath}`
                        };
                    });
                }
            }
        } catch (e) {
            this.embeddings = [];
        }
    }

    async fetchLoras() {
        // Try custom endpoint first
        try {
            const response = await this.fetchWithAbort("/kikotools/autocomplete/loras");
            if (response && response.ok) {
                const lorasData = await response.json();
                this.loras = lorasData.map(item => {
                    const path = item.path || item.name;
                    const nameOnly = item.name || path.split('/').pop();

                    return {
                        name: nameOnly,
                        fullPath: path,
                        type: "lora",
                        display: `<lora:${path}:1.0>`,
                        value: `<lora:${path}:1.0>`
                    };
                });
                return;
            }
        } catch (e) {
            // Custom endpoint failed, try fallback
        }

        // Fallback to object info API
        try {
            const response = await this.fetchWithAbort("/object_info");
            if (response && response.ok) {
                const objectInfo = await response.json();
                if (objectInfo.LoraLoader?.input?.required?.lora_name?.[0]) {
                    const loraNames = objectInfo.LoraLoader.input.required.lora_name[0];
                    this.loras = loraNames.map(name => {
                        const cleanName = name.replace(/\.(pt|safetensors|ckpt|bin)$/i, '');
                        return {
                            name: cleanName,
                            fullPath: cleanName,
                            type: "lora",
                            display: `<lora:${cleanName}:1.0>`,
                            value: `<lora:${cleanName}:1.0>`
                        };
                    });
                }
            }
        } catch (e) {
            this.loras = [];
        }
    }

    async restoreCustomWords() {
        const revision = this.tagRevision = (this.tagRevision || 0) + 1;
        try {
            const cached = await tagCache();
            const source = this.settings.tagSource || this.settings.customWordsUrl;
            if (cached?.source === source) {
                const tags = await parseTagFile(cached.text, this.scope.signal);
                if (!this.scope.signal.aborted && revision === this.tagRevision) this.customWords = tags;
            } else if (!this.scope.signal.aborted && revision === this.tagRevision) {
                if (this.settings.tagSource?.startsWith('file:')) this.customWordsError = 'Saved tag file is missing. Import it again.';
                else await this.loadCustomWords(this.settings.customWordsUrl);
            }
        } catch (error) {
            if (error.name !== 'AbortError' && !this.scope.signal.aborted && revision === this.tagRevision) {
                if (this.settings.tagSource?.startsWith('file:')) this.customWordsError = 'Could not restore the saved tag file. Import it again.';
                else await this.loadCustomWords(this.settings.customWordsUrl);
            }
        }
    }

    async fetchTagList(url, signal = this.scope.signal) {
        const parsed = new URL(url, location.href);
        if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Use an HTTP or HTTPS tag-list URL.');
        const response = await this.fetchWithAbort(parsed.href, { signal });
        if (!response?.ok) throw new Error(`Tag download failed (${response?.status || 'cancelled'}).`);
        const text = await readTagResponse(response, { signal });
        const tags = await parseTagFile(text, signal);
        return { text, tags, source: parsed.href };
    }

    async loadCustomWords(url) {
        if (!url || this.scope.signal.aborted) return 0;
        const revision = this.tagRevision = (this.tagRevision || 0) + 1;
        try {
            const list = await this.fetchTagList(url);
            if (revision !== this.tagRevision || this.scope.signal.aborted) return 0;
            this.customWords = list.tags;
            this.customWordsError = '';
            return this.customWords.length;
        } catch (error) {
            if (error.name !== 'AbortError') this.customWordsError = error.message;
            return 0;
        }
    }

    async saveTagSettings(next, pending) {
        const previous = { ...this.settings };
        Object.assign(this.settings, next);
        if (!this.saveSettings()) {
            this.settings = previous;
            throw new Error('Could not save settings. Check browser storage and try again.');
        }
        if (pending) {
            try { await tagCache({ text: pending.text, source: pending.source }); }
            catch (error) {
                this.settings = previous;
                this.saveSettings();
                throw new Error(`Could not save tag list: ${error.message}`);
            }
            this.tagRevision = (this.tagRevision || 0) + 1;
            this.customWords = pending.tags;
            this.customWordsError = '';
        }
        if (this.settings.showEmbeddings || this.settings.showLoras) this.fetchResourcesDebounced();
        if (!pending && this.settings.showCustomWords && (!previous.showCustomWords || previous.customWordsUrl !== this.settings.customWordsUrl)) this.restoreCustomWords();
    }

    createSuggestionContainer() {
        if (this.suggestionContainer) return;
        this.suggestionView = createSuggestionView(this.scope, app.ui.settings);
        this.suggestionContainer = this.suggestionView.element;
    }

    hideSuggestions() {
        this.currentWidget?.inputEl.removeAttribute('aria-activedescendant');
        this.suggestionView?.hide();
        this.currentWidget = null;
    }

    attachToWidget(widget, node) {
        if (this.scope.signal.aborted || !widget.inputEl || widget.inputEl.readOnly || widget.inputEl.disabled || this.activeWidgets.has(widget)) {
            return;
        }

        if (node.graph === null || (node.graph?._nodes && !node.graph._nodes.includes(node))) return;
        this.activeWidgets.add(widget);
        const textarea = widget.inputEl;
        const widgetScope = createScope();
        let blurFrame;
        widgetScope.cleanup(() => cancelAnimationFrame(blurFrame));
        const attributes = new Map(['aria-controls', 'aria-autocomplete', 'aria-haspopup', 'aria-activedescendant'].map(name => [name, textarea.getAttribute(name)]));

        // Create suggestion container if it doesn't exist
        if (!this.suggestionContainer) {
            this.createSuggestionContainer();
        }

        textarea.setAttribute('aria-controls', this.suggestionContainer.id);
        textarea.setAttribute('aria-autocomplete', 'list');
        textarea.setAttribute('aria-haspopup', 'listbox');

        // Store widget-specific state
        const widgetState = {
            currentSuggestions: [],
            selectedIndex: -1,
            currentPrefix: "",
            prefixStart: -1
        };

        // Event handler functions
        const handlers = {
            hideSuggestions: () => {
                if (this.currentWidget === widget) this.hideSuggestions();
                widgetState.selectedIndex = -1;
                widgetState.currentSuggestions = [];
            },

            showSuggestions: (suggestions) => {
                if (!suggestions.length) { handlers.hideSuggestions(); return; }
                if (this.currentWidget !== widget) this.hideSuggestions();
                this.currentWidget = widget;
                if (widgetState.selectedIndex >= suggestions.length) widgetState.selectedIndex = -1;
                this.suggestionView.render(suggestions, index => {
                    widgetState.selectedIndex = index;
                    handlers.updateSelection();
                }, handlers.insertSuggestion);
                handlers.updateSelection();
                this.suggestionView.position(textarea.getBoundingClientRect());
            },

            updateSelection: () => {
                const id = this.suggestionView.select(widgetState.selectedIndex);
                if (id) textarea.setAttribute('aria-activedescendant', id);
                else textarea.removeAttribute('aria-activedescendant');
            },

            insertSuggestion: (suggestion) => {
                const text = textarea.value;
                const cursor = textarea.selectionStart;
                const textBefore = text.substring(0, cursor);

                let insertText = "";
                let replaceLength = cursor - widgetState.prefixStart;

                // Apply replace underscores setting for custom words
                if (suggestion.type === "custom" && this.settings.replaceUnderscores) {
                    suggestion = {
                        ...suggestion,
                        name: suggestion.name.replace(/_/g, ' '),
                        value: suggestion.value.replace(/_/g, ' '),
                        display: suggestion.display.replace(/_/g, ' ')
                    };
                }

                // Check context and determine what to insert
                const embTrigger = this.settings.embeddingTrigger || "embedding:";
                const embRegex = new RegExp(embTrigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + "([a-zA-Z0-9_\\/-]*)$");

                if (textBefore.match(embRegex) || (embTrigger === "embedding:" && textBefore.match(/embeddings:([a-zA-Z0-9_\/-]*)$/))) {
                    insertText = suggestion.fullPath || suggestion.name;
                } else if (suggestion.type === "lora") {
                    const loraTrigger = this.settings.loraTrigger || "<lora:";
                    const escapedTrigger = loraTrigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    const loraRegex = new RegExp(escapedTrigger + "([a-zA-Z0-9_\\s\\/-]*)$");

                    if (textBefore.match(loraRegex)) {
                        insertText = (suggestion.fullPath || suggestion.name) + ":1.0>";
                    } else {
                        insertText = suggestion.value || suggestion.display;
                    }
                } else if (widgetState.currentPrefix && textBefore.match(/\b(em|emb|embe|embed|embeddi|embeddin|embedding)$/i)) {
                    const match = textBefore.match(/\b(em|emb|embe|embed|embeddi|embeddin|embedding)$/i);
                    insertText = suggestion.value || suggestion.display;
                    widgetState.prefixStart = cursor - match[1].length;
                    replaceLength = match[1].length;
                } else {
                    insertText = suggestion.value || suggestion.display;
                    replaceLength = cursor - widgetState.prefixStart;
                }

                const before = text.substring(0, widgetState.prefixStart);
                const after = text.substring(widgetState.prefixStart + replaceLength);

                // Add comma if enabled
                let finalInsertText = insertText;
                if (this.settings.autoInsertComma && (suggestion.type === "custom" || suggestion.type === "embedding" || suggestion.type === "lora")) {
                    const trimmedAfter = after.trim();
                    if (!/^(?:[,.;)\]]|:\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)\s*[)\]])/.test(trimmedAfter)) {
                        finalInsertText += ', ';
                    }
                }

                textarea.focus({ preventScroll: true });
                textarea.value = before + finalInsertText + after;
                textarea.selectionStart = textarea.selectionEnd = widgetState.prefixStart + finalInsertText.length;

                handlers.hideSuggestions();

                // Trigger change event
                const event = new Event("input", { bubbles: true });
                textarea.dispatchEvent(event);
            },

            findPrefix: () => {
                const text = textarea.value;
                const cursor = textarea.selectionStart;
                const textBefore = text.substring(0, cursor);

                // Check for embedding trigger
                const embTrigger = this.settings.embeddingTrigger || "embedding:";
                const embRegex = new RegExp(embTrigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + "([a-zA-Z0-9_\\/-]*)$");
                const embeddingMatch = textBefore.match(embRegex);
                if (embeddingMatch) {
                    widgetState.currentPrefix = embeddingMatch[1].toLowerCase();
                    widgetState.prefixStart = cursor - embeddingMatch[1].length;
                    return "embedding";
                }

                // Check for plural embeddings
                if (embTrigger === "embedding:") {
                    const pluralMatch = textBefore.match(/embeddings:([a-zA-Z0-9_\/-]*)$/);
                    if (pluralMatch) {
                        widgetState.currentPrefix = pluralMatch[1].toLowerCase();
                        widgetState.prefixStart = cursor - pluralMatch[1].length;
                        return "embedding";
                    }
                }

                // Check for LoRA trigger
                const loraTrigger = this.settings.loraTrigger || "<lora:";
                const escapedTrigger = loraTrigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const loraRegex = new RegExp(escapedTrigger + "([a-zA-Z0-9_\\s\\/-]*)$");
                const loraMatch = textBefore.match(loraRegex);
                if (loraMatch) {
                    widgetState.currentPrefix = loraMatch[1].toLowerCase();
                    widgetState.prefixStart = cursor - loraMatch[1].length;
                    return "lora";
                }

                const query = tagQuery(textBefore);
                if (query && [...query.prefix].length >= this.settings.minChars) {
                    widgetState.currentPrefix = query.prefix.toLowerCase();
                    widgetState.prefixStart = query.start;
                    const word = query.prefix;

                    const quickTrigger = this.settings.quickTrigger;
                    if (quickTrigger && word.toLowerCase().startsWith(quickTrigger.toLowerCase())) {
                        return "embedding-word";
                    }

                    return "general";
                }

                return false;
            },

            getSuggestions: (prefix, type) => {
                const suggestions = [];

                if (type === "embedding" && this.settings.showEmbeddings) {
                    suggestions.push(...this.embeddings.filter(e =>
                        prefix === "" || e.name.toLowerCase().includes(prefix) || (e.fullPath && e.fullPath.toLowerCase().includes(prefix))
                    ));
                } else if (type === "embedding-word" && this.settings.showEmbeddings) {
                    suggestions.push(...this.embeddings);
                } else if (type === "lora" && this.settings.showLoras) {
                    suggestions.push(...this.loras.filter(l =>
                        prefix === "" || l.name.toLowerCase().includes(prefix)
                    ));
                } else if (type === "general") {
                    if (this.settings.showEmbeddings) {
                        suggestions.push(...this.embeddings.filter(e =>
                            e.name.toLowerCase().includes(prefix) || (e.fullPath && e.fullPath.toLowerCase().includes(prefix))
                        ));
                    }

                    if (this.settings.showLoras) {
                        suggestions.push(...this.loras.filter(l =>
                            l.name.toLowerCase().includes(prefix)
                        ));
                    }

                    if (this.settings.showCustomWords) {
                        suggestions.push(...searchTags(this.customWords, prefix, this.settings.maxSuggestions));
                    }
                }

                // Sort suggestions
                suggestions.sort((a, b) => {
                    if (a.type === 'custom' && b.type === 'custom') return 0;
                    const aName = a.name.toLowerCase();
                    const bName = b.name.toLowerCase();
                    const aPath = (a.fullPath || a.name).toLowerCase();
                    const bPath = (b.fullPath || b.name).toLowerCase();

                    if (aName === prefix) return -1;
                    if (bName === prefix) return 1;
                    if (aPath === prefix) return -1;
                    if (bPath === prefix) return 1;
                    if (aName.startsWith(prefix) && !bName.startsWith(prefix)) return -1;
                    if (!aName.startsWith(prefix) && bName.startsWith(prefix)) return 1;
                    if (aPath.startsWith(prefix) && !bPath.startsWith(prefix)) return -1;
                    if (!aPath.startsWith(prefix) && bPath.startsWith(prefix)) return 1;

                    if (this.settings.sortByDirectory) {
                        const aDir = aPath.includes('/') ? aPath.split('/')[0] : '';
                        const bDir = bPath.includes('/') ? bPath.split('/')[0] : '';

                        if (aDir !== bDir) {
                            return aDir.localeCompare(bDir);
                        }
                    }

                    return aName.localeCompare(bName);
                });

                return suggestions.slice(0, this.settings.maxSuggestions);
            },

            onInput: (e) => {
                if (!this.settings.enabled || textarea.readOnly || textarea.disabled || e.isComposing) {
                    handlers.hideSuggestions();
                    return;
                }

                const triggerType = handlers.findPrefix();
                widgetState.selectedIndex = -1;
                if (triggerType) {
                    widgetState.currentSuggestions = handlers.getSuggestions(widgetState.currentPrefix, triggerType);
                    if (!widgetState.currentSuggestions.length && triggerType === 'general') {
                        const query = tagQuery(textarea.value.substring(0, textarea.selectionStart), true);
                        if (query && query.start !== widgetState.prefixStart && [...query.prefix].length >= this.settings.minChars) {
                            widgetState.currentPrefix = query.prefix.toLowerCase();
                            widgetState.prefixStart = query.start;
                            widgetState.currentSuggestions = handlers.getSuggestions(widgetState.currentPrefix, triggerType);
                        }
                    }

                    if (widgetState.currentSuggestions.length > 0) {
                        handlers.showSuggestions(widgetState.currentSuggestions);
                    } else {
                        handlers.hideSuggestions();
                    }
                } else {
                    handlers.hideSuggestions();
                }
            },

            onKeydown: (e) => {
                if (e.isComposing || e.keyCode === 229 || !this.suggestionContainer || this.suggestionContainer.hidden || this.currentWidget !== widget) {
                    return;
                }

                if (e.key === "ArrowDown") {
                    e.preventDefault();
                    e.stopPropagation();
                    widgetState.selectedIndex = Math.min(widgetState.selectedIndex + 1, widgetState.currentSuggestions.length - 1);
                    handlers.updateSelection();
                } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    e.stopPropagation();
                    widgetState.selectedIndex = Math.max(widgetState.selectedIndex - 1, 0);
                    handlers.updateSelection();
                } else if ((e.key === "Enter" && this.settings.insertOnEnter) ||
                           (e.key === "Tab" && this.settings.insertOnTab)) {
                    if (widgetState.selectedIndex >= 0 && widgetState.selectedIndex < widgetState.currentSuggestions.length) {
                        e.preventDefault();
                        e.stopPropagation();
                        handlers.insertSuggestion(widgetState.currentSuggestions[widgetState.selectedIndex]);
                    }
                } else if (e.key === "Escape") {
                    e.preventDefault();
                    e.stopPropagation();
                    handlers.hideSuggestions();
                }
            },

            onBlur: () => {
                cancelAnimationFrame(blurFrame);
                blurFrame = requestAnimationFrame(() => {
                    blurFrame = null;
                    if (!widgetScope.signal.aborted && document.activeElement !== textarea && this.currentWidget === widget) handlers.hideSuggestions();
                });
            },

            onScroll: () => {
                // Hide suggestions when scrolling
                if (this.currentWidget === widget) {
                    handlers.hideSuggestions();
                }
            }
        };

        for (const [event, handler] of [['input', handlers.onInput], ['keydown', handlers.onKeydown], ['blur', handlers.onBlur], ['scroll', handlers.onScroll]]) widgetScope.listen(textarea, event, handler);
        const cleanup = () => {
            if (widgetScope.signal.aborted) return;
            handlers.hideSuggestions();
            widgetScope.dispose();
            for (const [name, value] of attributes) {
                if (value === null) textarea.removeAttribute(name);
                else textarea.setAttribute(name, value);
            }
            this.activeWidgets.delete(widget);
            this.widgetCleanupMap.delete(widget);
            this.widgetCleanups.delete(cleanup);
        };
        for (const [owner, name] of [[widget, 'onRemoved'], [widget, 'onRemove']]) {
            const original = owner[name];
            const wrapped = function (...args) { cleanup(); return original?.apply(this, args); };
            owner[name] = wrapped;
            widgetScope.cleanup(() => { if (owner[name] === wrapped) owner[name] = original; });
        }
        let nodeHook = this.nodeHooks.get(node);
        if (!nodeHook) {
            const original = node.onRemoved;
            const cleanups = new Set();
            const wrapped = function (...args) {
                for (const cleanup of [...cleanups]) cleanup();
                return original?.apply(this, args);
            };
            nodeHook = { original, wrapped, cleanups };
            this.nodeHooks.set(node, nodeHook);
            node.onRemoved = wrapped;
        }
        nodeHook.cleanups.add(cleanup);
        widgetScope.cleanup(() => {
            nodeHook.cleanups.delete(cleanup);
            if (!nodeHook.cleanups.size) {
                if (node.onRemoved === nodeHook.wrapped) node.onRemoved = nodeHook.original;
                this.nodeHooks.delete(node);
            }
        });
        this.widgetCleanupMap.set(widget, cleanup);
        this.widgetCleanups.add(cleanup);
    }

    detachFromWidget(widget) {
        const cleanup = this.widgetCleanupMap.get(widget);
        if (cleanup) {
            cleanup();
        }
    }
}

// Initialize and register
let autocompleteInstance = null;
let originalStringWidget = null;

app.registerExtension({
    name: "kikotools.embeddingAutocomplete",

    async setup() {
        // Clean up any existing instance
        if (autocompleteInstance) {
            autocompleteInstance.cleanup();
        }

        // Create new autocomplete instance
        autocompleteInstance = new KikoEmbeddingAutocomplete();
        const instance = autocompleteInstance;

        // Store reference for debugging (but not in global window to avoid conflicts)
        if (!window.kikotools) {
            window.kikotools = {};
        }
        window.kikotools.autocomplete = autocompleteInstance;

        // Add settings button
        app.ui.settings.addSetting({
            id: "kikotools.embeddingAutocomplete",
            name: "🫶 Embedding Autocomplete Configuration",
            tooltip: "Configure autocomplete settings",
            category: ["kikotools", "🫶 Embedding Autocomplete Configuration"],
            defaultValue: null,
            type: () => createAutocompleteLauncher(autocompleteInstance, app.ui.settings, app.canvas.canvas)
        });

        // Override STRING widget creation
        if (!originalStringWidget) {
            originalStringWidget = ComfyWidgets.STRING;
        }

        const wrappedStringWidget = function(node, inputName, inputData, app) {
            const widget = originalStringWidget.apply(this, arguments);

            // Only attach to multiline text widgets (prompts)
            const entry = widget.widget || widget;
            if (inputData[1]?.multiline && entry.inputEl) {
                // Use requestAnimationFrame to ensure DOM is ready
                instance.nextFrame(() => instance.attachToWidget(entry, node));
            }

            return widget;
        };

        ComfyWidgets.STRING = wrappedStringWidget;
        instance.scope.cleanup(() => { if (ComfyWidgets.STRING === wrappedStringWidget) ComfyWidgets.STRING = originalStringWidget; });

        // Attach to existing multiline widgets
        const attachToExistingWidgets = () => {
            if (instance.scope.signal.aborted) return;

            app.graph._nodes.forEach(node => {
                if (node.widgets) {
                    node.widgets.forEach(widget => {
                        if (widget.inputEl && widget.inputEl.tagName === "TEXTAREA" && !instance.activeWidgets.has(widget)) {
                            instance.attachToWidget(widget, node);
                        }
                    });
                }
            });
        };

        // Wait for graph to be ready
        instance.nextFrame(() => instance.nextFrame(attachToExistingWidgets));

        // Re-attach when new nodes are added
        const originalAddNode = app.graph.add;
        const wrappedAddNode = function(...args) {
            const result = originalAddNode.apply(this, args);
            instance.nextFrame(attachToExistingWidgets);
            return result;
        };
        app.graph.add = wrappedAddNode;
        instance.scope.cleanup(() => { if (app.graph.add === wrappedAddNode) app.graph.add = originalAddNode; });
    },

    async beforeUnload() {
        // Clean up before page unload
        if (autocompleteInstance) {
            autocompleteInstance.cleanup();
        }
    }
});
