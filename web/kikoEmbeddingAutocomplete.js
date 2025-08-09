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
        
        // Fetch available embeddings and LoRAs
        this.fetchResources();
        
        // Load custom words if URL is set
        if (this.settings.customWordsUrl && this.settings.showCustomWords) {
            this.loadCustomWords(this.settings.customWordsUrl);
        }
        
        // Track active widgets
        this.activeWidgets = new Set();
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
    
    async fetchResources() {
        try {
            // Fetch embeddings - try our custom endpoint first, then ComfyUI's API
            if (this.settings.showEmbeddings) {
                
                // Always use our custom endpoint that preserves paths
                let useCustomEndpoint = true;
                try {
                    const response = await fetch("/kikotools/autocomplete/embeddings");
                    
                    if (response.ok) {
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
                        
                        useCustomEndpoint = false; // Success, don't use fallback
                    }
                } catch (customError) {
                    // Custom endpoint not available, will use fallback
                }
                
                // Only fallback if custom endpoint failed
                if (useCustomEndpoint) {
                    try {
                        const embeddingsResponse = await api.getEmbeddings();
                        
                        let allEmbeddings = [];
                        
                        // Check if this is a paginated response
                        if (embeddingsResponse && embeddingsResponse.items && Array.isArray(embeddingsResponse.items)) {
                            // This is a paginated response - get all pages
                            const totalPages = embeddingsResponse.total_pages || 1;
                            
                            // Add items from first page
                            allEmbeddings = [...embeddingsResponse.items];
                            
                            // Fetch remaining pages if any
                            if (totalPages > 1) {
                                // Check if api.getEmbeddings accepts page parameter
                                for (let page = 2; page <= totalPages; page++) {
                                    try {
                                        
                                        // Try using the api method with page parameter
                                        const pageData = await api.getEmbeddings(page);
                                        if (pageData && pageData.items) {
                                            allEmbeddings.push(...pageData.items);
                                        } else {
                                            break;
                                        }
                                    } catch (err) {
                                        // If pagination doesn't work, just use what we have
                                        break;
                                    }
                                }
                            }
                            
                            // Process the embeddings
                            this.embeddings = allEmbeddings.map((item, index) => {
                                let fullPath = "";
                                
                                // Extract name from different possible formats
                                if (typeof item === 'string') {
                                    fullPath = item;
                                } else if (item && typeof item === 'object') {
                                    // Based on the logs, items have file_name and model_name properties
                                    fullPath = item.file_name || item.model_name || item.name || item.filename;
                                }
                                
                                // Clean up the path - remove file extensions but keep directory structure
                                const cleanPath = String(fullPath || "").replace(/\.(pt|safetensors|ckpt|bin)$/i, '');
                                
                                // Extract just the filename (without path) for display/search purposes
                                const nameOnly = cleanPath.split('/').pop() || cleanPath;
                                
                                // Only include if we have a valid name
                                if (cleanPath && cleanPath !== "undefined") {
                                    return {
                                        name: nameOnly,  // Just the name for searching
                                        fullPath: cleanPath,  // Full path including subdirectory
                                        type: "embedding",
                                        display: `embedding:${cleanPath}`,  // Show full path in display
                                        value: `embedding:${cleanPath}`  // Use full path in value
                                    };
                                }
                                return null;
                            }).filter(item => item !== null); // Remove any null entries
                        }
                        // Check if it's a simple object with embedding names as keys (old format)
                        else if (embeddingsResponse && typeof embeddingsResponse === 'object' && !Array.isArray(embeddingsResponse)) {
                            // Try to extract embeddings from object keys
                            const keys = Object.keys(embeddingsResponse);
                            
                            // If the object has standard pagination keys, it's not the embeddings object
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
                            } else {
                                this.embeddings = [];
                            }
                        } else {
                            this.embeddings = [];
                        }
                    } catch (e) {
                        this.embeddings = [];
                    }
                }
            }
            
            // Fetch LoRAs - try multiple methods
            if (this.settings.showLoras) {
                
                // Method 1: Try our custom endpoint
                try {
                    const response = await fetch("/kikotools/autocomplete/loras");
                    if (response.ok) {
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
                    } else {
                        throw new Error("Custom endpoint not available");
                    }
                } catch (e) {
                    
                    // Method 2: Try using the object list API
                    try {
                        const response = await fetch("/object_info");
                        if (response.ok) {
                            const objectInfo = await response.json();
                            // Look for LoraLoader node to get available loras
                            if (objectInfo.LoraLoader?.input?.required?.lora_name?.[0]) {
                                const loraNames = objectInfo.LoraLoader.input.required.lora_name[0];
                                this.loras = loraNames.map(name => {
                                    const cleanName = name.replace(/\.(pt|safetensors|ckpt|bin)$/i, '');
                                    return {
                                        name: cleanName,
                                        type: "lora",
                                        display: `<lora:${cleanName}:1.0>`,
                                        value: `<lora:${cleanName}:1.0>`
                                    };
                                });
                            }
                        }
                    } catch (e2) {
                        this.loras = [];
                    }
                }
            }
            
            // Store reference for debugging if needed
            window.kikoDebug = {
                embeddings: this.embeddings,
                loras: this.loras,
                customWords: this.customWords,
                autocomplete: this
            };
            
        } catch (error) {
            // Silent fail - resources will be empty
        }
    }
    
    async loadCustomWords(url) {
        if (!url) return;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to load custom words: ${response.status}`);
            }
            
            const text = await response.text();
            
            // Security check: Validate content is safe plain text
            // Check for potential script injections or executable code
            const dangerousPatterns = [
                /<script[\s\S]*?<\/script>/gi,  // HTML script tags
                /<iframe[\s\S]*?>/gi,            // iframes
                /javascript:/gi,                 // javascript: protocol
                /\bon(click|load|error|mouseover|mouseout|focus|blur|change|submit)\s*=/gi,  // Specific event handlers only
                /<embed[\s\S]*?>/gi,             // embed tags
                /<object[\s\S]*?>/gi,            // object tags
                /import\s+[\s\S]*?from/gi,       // ES6 imports
                /require\s*\(/gi,                // CommonJS requires
                /eval\s*\(/gi,                   // eval statements
                /new\s+Function\s*\(/gi,         // Function constructor
                /\.innerHTML\s*=/gi,             // innerHTML assignments
                /document\.\w+/gi,               // document manipulation
                /window\.\w+/gi,                 // window manipulation
                /(__proto__|\.prototype\.|\.constructor\s*\()/gi  // Prototype pollution attempts - more specific
            ];
            
            for (const pattern of dangerousPatterns) {
                if (pattern.test(text)) {
                    throw new Error("Security Warning: File contains potentially dangerous code patterns. Only plain text files with words/tags are allowed.");
                }
            }
            
            // Additional check: File should not be too large (limit to 10MB)
            if (text.length > 10 * 1024 * 1024) {
                throw new Error("File too large. Maximum size is 10MB.");
            }
            
            const lines = text.split('\n');
            
            // Parse custom words - format is typically "word,frequency" or just "word"
            this.customWords = [];
            let invalidLines = 0;
            let validLines = 0;
            const maxLineLength = 500; // Reasonable max length for a word/tag
            
            
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;
                
                // Skip lines that are too long (likely not valid words)
                if (trimmed.length > maxLineLength) {
                    invalidLines++;
                    continue;
                }
                
                // Check for suspicious patterns in individual lines
                // Be more lenient - only check for actual code patterns, not simple brackets
                if ((trimmed.includes('<script') || trimmed.includes('</script')) ||
                    (trimmed.includes('{') && trimmed.includes('}') && trimmed.includes('function')) ||
                    trimmed.includes('=>') || 
                    trimmed.includes('eval(') ||
                    trimmed.includes('document.') ||
                    trimmed.includes('window.')) {
                    invalidLines++;
                    continue;
                }
                
                // Split by comma to handle frequency data if present
                const parts = trimmed.split(',');
                const word = parts[0].trim();
                const frequency = parts[1] ? parseInt(parts[1]) : 0;
                
                // Validate word contains only safe characters
                // Allow alphanumeric (including starting with numbers), spaces, underscores, hyphens, and common punctuation
                // Also allow Japanese characters and other unicode letters for international tags
                // Include semicolons, equals, brackets for tags like "steins;gate" or special formatting
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
                    validLines++;
                } else if (word) {
                    invalidLines++;
                }
            }
            
            // Skip warning for invalid lines
            
            // Sort by frequency if available, otherwise alphabetically
            this.customWords.sort((a, b) => {
                if (a.frequency !== b.frequency) {
                    return b.frequency - a.frequency; // Higher frequency first
                }
                return a.name.localeCompare(b.name);
            });
            
            
            // Store in debug info
            if (window.kikoDebug) {
                window.kikoDebug.customWords = this.customWords;
            }
            
            // Return count for notification
            return this.customWords.length;
            
        } catch (error) {
            return 0;
        }
    }
    
    attachToWidget(widget, node) {
        if (!widget.inputEl || this.activeWidgets.has(widget)) {
            return;
        }
        this.activeWidgets.add(widget);
        const textarea = widget.inputEl;
        
        // Create suggestion container
        const suggestionContainer = document.createElement("div");
        suggestionContainer.className = "kikotools-autocomplete-suggestions";
        suggestionContainer.style.cssText = `
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
        document.body.appendChild(suggestionContainer);
        
        let currentSuggestions = [];
        let selectedIndex = -1;
        let currentPrefix = "";
        let prefixStart = -1;
        
        const hideSuggestions = () => {
            suggestionContainer.style.display = "none";
            suggestionContainer.innerHTML = ""; // Clear content to prevent artifacts
            selectedIndex = -1;
            currentSuggestions = [];
        };
        
        const showSuggestions = (suggestions, x, y) => {
            if (!suggestions.length) {
                hideSuggestions();
                return;
            }
            
            suggestionContainer.innerHTML = "";
            suggestions.forEach((item, index) => {
                const div = document.createElement("div");
                div.className = "kikotools-autocomplete-item";
                div.style.cssText = `
                    padding: 5px 10px;
                    cursor: pointer;
                    color: var(--fg-color);
                    ${index === selectedIndex ? "background: var(--comfy-input-bg);" : ""}
                `;
                
                // Add type indicator
                const typeSpan = document.createElement("span");
                let typeColor = "#2196F3"; // Default for LORA
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
                // For embeddings with paths, show the full path structure
                if (item.type === "embedding" && item.fullPath && item.fullPath.includes('/')) {
                    // Show subdirectory in gray, filename in normal color
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
                    selectedIndex = index;
                    updateSelection();
                });
                
                div.addEventListener("click", () => {
                    insertSuggestion(item);
                });
                
                suggestionContainer.appendChild(div);
            });
            
            // Position the suggestions
            const rect = textarea.getBoundingClientRect();
            suggestionContainer.style.left = Math.min(x, rect.right - 200) + "px";
            suggestionContainer.style.top = y + "px";
            suggestionContainer.style.display = "block";
        };
        
        const updateSelection = () => {
            const items = suggestionContainer.querySelectorAll(".kikotools-autocomplete-item");
            items.forEach((item, index) => {
                item.style.background = index === selectedIndex ? "var(--comfy-input-bg)" : "";
            });
            
            // Auto-scroll to keep selected item visible
            if (selectedIndex >= 0 && items[selectedIndex]) {
                const selectedItem = items[selectedIndex];
                const containerRect = suggestionContainer.getBoundingClientRect();
                const itemRect = selectedItem.getBoundingClientRect();
                
                // Check if item is below visible area
                if (itemRect.bottom > containerRect.bottom) {
                    // Scroll down to show the item
                    suggestionContainer.scrollTop += itemRect.bottom - containerRect.bottom + 5;
                }
                // Check if item is above visible area
                else if (itemRect.top < containerRect.top) {
                    // Scroll up to show the item
                    suggestionContainer.scrollTop -= containerRect.top - itemRect.top + 5;
                }
            }
        };
        
        const insertSuggestion = (suggestion) => {
            const text = textarea.value;
            const cursor = textarea.selectionStart;
            const textBefore = text.substring(0, cursor);
            
            // Determine what to insert based on context
            let insertText = "";
            let replaceLength = currentPrefix.length;
            
            // Apply replace underscores setting for custom words
            if (suggestion.type === "custom" && this.settings.replaceUnderscores) {
                // Create a modified suggestion with underscores replaced
                suggestion = {
                    ...suggestion,
                    name: suggestion.name.replace(/_/g, ' '),
                    value: suggestion.value.replace(/_/g, ' '),
                    display: suggestion.display.replace(/_/g, ' ')
                };
            }
            
            // Check if we're completing an embedding after the trigger
            const embTrigger = this.settings.embeddingTrigger || "embedding:";
            const embRegex = new RegExp(embTrigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + "([a-zA-Z0-9_\\/-]*)$");
            
            if (textBefore.match(embRegex) || (embTrigger === "embedding:" && textBefore.match(/embeddings:([a-zA-Z0-9_\/-]*)$/))) {
                // For embeddings, use the full path (including subdirectory)
                insertText = suggestion.fullPath || suggestion.name;  // Use full path if available
            }
            // Check if we're completing a lora
            else if (suggestion.type === "lora") {
                const loraTrigger = this.settings.loraTrigger || "<lora:";
                const escapedTrigger = loraTrigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const loraRegex = new RegExp(escapedTrigger + "([a-zA-Z0-9_\\s\\/-]*)$");
                
                if (textBefore.match(loraRegex)) {
                    // Complete the lora name and add the closing
                    insertText = (suggestion.fullPath || suggestion.name) + ":1.0>";
                } else {
                    // Insert full lora syntax
                    insertText = suggestion.value || suggestion.display;
                }
            }
            // Check if we're replacing a word that starts with "em" (embedding autocomplete)
            else if (currentPrefix && textBefore.match(/\b(em|emb|embe|embed|embeddi|embeddin|embedding)$/i)) {
                // User typed a partial "embedding" word, replace it with the full embedding syntax
                const match = textBefore.match(/\b(em|emb|embe|embed|embeddi|embeddin|embedding)$/i);
                insertText = suggestion.value || suggestion.display;
                prefixStart = cursor - match[1].length;
                replaceLength = match[1].length;
            }
            // General insertion
            else {
                insertText = suggestion.value || suggestion.display;
                // For general insertion, replace the whole word
                let wordStart = cursor - currentPrefix.length;
                while (wordStart > 0 && /[a-zA-Z0-9_-]/.test(text[wordStart - 1])) {
                    wordStart--;
                }
                prefixStart = wordStart;
                replaceLength = cursor - wordStart;
            }
            
            const before = text.substring(0, prefixStart);
            const after = text.substring(prefixStart + replaceLength);
            
            // Add comma if auto-insert comma is enabled and appropriate
            let finalInsertText = insertText;
            if (this.settings.autoInsertComma && (suggestion.type === "custom" || suggestion.type === "embedding" || suggestion.type === "lora")) {
                // Check if we should add a comma
                // Add comma if: not already followed by comma, and either at end of text or followed by non-empty content
                const trimmedAfter = after.trim();
                const nextChar = trimmedAfter.charAt(0);
                
                // Add comma unless already followed by comma or punctuation
                if (nextChar !== ',' && nextChar !== '.' && nextChar !== ';') {
                    // Add comma and space
                    finalInsertText += ', ';
                }
            }
            
            textarea.value = before + finalInsertText + after;
            textarea.selectionStart = textarea.selectionEnd = prefixStart + finalInsertText.length;
            
            hideSuggestions();
            
            // Trigger change event
            const event = new Event("input", { bubbles: true });
            textarea.dispatchEvent(event);
        };
        
        const findPrefix = () => {
            const text = textarea.value;
            const cursor = textarea.selectionStart;
            const textBefore = text.substring(0, cursor);
            
            
            // Check for custom embedding trigger
            const embTrigger = this.settings.embeddingTrigger || "embedding:";
            const embRegex = new RegExp(embTrigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + "([a-zA-Z0-9_\\/-]*)$");
            const embeddingMatch = textBefore.match(embRegex);
            if (embeddingMatch) {
                currentPrefix = embeddingMatch[1].toLowerCase();
                prefixStart = cursor - embeddingMatch[1].length;
                return "embedding";
            }
            
            // Also check for "embeddings:" (plural) if default trigger
            if (embTrigger === "embedding:") {
                const pluralMatch = textBefore.match(/embeddings:([a-zA-Z0-9_\/-]*)$/);
                if (pluralMatch) {
                    currentPrefix = pluralMatch[1].toLowerCase();
                    prefixStart = cursor - pluralMatch[1].length;
                    return "embedding";
                }
            }
            
            // Check for custom LoRA trigger
            const loraTrigger = this.settings.loraTrigger || "<lora:";
            const escapedTrigger = loraTrigger.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const loraRegex = new RegExp(escapedTrigger + "([a-zA-Z0-9_\\s\\/-]*)$");
            const loraMatch = textBefore.match(loraRegex);
            if (loraMatch) {
                currentPrefix = loraMatch[1].toLowerCase();
                prefixStart = cursor - loraMatch[1].length;
                return "lora";
            }
            
            // Check for general word that might match embeddings or loras
            let start = cursor - 1;
            while (start >= 0 && /[a-zA-Z0-9_-]/.test(text[start])) {
                start--;
            }
            start++;
            
            const word = text.substring(start, cursor);
            
            // Check if we should show suggestions
            if (word.length >= this.settings.minChars) {
                currentPrefix = word.toLowerCase();
                prefixStart = start;
                
                // Check for quick trigger (e.g., "em" for embeddings)
                const quickTrigger = this.settings.quickTrigger;
                if (quickTrigger && word.toLowerCase().startsWith(quickTrigger.toLowerCase())) {
                    return "embedding-word";
                }
                
                // For other words, show general matches
                return "general";
            }
            
            return false;
        };
        
        const getSuggestions = (prefix, type) => {
            const suggestions = [];
            
            // If type is embedding (after "embedding:"), only show embeddings
            if (type === "embedding" && this.settings.showEmbeddings) {
                suggestions.push(...this.embeddings.filter(e => 
                    prefix === "" || e.name.toLowerCase().includes(prefix) || (e.fullPath && e.fullPath.toLowerCase().includes(prefix))
                ));
            }
            // If type is embedding-word (user typed "em", "emb", etc), ONLY show embeddings
            else if (type === "embedding-word" && this.settings.showEmbeddings) {
                // When user types "em", "emb", "embe", etc. we want to show ALL embeddings
                // because they're trying to trigger the embedding autocomplete
                suggestions.push(...this.embeddings);
            }
            // If type is lora, only show loras
            else if (type === "lora" && this.settings.showLoras) {
                suggestions.push(...this.loras.filter(l => 
                    prefix === "" || l.name.toLowerCase().includes(prefix)
                ));
            }
            // For general matching, show embeddings, loras, and custom words
            else if (type === "general") {
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
            
            // Sort suggestions - prioritize exact matches and starts-with matches
            suggestions.sort((a, b) => {
                const aName = a.name.toLowerCase();
                const bName = b.name.toLowerCase();
                const aPath = (a.fullPath || a.name).toLowerCase();
                const bPath = (b.fullPath || b.name).toLowerCase();
                
                // Exact match on name
                if (aName === prefix) return -1;
                if (bName === prefix) return 1;
                
                // Exact match on full path
                if (aPath === prefix) return -1;
                if (bPath === prefix) return 1;
                
                // Starts with on name
                if (aName.startsWith(prefix) && !bName.startsWith(prefix)) return -1;
                if (!aName.startsWith(prefix) && bName.startsWith(prefix)) return 1;
                
                // Starts with on path
                if (aPath.startsWith(prefix) && !bPath.startsWith(prefix)) return -1;
                if (!aPath.startsWith(prefix) && bPath.startsWith(prefix)) return 1;
                
                // Group by directory if enabled
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
        };
        
        // Event handlers
        textarea.addEventListener("input", (e) => {
            if (!this.settings.enabled) {
                hideSuggestions();
                return;
            }
            
            const triggerType = findPrefix();
            if (triggerType) {
                currentSuggestions = getSuggestions(currentPrefix, triggerType);
                
                if (currentSuggestions.length > 0) {
                    // Get cursor position for suggestion placement
                    const rect = textarea.getBoundingClientRect();
                    const lineHeight = parseInt(window.getComputedStyle(textarea).lineHeight);
                    
                    // Simple positioning below cursor
                    showSuggestions(currentSuggestions, rect.left, rect.bottom);
                } else {
                    hideSuggestions();
                }
            } else {
                hideSuggestions();
            }
        });
        
        textarea.addEventListener("keydown", (e) => {
            if (suggestionContainer.style.display === "none") {
                return;
            }
            
            if (e.key === "ArrowDown") {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, currentSuggestions.length - 1);
                updateSelection();
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                updateSelection();
            } else if ((e.key === "Enter" && this.settings.insertOnEnter) || 
                       (e.key === "Tab" && this.settings.insertOnTab)) {
                if (selectedIndex >= 0 && selectedIndex < currentSuggestions.length) {
                    e.preventDefault();
                    insertSuggestion(currentSuggestions[selectedIndex]);
                }
            } else if (e.key === "Escape") {
                e.preventDefault();
                hideSuggestions();
            }
        });
        
        textarea.addEventListener("blur", () => {
            setTimeout(hideSuggestions, 200);
        });
        
        // Cleanup on widget destruction
        if (widget.onRemoved) {
            const originalOnRemoved = widget.onRemoved;
            widget.onRemoved = () => {
                hideSuggestions();
                if (suggestionContainer && suggestionContainer.parentNode) {
                    suggestionContainer.parentNode.removeChild(suggestionContainer);
                }
                this.activeWidgets.delete(widget);
                originalOnRemoved.call(widget);
            };
        } else {
            widget.onRemoved = () => {
                hideSuggestions();
                if (suggestionContainer && suggestionContainer.parentNode) {
                    suggestionContainer.parentNode.removeChild(suggestionContainer);
                }
                this.activeWidgets.delete(widget);
            };
        }
    }
}

