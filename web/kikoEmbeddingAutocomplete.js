import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// KikoEmbeddingAutocomplete - Provides autocomplete for embeddings and LoRAs in text widgets
class KikoEmbeddingAutocomplete {
    constructor() {
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
        window.addEventListener('beforeunload', () => this.cleanup());
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    cleanup() {
        // Cancel all pending fetches
        this.pendingFetches.forEach(controller => {
            try {
                controller.abort();
            } catch (e) {
                // Ignore abort errors
            }
        });
        this.pendingFetches.clear();

        // Clean up suggestion container
        if (this.suggestionContainer && this.suggestionContainer.parentNode) {
            this.suggestionContainer.parentNode.removeChild(this.suggestionContainer);
            this.suggestionContainer = null;
        }

        // Note: WeakMap and WeakSet will automatically clean up when widgets are garbage collected
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
        } catch (error) {
            console.error("[KikoTools] Error saving autocomplete settings:", error);
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

        this.suggestionContainer = document.createElement("div");
        this.suggestionContainer.className = "kikotools-autocomplete-suggestions";
        this.suggestionContainer.style.cssText = `
            position: absolute;
            z-index: 10000;
            background: var(--comfy-menu-bg);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
            display: none;
            min-width: 200px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;
        document.body.appendChild(this.suggestionContainer);
    }

    attachToWidget(widget, node) {
        if (!widget.inputEl || this.activeWidgets.has(widget)) {
            return;
        }

        this.activeWidgets.add(widget);
        const textarea = widget.inputEl;

        // Create suggestion container if it doesn't exist
        if (!this.suggestionContainer) {
            this.createSuggestionContainer();
        }

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
                if (this.suggestionContainer) {
                    this.suggestionContainer.style.display = "none";
                    this.suggestionContainer.innerHTML = "";
                }
                widgetState.selectedIndex = -1;
                widgetState.currentSuggestions = [];
                this.currentWidget = null;
            },

            showSuggestions: (suggestions, x, y) => {
                if (!suggestions.length) {
                    handlers.hideSuggestions();
                    return;
                }

                if (!this.suggestionContainer) {
                    this.createSuggestionContainer();
                }

                this.currentWidget = widget;
                this.suggestionContainer.innerHTML = "";

                suggestions.forEach((item, index) => {
                    const div = document.createElement("div");
                    div.className = "kikotools-autocomplete-item";
                    div.style.cssText = `
                        padding: 5px 10px;
                        cursor: pointer;
                        color: var(--fg-color);
                        ${index === widgetState.selectedIndex ? "background: var(--comfy-input-bg);" : ""}
                    `;

                    // Add type indicator
                    const typeSpan = document.createElement("span");
                    let typeColor = "#2196F3";
                    let typeText = "[LORA]";

                    if (item.type === "embedding") {
                        typeColor = "#4CAF50";
                        typeText = "[EMB]";
                    } else if (item.type === "custom") {
                        typeColor = "#FFA500";
                        typeText = "[TAG]";
                    }

                    typeSpan.style.cssText = `
                        display: inline-block;
                        width: 60px;
                        color: ${typeColor};
                        font-size: 0.9em;
                    `;
                    typeSpan.textContent = typeText;

                    const nameSpan = document.createElement("span");
                    if (item.type === "embedding" && item.fullPath && item.fullPath.includes('/')) {
                        const parts = item.fullPath.split('/');
                        const dir = parts.slice(0, -1).join('/');
                        const file = parts[parts.length - 1];

                        const dirSpan = document.createElement("span");
                        dirSpan.style.cssText = "color: #888; font-size: 0.9em;";
                        dirSpan.textContent = dir + "/";

                        const fileSpan = document.createElement("span");
                        fileSpan.textContent = file;

                        nameSpan.appendChild(dirSpan);
                        nameSpan.appendChild(fileSpan);
                    } else {
                        nameSpan.textContent = item.name;
                    }

                    div.appendChild(typeSpan);
                    div.appendChild(nameSpan);

                    div.addEventListener("mouseenter", () => {
                        widgetState.selectedIndex = index;
                        handlers.updateSelection();
                    });

                    div.addEventListener("click", () => {
                        handlers.insertSuggestion(item);
                    });

                    this.suggestionContainer.appendChild(div);
                });

                // Position the suggestions
                const rect = textarea.getBoundingClientRect();
                this.suggestionContainer.style.left = Math.min(x, rect.right - 200) + "px";
                this.suggestionContainer.style.top = y + "px";
                this.suggestionContainer.style.display = "block";
            },

            updateSelection: () => {
                const items = this.suggestionContainer.querySelectorAll(".kikotools-autocomplete-item");
                items.forEach((item, index) => {
                    item.style.background = index === widgetState.selectedIndex ? "var(--comfy-input-bg)" : "";
                });

                // Auto-scroll to keep selected item visible
                if (widgetState.selectedIndex >= 0 && items[widgetState.selectedIndex]) {
                    const selectedItem = items[widgetState.selectedIndex];
                    const containerRect = this.suggestionContainer.getBoundingClientRect();
                    const itemRect = selectedItem.getBoundingClientRect();

                    if (itemRect.bottom > containerRect.bottom) {
                        this.suggestionContainer.scrollTop += itemRect.bottom - containerRect.bottom + 5;
                    } else if (itemRect.top < containerRect.top) {
                        this.suggestionContainer.scrollTop -= containerRect.top - itemRect.top + 5;
                    }
                }
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
                if (!this.settings.enabled) {
                    handlers.hideSuggestions();
                    return;
                }

                const triggerType = handlers.findPrefix();
                if (triggerType) {
                    widgetState.currentSuggestions = handlers.getSuggestions(widgetState.currentPrefix, triggerType);

                    if (widgetState.currentSuggestions.length > 0) {
                        const rect = textarea.getBoundingClientRect();
                        handlers.showSuggestions(widgetState.currentSuggestions, rect.left, rect.bottom);
                    } else {
                        handlers.hideSuggestions();
                    }
                } else {
                    handlers.hideSuggestions();
                }
            },

            onKeydown: (e) => {
                if (!this.suggestionContainer || this.suggestionContainer.style.display === "none" || this.currentWidget !== widget) {
                    return;
                }

                if (e.key === "ArrowDown") {
                    e.preventDefault();
                    widgetState.selectedIndex = Math.min(widgetState.selectedIndex + 1, widgetState.currentSuggestions.length - 1);
                    handlers.updateSelection();
                } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    widgetState.selectedIndex = Math.max(widgetState.selectedIndex - 1, 0);
                    handlers.updateSelection();
                } else if ((e.key === "Enter" && this.settings.insertOnEnter) ||
                           (e.key === "Tab" && this.settings.insertOnTab)) {
                    if (widgetState.selectedIndex >= 0 && widgetState.selectedIndex < widgetState.currentSuggestions.length) {
                        e.preventDefault();
                        handlers.insertSuggestion(widgetState.currentSuggestions[widgetState.selectedIndex]);
                    }
                } else if (e.key === "Escape") {
                    e.preventDefault();
                    handlers.hideSuggestions();
                }
            },

            onBlur: () => {
                // Use requestAnimationFrame to allow click events to fire first
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        if (this.currentWidget === widget) {
                            handlers.hideSuggestions();
                        }
                    });
                });
            },

            onScroll: () => {
                // Hide suggestions when scrolling
                if (this.currentWidget === widget) {
                    handlers.hideSuggestions();
                }
            }
        };

        // Add event listeners
        textarea.addEventListener("input", handlers.onInput);
        textarea.addEventListener("keydown", handlers.onKeydown);
        textarea.addEventListener("blur", handlers.onBlur);
        textarea.addEventListener("scroll", handlers.onScroll);

        // Store cleanup function
        const cleanup = () => {
            textarea.removeEventListener("input", handlers.onInput);
            textarea.removeEventListener("keydown", handlers.onKeydown);
            textarea.removeEventListener("blur", handlers.onBlur);
            textarea.removeEventListener("scroll", handlers.onScroll);
            handlers.hideSuggestions();
            this.activeWidgets.delete(widget);
            this.widgetCleanupMap.delete(widget);
        };

        this.widgetCleanupMap.set(widget, cleanup);

        // Handle widget removal
        if (widget.onRemoved) {
            const originalOnRemoved = widget.onRemoved;
            widget.onRemoved = () => {
                cleanup();
                originalOnRemoved.call(widget);
            };
        } else {
            widget.onRemoved = cleanup;
        }
    }

    detachFromWidget(widget) {
        const cleanup = this.widgetCleanupMap.get(widget);
        if (cleanup) {
            cleanup();
        }
    }
}

// Settings Dialog
class KikoEmbeddingAutocompleteDialog {
    constructor(autocompleteInstance) {
        this.autocomplete = autocompleteInstance;
        this.element = null;
    }

    createDialog() {
        // Create dialog backdrop
        const backdrop = document.createElement("div");
        backdrop.className = "kiko-dialog-backdrop";
        backdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 99998;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        // Create dialog container
        const dialog = document.createElement("div");
        dialog.className = "kiko-dialog";
        dialog.style.cssText = `
            background: var(--comfy-menu-bg, #202020);
            border: 1px solid var(--border-color, #4e4e4e);
            border-radius: 8px;
            width: 600px;
            max-width: 90vw;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            color: var(--fg-color, #ffffff);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        `;

        // Header
        const header = document.createElement("div");
        header.style.cssText = `
            padding: 20px;
            border-bottom: 1px solid var(--border-color, #4e4e4e);
            display: flex;
            align-items: center;
            justify-content: space-between;
        `;

        const title = document.createElement("h2");
        title.textContent = "🫶 Embedding Autocomplete Settings";
        title.style.cssText = `
            margin: 0;
            font-size: 20px;
            font-weight: 600;
            color: var(--fg-color, #ffffff);
        `;

        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "✕";
        closeBtn.style.cssText = `
            background: transparent;
            border: none;
            color: var(--fg-color, #ffffff);
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0.7;
            transition: opacity 0.2s;
        `;
        closeBtn.onmouseover = () => closeBtn.style.opacity = "1";
        closeBtn.onmouseout = () => closeBtn.style.opacity = "0.7";

        header.appendChild(title);
        header.appendChild(closeBtn);

        // Content
        const content = document.createElement("div");
        content.style.cssText = `
            padding: 20px;
            overflow-y: auto;
            flex: 1;
        `;

        // Create settings sections (simplified for brevity - same as original)
        content.innerHTML = `
            <div class="kiko-settings-section">
                <h3 style="margin-top: 0; margin-bottom: 15px; font-size: 16px; font-weight: 600;">General Settings</h3>

                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="kiko-enabled" style="margin-right: 10px;">
                        <span>Enable Autocomplete</span>
                    </label>
                </div>

                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="kiko-show-embeddings" style="margin-right: 10px;">
                        <span>Show Embeddings</span>
                    </label>
                </div>

                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="kiko-show-loras" style="margin-right: 10px;">
                        <span>Show LoRAs</span>
                    </label>
                </div>

                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="kiko-show-custom" style="margin-right: 10px;">
                        <span>Show Custom Words</span>
                    </label>
                </div>
            </div>
        `;

        // Footer
        const footer = document.createElement("div");
        footer.style.cssText = `
            padding: 15px 20px;
            border-top: 1px solid var(--border-color, #4e4e4e);
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        `;

        const saveBtn = document.createElement("button");
        saveBtn.textContent = "Save Settings";
        saveBtn.style.cssText = `
            padding: 8px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.2s;
        `;
        saveBtn.onmouseover = () => saveBtn.style.background = "#45a049";
        saveBtn.onmouseout = () => saveBtn.style.background = "#4CAF50";

        const cancelBtn = document.createElement("button");
        cancelBtn.textContent = "Cancel";
        cancelBtn.style.cssText = `
            padding: 8px 20px;
            background: var(--comfy-input-bg, #1a1a1a);
            color: var(--fg-color, #ffffff);
            border: 1px solid var(--border-color, #4e4e4e);
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        `;

        footer.appendChild(cancelBtn);
        footer.appendChild(saveBtn);

        // Assemble dialog
        dialog.appendChild(header);
        dialog.appendChild(content);
        dialog.appendChild(footer);
        backdrop.appendChild(dialog);

        // Event handlers
        closeBtn.onclick = () => this.close();
        cancelBtn.onclick = () => this.close();
        backdrop.onclick = (e) => {
            if (e.target === backdrop) this.close();
        };

        saveBtn.onclick = () => this.save();

        this.element = backdrop;
        this.dialog = dialog;

        return backdrop;
    }

    loadSettings() {
        if (!this.autocomplete) return;

        const settings = this.autocomplete.settings;

        // Set values (simplified for brevity)
        const elements = {
            enabled: document.getElementById("kiko-enabled"),
            showEmbeddings: document.getElementById("kiko-show-embeddings"),
            showLoras: document.getElementById("kiko-show-loras"),
            showCustom: document.getElementById("kiko-show-custom")
        };

        if (elements.enabled) elements.enabled.checked = settings.enabled !== false;
        if (elements.showEmbeddings) elements.showEmbeddings.checked = settings.showEmbeddings !== false;
        if (elements.showLoras) elements.showLoras.checked = settings.showLoras !== false;
        if (elements.showCustom) elements.showCustom.checked = settings.showCustomWords !== false;
    }

    save() {
        if (!this.autocomplete) return;

        // Gather settings
        const newSettings = {
            ...this.autocomplete.settings,
            enabled: document.getElementById("kiko-enabled").checked,
            showEmbeddings: document.getElementById("kiko-show-embeddings").checked,
            showLoras: document.getElementById("kiko-show-loras").checked,
            showCustomWords: document.getElementById("kiko-show-custom").checked
        };

        // Update autocomplete settings
        Object.assign(this.autocomplete.settings, newSettings);
        this.autocomplete.saveSettings();

        // Refresh resources if needed
        if (newSettings.showEmbeddings || newSettings.showLoras) {
            this.autocomplete.fetchResourcesDebounced();
        }

        // Close dialog
        this.close();
    }

    show() {
        if (!this.element) {
            this.createDialog();
        }
        document.body.appendChild(this.element);

        // Load settings after adding to DOM
        setTimeout(() => this.loadSettings(), 10);
    }

    close() {
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
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
            type: () => {
                const tr = document.createElement("tr");
                tr.className = "kikotools-settings-row";

                const tdLabel = document.createElement("td");
                tdLabel.innerHTML = `<div style="display: flex; align-items: center;">
                    <span style="font-size: 20px; margin-right: 8px;">🫶</span>
                    <span>Embedding Autocomplete Configuration</span>
                </div>`;

                const tdButton = document.createElement("td");
                const button = document.createElement("button");
                button.textContent = "Open Settings";
                button.className = "kiko-settings-button";
                button.style.cssText = `
                    padding: 8px 20px;
                    background: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 500;
                    transition: background 0.2s;
                `;
                button.onmouseover = () => button.style.background = "#45a049";
                button.onmouseout = () => button.style.background = "#4CAF50";
                button.onclick = () => {
                    const dialog = new KikoEmbeddingAutocompleteDialog(autocompleteInstance);
                    dialog.show();
                };

                tdButton.appendChild(button);
                tr.appendChild(tdLabel);
                tr.appendChild(tdButton);

                return tr;
            }
        });

        // Override STRING widget creation
        if (!originalStringWidget) {
            originalStringWidget = ComfyWidgets.STRING;
        }

        ComfyWidgets.STRING = function(node, inputName, inputData, app) {
            const widget = originalStringWidget.apply(this, arguments);

            // Only attach to multiline text widgets (prompts)
            if (inputData[1]?.multiline && widget.inputEl) {
                // Use requestAnimationFrame to ensure DOM is ready
                requestAnimationFrame(() => {
                    if (autocompleteInstance) {
                        autocompleteInstance.attachToWidget(widget, node);
                    }
                });
            }

            return widget;
        };

        // Attach to existing multiline widgets
        const attachToExistingWidgets = () => {
            if (!autocompleteInstance) return;

            app.graph._nodes.forEach(node => {
                if (node.widgets) {
                    node.widgets.forEach(widget => {
                        if (widget.inputEl && widget.inputEl.tagName === "TEXTAREA" && !autocompleteInstance.activeWidgets.has(widget)) {
                            autocompleteInstance.attachToWidget(widget, node);
                        }
                    });
                }
            });
        };

        // Wait for graph to be ready
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                attachToExistingWidgets();
            });
        });

        // Re-attach when new nodes are added
        const originalAddNode = app.graph.add;
        app.graph.add = function(...args) {
            const result = originalAddNode.apply(this, args);
            requestAnimationFrame(() => attachToExistingWidgets());
            return result;
        };
    },

    async beforeUnload() {
        // Clean up before page unload
        if (autocompleteInstance) {
            autocompleteInstance.cleanup();
        }
    }
});
