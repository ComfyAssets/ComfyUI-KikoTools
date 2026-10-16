import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";
import { createScope } from './ui/core.js';
import { createSuggestionView } from './ui/autocomplete-suggestions.js';
import { watchRendererTextareas } from './ui/text-widget-adapter.js';
import { createAutocompleteLauncher } from './views/autocomplete-settings.js';

// KikoEmbeddingAutocomplete - Provides autocomplete for embeddings and LoRAs in text widgets
class KikoEmbeddingAutocomplete {
    constructor() {
        this.scope = createScope();
        this.widgetCleanups = new Set();
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
        if (this.settings.customWordsUrl && this.settings.showCustomWords) {
            this.loadCustomWords(this.settings.customWordsUrl);
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
                signal: controller.signal
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

    async loadCustomWords(url) {
        if (!url) return 0;

        try {
            const response = await this.fetchWithAbort(url);
            if (!response || !response.ok) {
                throw new Error(`Failed to load custom words: ${response?.status || 'aborted'}`);
            }

            const text = await response.text();

            // Security validation - detect potentially dangerous patterns
            // Note: This is defense-in-depth for text files, not HTML rendering
            const dangerousPatterns = [
                // Script tags - catch all variations including bypass attempts with whitespace
                // Matches: <script>, <script >, <script src="x">, </script >, </script>, etc.
                /<\s*\/?script[^>]*>/gi,  // Script tags (opening/closing with any attributes/whitespace)
                // Other dangerous HTML tags
                /<\s*iframe[^>]*>/gi,
                /<\s*embed[^>]*>/gi,
                /<\s*object[^>]*>/gi,
                // JavaScript protocol and event handlers
                /javascript:/gi,
                /data:text\/html/gi,
                /\bon\w+\s*=/gi,  // Matches any event handler (onclick, onload, etc.)
                // Code execution patterns
                /import\s+/gi,
                /require\s*\(/gi,
                /eval\s*\(/gi,
                /new\s+Function\s*\(/gi,
                /\.innerHTML\s*=/gi,
                // DOM manipulation
                /document\./gi,
                /window\./gi,
                // Prototype pollution
                /__proto__/gi,
                /\.prototype\./gi,
                /\.constructor\s*\(/gi
            ];

            for (const pattern of dangerousPatterns) {
                if (pattern.test(text)) {
                    throw new Error("Security Warning: File contains potentially dangerous code patterns.");
                }
            }

            // Size check
            if (text.length > 10 * 1024 * 1024) {
                throw new Error("File too large. Maximum size is 10MB.");
            }

            const lines = text.split('\n');
            this.customWords = [];
            const maxLineLength = 500;

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed || trimmed.length > maxLineLength) continue;

                // Security check for individual lines
                if ((trimmed.includes('<script') || trimmed.includes('</script')) ||
                    (trimmed.includes('{') && trimmed.includes('}') && trimmed.includes('function')) ||
                    trimmed.includes('=>') ||
                    trimmed.includes('eval(') ||
                    trimmed.includes('document.') ||
                    trimmed.includes('window.')) {
                    continue;
                }

                const parts = trimmed.split(',');
                const word = parts[0].trim();
                const frequency = parts[1] ? parseInt(parts[1]) : 0;

                const safeWordPattern = /^[a-zA-Z0-9_\s\-:()'\.\!\?,\/\+\*&@#;=\[\]]+$/;
                if (word && safeWordPattern.test(word) && word.length > 0) {
                    this.customWords.push({
                        name: word,
                        fullPath: word,
                        type: "custom",
                        display: word,
                        value: word,
                        frequency: frequency
                    });
                }
            }

            // Sort by frequency and name
            this.customWords.sort((a, b) => {
                if (a.frequency !== b.frequency) {
                    return b.frequency - a.frequency;
                }
                return a.name.localeCompare(b.name);
            });

            return this.customWords.length;

        } catch (error) {
            console.error("[KikoTools] Error loading custom words:", error);
            return 0;
        }
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
                let replaceLength = widgetState.currentPrefix.length;

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
                    let wordStart = cursor - widgetState.currentPrefix.length;
                    while (wordStart > 0 && /[a-zA-Z0-9_-]/.test(text[wordStart - 1])) {
                        wordStart--;
                    }
                    widgetState.prefixStart = wordStart;
                    replaceLength = cursor - wordStart;
                }

                const before = text.substring(0, widgetState.prefixStart);
                const after = text.substring(widgetState.prefixStart + replaceLength);

                // Add comma if enabled
                let finalInsertText = insertText;
                if (this.settings.autoInsertComma && (suggestion.type === "custom" || suggestion.type === "embedding" || suggestion.type === "lora")) {
                    const trimmedAfter = after.trim();
                    const nextChar = trimmedAfter.charAt(0);

                    if (nextChar !== ',' && nextChar !== '.' && nextChar !== ';') {
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

                // Check for general word
                let start = cursor - 1;
                while (start >= 0 && /[a-zA-Z0-9_-]/.test(text[start])) {
                    start--;
                }
                start++;

                const word = text.substring(start, cursor);

                if (word.length >= this.settings.minChars) {
                    widgetState.currentPrefix = word.toLowerCase();
                    widgetState.prefixStart = start;

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
                        suggestions.push(...this.customWords.filter(w =>
                            w.name.toLowerCase().includes(prefix)
                        ));
                    }
                }

                // Sort suggestions
                suggestions.sort((a, b) => {
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
        for (const [owner, name] of [[widget, 'onRemoved'], [widget, 'onRemove'], [node, 'onRemoved']]) {
            const original = owner[name];
            const wrapped = function (...args) { cleanup(); return original?.apply(this, args); };
            owner[name] = wrapped;
            widgetScope.cleanup(() => { if (owner[name] === wrapped) owner[name] = original; });
        }
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