// Settings Dialog - Clean, modern interface
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
        
        // Create settings sections
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
                
                <div class="kiko-setting-row" style="margin-bottom: 20px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="kiko-group-by-dir" style="margin-right: 10px;">
                        <span>Group by Directory</span>
                    </label>
                </div>
            </div>
            
            <div class="kiko-settings-section">
                <h3 style="margin-bottom: 15px; font-size: 16px; font-weight: 600;">Trigger Settings</h3>
                
                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-size: 14px;">Embedding Trigger</label>
                    <input type="text" id="kiko-embedding-trigger" placeholder="e.g., embedding:" style="
                        width: 100%;
                        padding: 8px 12px;
                        background: var(--comfy-input-bg, #1a1a1a);
                        border: 1px solid var(--border-color, #4e4e4e);
                        border-radius: 4px;
                        color: var(--fg-color, #ffffff);
                        font-size: 14px;
                    ">
                    <small style="color: #888; font-size: 12px; margin-top: 4px; display: block;">
                        Text that triggers embedding autocomplete (e.g., "embedding:", "emb:", "e:")
                    </small>
                </div>
                
                <div class="kiko-setting-row" style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-size: 14px;">LoRA Trigger</label>
                    <input type="text" id="kiko-lora-trigger" placeholder="e.g., <lora:" style="
                        width: 100%;
                        padding: 8px 12px;
                        background: var(--comfy-input-bg, #1a1a1a);
                        border: 1px solid var(--border-color, #4e4e4e);
                        border-radius: 4px;
                        color: var(--fg-color, #ffffff);
                        font-size: 14px;
                    ">
                    <small style="color: #888; font-size: 12px; margin-top: 4px; display: block;">
                        Text that triggers LoRA autocomplete (e.g., "&lt;lora:", "lora:", "l:")
                    </small>
                </div>
            </div>
            
            <div class="kiko-settings-section">
                <h3 style="margin-bottom: 15px; font-size: 16px; font-weight: 600;">Display Settings</h3>
                
                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-size: 14px;">Maximum Suggestions</label>
                    <input type="number" id="kiko-max-suggestions" min="5" max="100" step="5" style="
                        width: 120px;
                        padding: 8px 12px;
                        background: var(--comfy-input-bg, #1a1a1a);
                        border: 1px solid var(--border-color, #4e4e4e);
                        border-radius: 4px;
                        color: var(--fg-color, #ffffff);
                        font-size: 14px;
                    ">
                    <small style="color: #888; font-size: 12px; margin-top: 4px; display: block;">
                        Number of suggestions to show (5-100)
                    </small>
                </div>
                
                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-size: 14px;">Minimum Characters to Trigger</label>
                    <input type="number" id="kiko-min-chars" min="1" max="10" step="1" style="
                        width: 120px;
                        padding: 8px 12px;
                        background: var(--comfy-input-bg, #1a1a1a);
                        border: 1px solid var(--border-color, #4e4e4e);
                        border-radius: 4px;
                        color: var(--fg-color, #ffffff);
                        font-size: 14px;
                    ">
                    <small style="color: #888; font-size: 12px; margin-top: 4px; display: block;">
                        Minimum characters before showing suggestions (1-10)
                    </small>
                </div>
            </div>
            
            <div class="kiko-settings-section">
                <h3 style="margin-bottom: 15px; font-size: 16px; font-weight: 600;">Insertion Settings</h3>
                
                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="kiko-auto-comma" style="margin-right: 10px;">
                        <span>Auto-insert comma after completion</span>
                    </label>
                </div>
                
                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="kiko-replace-underscores" style="margin-right: 10px;">
                        <span>Replace underscores with spaces</span>
                    </label>
                </div>
                
                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 10px; font-size: 14px;">Insert suggestion on:</label>
                    <div style="margin-left: 20px;">
                        <label style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;">
                            <input type="checkbox" id="kiko-insert-tab" style="margin-right: 10px;">
                            <span>Tab key</span>
                        </label>
                        <label style="display: flex; align-items: center; cursor: pointer;">
                            <input type="checkbox" id="kiko-insert-enter" style="margin-right: 10px;">
                            <span>Enter key</span>
                        </label>
                    </div>
                </div>
            </div>
            
            <div class="kiko-settings-section">
                <h3 style="margin-bottom: 15px; font-size: 16px; font-weight: 600;">Custom Words</h3>
                
                <div class="kiko-setting-row" style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-size: 14px;">Load Custom Words</label>
                    <div style="display: flex; gap: 10px; align-items: flex-start;">
                        <input type="text" id="kiko-custom-words-url" placeholder="Enter URL to custom words list" style="
                            flex: 1;
                            padding: 8px 12px;
                            background: var(--comfy-input-bg, #1a1a1a);
                            border: 1px solid var(--border-color, #4e4e4e);
                            border-radius: 4px;
                            color: var(--fg-color, #ffffff);
                            font-size: 14px;
                        ">
                        <button id="kiko-load-custom-words" style="
                            padding: 8px 16px;
                            background: #2196F3;
                            color: white;
                            border: none;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 14px;
                            font-weight: 500;
                            transition: background 0.2s;
                            white-space: nowrap;
                        ">Load</button>
                    </div>
                    <small style="color: #888; font-size: 12px; margin-top: 4px; display: block;">
                        <strong>File Format Requirements:</strong><br>
                        • Plain text file only (no HTML, JavaScript, or code)<br>
                        • One word/tag per line<br>
                        • Optional format: <code>word,frequency</code> (comma-separated)<br>
                        • Allowed characters: letters, numbers, spaces, underscores, hyphens, basic punctuation<br>
                        • Maximum file size: 10MB<br>
                        • Example: <code>landscape</code> or <code>landscape,5000</code>
                    </small>
                    <div id="kiko-custom-words-status" style="
                        margin-top: 8px;
                        padding: 8px 12px;
                        background: var(--comfy-input-bg, #1a1a1a);
                        border: 1px solid var(--border-color, #4e4e4e);
                        border-radius: 4px;
                        font-size: 13px;
                        color: #888;
                        display: none;
                    "></div>
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
        cancelBtn.onmouseover = () => cancelBtn.style.background = "var(--comfy-input-bg-hover, #2a2a2a)";
        cancelBtn.onmouseout = () => cancelBtn.style.background = "var(--comfy-input-bg, #1a1a1a)";
        
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
        
        // Settings will be loaded after adding to DOM
        
        return backdrop;
    }
    
    showCustomStatus(message, type = "info") {
        const statusEl = document.getElementById("kiko-custom-words-status");
        if (!statusEl) return;
        
        statusEl.textContent = message;
        statusEl.style.display = "block";
        
        // Set color based on type
        switch(type) {
            case "success":
                statusEl.style.color = "#4CAF50";
                break;
            case "error":
                statusEl.style.color = "#f44336";
                break;
            case "warning":
                statusEl.style.color = "#FFA500";
                break;
            default:
                statusEl.style.color = "#888";
        }
    }
    
    loadSettings() {
        if (!this.autocomplete) return;
        
        const settings = this.autocomplete.settings;
        
        // Make sure elements exist before trying to set values
        const elements = {
            enabled: document.getElementById("kiko-enabled"),
            showEmbeddings: document.getElementById("kiko-show-embeddings"),
            showLoras: document.getElementById("kiko-show-loras"),
            showCustom: document.getElementById("kiko-show-custom"),
            groupByDir: document.getElementById("kiko-group-by-dir"),
            embeddingTrigger: document.getElementById("kiko-embedding-trigger"),
            loraTrigger: document.getElementById("kiko-lora-trigger"),
            maxSuggestions: document.getElementById("kiko-max-suggestions"),
            minChars: document.getElementById("kiko-min-chars"),
            customWordsUrl: document.getElementById("kiko-custom-words-url"),
            loadCustomBtn: document.getElementById("kiko-load-custom-words"),
            customStatus: document.getElementById("kiko-custom-words-status"),
            autoComma: document.getElementById("kiko-auto-comma"),
            replaceUnderscores: document.getElementById("kiko-replace-underscores"),
            insertTab: document.getElementById("kiko-insert-tab"),
            insertEnter: document.getElementById("kiko-insert-enter")
        };
        
        // Check if all elements exist
        if (!elements.enabled) {
            console.error("[KikoAutocomplete] Settings elements not found in DOM");
            return;
        }
        
        // Set values
        if (elements.enabled) elements.enabled.checked = settings.enabled !== false;
        if (elements.showEmbeddings) elements.showEmbeddings.checked = settings.showEmbeddings !== false;
        if (elements.showLoras) elements.showLoras.checked = settings.showLoras !== false;
        if (elements.showCustom) elements.showCustom.checked = settings.showCustomWords !== false;
        if (elements.groupByDir) elements.groupByDir.checked = settings.sortByDirectory !== false;
        if (elements.embeddingTrigger) elements.embeddingTrigger.value = settings.embeddingTrigger || "embedding:";
        if (elements.loraTrigger) elements.loraTrigger.value = settings.loraTrigger || "<lora:";
        if (elements.maxSuggestions) elements.maxSuggestions.value = settings.maxSuggestions || 20;
        if (elements.minChars) elements.minChars.value = settings.minChars || 2;
        if (elements.customWordsUrl) elements.customWordsUrl.value = settings.customWordsUrl || "";
        if (elements.autoComma) elements.autoComma.checked = settings.autoInsertComma !== false;
        if (elements.replaceUnderscores) elements.replaceUnderscores.checked = settings.replaceUnderscores !== false;
        if (elements.insertTab) elements.insertTab.checked = settings.insertOnTab !== false;
        if (elements.insertEnter) elements.insertEnter.checked = settings.insertOnEnter !== false;
        
        // Set up load button handler
        if (elements.loadCustomBtn) {
            elements.loadCustomBtn.onclick = async () => {
                const url = elements.customWordsUrl.value.trim();
                if (!url) {
                    this.showCustomStatus("Please enter a URL", "error");
                    return;
                }
                
                // Show loading state
                elements.loadCustomBtn.disabled = true;
                elements.loadCustomBtn.textContent = "Loading...";
                this.showCustomStatus("Loading custom words...", "info");
                
                try {
                    const count = await this.autocomplete.loadCustomWords(url);
                    if (count > 0) {
                        this.showCustomStatus(`Successfully loaded ${count.toLocaleString()} custom words`, "success");
                        // Save the URL if successful
                        this.autocomplete.settings.customWordsUrl = url;
                        this.autocomplete.saveSettings();
                    } else {
                        this.showCustomStatus("No words found in the file", "warning");
                    }
                } catch (error) {
                    this.showCustomStatus(`Error loading custom words: ${error.message}`, "error");
                } finally {
                    elements.loadCustomBtn.disabled = false;
                    elements.loadCustomBtn.textContent = "Load";
                }
            };
        }
        
        // Show current custom words count if any
        if (this.autocomplete.customWords && this.autocomplete.customWords.length > 0) {
            this.showCustomStatus(`${this.autocomplete.customWords.length.toLocaleString()} custom words loaded`, "info");
        }
    }
    
    save() {
        if (!this.autocomplete) return;
        
        // Gather settings
        const newSettings = {
            enabled: document.getElementById("kiko-enabled").checked,
            showEmbeddings: document.getElementById("kiko-show-embeddings").checked,
            showLoras: document.getElementById("kiko-show-loras").checked,
            showCustomWords: document.getElementById("kiko-show-custom").checked,
            sortByDirectory: document.getElementById("kiko-group-by-dir").checked,
            embeddingTrigger: document.getElementById("kiko-embedding-trigger").value || "embedding:",
            loraTrigger: document.getElementById("kiko-lora-trigger").value || "<lora:",
            maxSuggestions: parseInt(document.getElementById("kiko-max-suggestions").value) || 20,
            minChars: parseInt(document.getElementById("kiko-min-chars").value) || 2,
            customWordsUrl: document.getElementById("kiko-custom-words-url").value || "",
            autoInsertComma: document.getElementById("kiko-auto-comma").checked,
            replaceUnderscores: document.getElementById("kiko-replace-underscores").checked,
            insertOnTab: document.getElementById("kiko-insert-tab").checked,
            insertOnEnter: document.getElementById("kiko-insert-enter").checked
        };
        
        // Update autocomplete settings
        Object.assign(this.autocomplete.settings, newSettings);
        this.autocomplete.saveSettings();
        
        // Refresh resources if needed
        if (newSettings.showEmbeddings || newSettings.showLoras) {
            this.autocomplete.fetchResources();
        }
        
        // Show success message
        this.showMessage("Settings saved successfully!");
        
        // Close dialog after a short delay
        setTimeout(() => this.close(), 1000);
    }
    
    showMessage(message) {
        const msgEl = document.createElement("div");
        msgEl.textContent = message;
        msgEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 100000;
            animation: slideIn 0.3s ease;
        `;
        
        // Add animation
        const style = document.createElement("style");
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(msgEl);
        
        setTimeout(() => {
            msgEl.style.animation = "slideIn 0.3s ease reverse";
            setTimeout(() => {
                msgEl.remove();
                style.remove();
            }, 300);
        }, 2000);
    }
    
    show() {
        if (!this.element) {
            this.createDialog();
        }
        document.body.appendChild(this.element);
        
        // Load settings after adding to DOM
        setTimeout(() => this.loadSettings(), 10);
        
        // Add open animation
        this.dialog.style.animation = "fadeIn 0.2s ease";
        this.element.style.animation = "fadeIn 0.2s ease";
        
        const style = document.createElement("style");
        style.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; transform: scale(0.95); }
                to { opacity: 1; transform: scale(1); }
            }
        `;
        document.head.appendChild(style);
        this.animStyle = style;
    }
    
    close() {
        if (this.element) {
            this.element.remove();
        }
        if (this.animStyle) {
            this.animStyle.remove();
        }
    }
}

// Initialize and register

app.registerExtension({
    name: "kikotools.embeddingAutocomplete",
    
    async setup() {
        
        // Create autocomplete instance first
        window.kikoAutocomplete = new KikoEmbeddingAutocomplete();
        
        // Simple button to open settings dialog (following rgthree's pattern)
        app.ui.settings.addSetting({
            id: "kikotools.embeddingAutocomplete",
            name: "🫶 Embedding Autocomplete Configuration",
            tooltip: "Configure autocomplete settings",
            category: ["kikotools", "🫶 Embedding Autocomplete Configuration"],
            defaultValue: null,
            type: () => {
                // Create a simple row with a button to open the dialog
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
                    const dialog = new KikoEmbeddingAutocompleteDialog(window.kikoAutocomplete);
                    dialog.show();
                };
                
                tdButton.appendChild(button);
                tr.appendChild(tdLabel);
                tr.appendChild(tdButton);
                
                return tr;
            }
        });
        
        // Override STRING widget creation to add autocomplete
        const originalStringWidget = ComfyWidgets.STRING;
        
        ComfyWidgets.STRING = function(node, inputName, inputData, app) {
            const widget = originalStringWidget.apply(this, arguments);
            
            // Only attach to multiline text widgets (prompts)
            if (inputData[1]?.multiline && widget.inputEl) {
                setTimeout(() => {
                    window.kikoAutocomplete.attachToWidget(widget, node);
                }, 100);
            }
            
            return widget;
        };
        
        // Also attach to existing multiline widgets
        setTimeout(() => {
            app.graph._nodes.forEach(node => {
                if (node.widgets) {
                    node.widgets.forEach(widget => {
                        // Check for text widgets with textareas
                        if (widget.type === "customtext" && widget.inputEl && widget.inputEl.tagName === "TEXTAREA") {
                            window.kikoAutocomplete.attachToWidget(widget, node);
                        }
                        // Also check for widgets that might be text inputs but not customtext
                        else if (widget.inputEl && widget.inputEl.tagName === "TEXTAREA" && !window.kikoAutocomplete.activeWidgets.has(widget)) {
                            window.kikoAutocomplete.attachToWidget(widget, node);
                        }
                    });
                }
            });
        }, 1000); // Wait a bit for all widgets to be created
    }
});