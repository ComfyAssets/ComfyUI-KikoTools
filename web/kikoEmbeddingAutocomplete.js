import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// KikoEmbeddingAutocomplete - Provides autocomplete for embeddings and LoRAs in text widgets
class KikoEmbeddingAutocomplete {
    constructor() {
        console.log("[KikoAutocomplete] Initializing...");
        this.embeddings = [];
        this.loras = [];
        this.settings = {
            enabled: true,
            triggerChars: 2,
            maxSuggestions: 20,
            showEmbeddings: true,
            showLoras: true
        };
        
        // Load settings from localStorage
        this.loadSettings();
        
        // Fetch available embeddings and LoRAs
        this.fetchResources();
        
        // Track active widgets
        this.activeWidgets = new Set();
        
        // Debug mode
        this.debug = true;
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
        console.log("[KikoAutocomplete] Starting fetchResources...");
        try {
            // Fetch embeddings using ComfyUI's API
            if (this.settings.showEmbeddings) {
                console.log("[KikoAutocomplete] Fetching embeddings via api.getEmbeddings()...");
                try {
                    const embeddings = await api.getEmbeddings();
                    console.log("[KikoAutocomplete] Raw embeddings response:", embeddings);
                    
                    // ComfyUI returns embeddings as an object with filenames as keys
                    if (embeddings && typeof embeddings === 'object') {
                        // Extract the keys (embedding names) from the object
                        const embeddingNames = Object.keys(embeddings);
                        console.log("[KikoAutocomplete] Found embedding names:", embeddingNames.slice(0, 5));
                        
                        this.embeddings = embeddingNames.map(name => {
                            // Remove file extension if present
                            const cleanName = name.replace(/\.(pt|safetensors|ckpt|bin)$/i, '');
                            return {
                                name: cleanName,
                                type: "embedding",
                                display: `embedding:${cleanName}`,
                                value: `embedding:${cleanName}`
                            };
                        });
                    } else {
                        console.warn("[KikoAutocomplete] Unexpected embeddings response:", typeof embeddings);
                        this.embeddings = [];
                    }
                    console.log(`[KikoAutocomplete] Processed ${this.embeddings.length} embeddings:`, this.embeddings.slice(0, 5));
                } catch (e) {
                    console.error("[KikoAutocomplete] Error fetching embeddings:", e);
                    this.embeddings = [];
                }
            }
            
            // Fetch LoRAs - try multiple methods
            if (this.settings.showLoras) {
                console.log("[KikoAutocomplete] Fetching LoRAs...");
                
                // Method 1: Try our custom endpoint
                try {
                    const response = await fetch("/kikotools/autocomplete/loras");
                    console.log("[KikoAutocomplete] Custom LoRA endpoint status:", response.status);
                    if (response.ok) {
                        const loras = await response.json();
                        console.log("[KikoAutocomplete] Raw LoRAs response:", loras);
                        this.loras = loras.map(name => ({
                            name: name,
                            type: "lora",
                            display: `<lora:${name}:1.0>`,
                            value: `<lora:${name}:1.0>`
                        }));
                        console.log(`[KikoAutocomplete] Processed ${this.loras.length} LoRAs from custom endpoint`);
                    } else {
                        throw new Error("Custom endpoint not available");
                    }
                } catch (e) {
                    console.log("[KikoAutocomplete] Custom endpoint failed, trying alternative method...");
                    
                    // Method 2: Try using the object list API
                    try {
                        const response = await fetch("/object_info");
                        if (response.ok) {
                            const objectInfo = await response.json();
                            // Look for LoraLoader node to get available loras
                            if (objectInfo.LoraLoader?.input?.required?.lora_name?.[0]) {
                                const loraNames = objectInfo.LoraLoader.input.required.lora_name[0];
                                console.log("[KikoAutocomplete] Found LoRAs from object_info:", loraNames.slice(0, 5));
                                this.loras = loraNames.map(name => {
                                    const cleanName = name.replace(/\.(pt|safetensors|ckpt|bin)$/i, '');
                                    return {
                                        name: cleanName,
                                        type: "lora",
                                        display: `<lora:${cleanName}:1.0>`,
                                        value: `<lora:${cleanName}:1.0>`
                                    };
                                });
                                console.log(`[KikoAutocomplete] Processed ${this.loras.length} LoRAs from object_info`);
                            }
                        }
                    } catch (e2) {
                        console.error("[KikoAutocomplete] Could not fetch LoRAs:", e2);
                        this.loras = [];
                    }
                }
            }
            
            console.log(`[KikoAutocomplete] Total loaded: ${this.embeddings.length} embeddings and ${this.loras.length} LoRAs`);
            
            // Store in window for debugging
            window.kikoDebug = {
                embeddings: this.embeddings,
                loras: this.loras,
                autocomplete: this
            };
            console.log("[KikoAutocomplete] Debug info available at window.kikoDebug");
            
        } catch (error) {
            console.error("[KikoAutocomplete] Fatal error in fetchResources:", error);
        }
    }
    
    attachToWidget(widget, node) {
        if (!widget.inputEl || this.activeWidgets.has(widget)) {
            return;
        }
        
        console.log("[KikoAutocomplete] Attaching to widget:", widget, "on node:", node?.title);
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
            selectedIndex = -1;
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
                typeSpan.style.cssText = `
                    display: inline-block;
                    width: 60px;
                    color: ${item.type === "embedding" ? "#4CAF50" : "#2196F3"};
                    font-size: 0.9em;
                `;
                typeSpan.textContent = item.type === "embedding" ? "[EMB]" : "[LORA]";
                
                const nameSpan = document.createElement("span");
                nameSpan.textContent = item.name;
                
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
        };
        
        const insertSuggestion = (suggestion) => {
            const text = textarea.value;
            const cursor = textarea.selectionStart;
            const textBefore = text.substring(0, cursor);
            
            // Determine what to insert based on context
            let insertText = "";
            let replaceLength = currentPrefix.length;
            
            // Check if we're completing an embedding
            if (textBefore.match(/embedding:([a-zA-Z0-9_-]*)$/)) {
                insertText = suggestion.name;  // Just the name, not the full "embedding:name"
            }
            // Check if we're completing a lora
            else if (textBefore.match(/<lora:([a-zA-Z0-9_-]*)$/)) {
                insertText = suggestion.name + ":1.0>";  // Complete the lora syntax
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
            
            textarea.value = before + insertText + after;
            textarea.selectionStart = textarea.selectionEnd = prefixStart + insertText.length;
            
            hideSuggestions();
            
            // Trigger change event
            const event = new Event("input", { bubbles: true });
            textarea.dispatchEvent(event);
        };
        
        const findPrefix = () => {
            const text = textarea.value;
            const cursor = textarea.selectionStart;
            const textBefore = text.substring(0, cursor);
            
            if (this.debug) {
                console.log("[KikoAutocomplete] findPrefix - textBefore:", textBefore);
            }
            
            // Check for embedding: trigger
            const embeddingMatch = textBefore.match(/embedding:([a-zA-Z0-9_-]*)$/);
            if (embeddingMatch) {
                currentPrefix = embeddingMatch[1].toLowerCase();
                prefixStart = cursor - embeddingMatch[1].length;
                console.log("[KikoAutocomplete] Found embedding trigger, prefix:", currentPrefix);
                return "embedding";
            }
            
            // Check for <lora: trigger
            const loraMatch = textBefore.match(/<lora:([a-zA-Z0-9_-]*)$/);
            if (loraMatch) {
                currentPrefix = loraMatch[1].toLowerCase();
                prefixStart = cursor - loraMatch[1].length;
                return "lora";
            }
            
            // Check for general word to match (after minimum chars)
            let start = cursor - 1;
            while (start >= 0 && /[a-zA-Z0-9_-]/.test(text[start])) {
                start--;
            }
            start++;
            
            const prefix = text.substring(start, cursor);
            
            // Check if we should show suggestions for general matching
            if (prefix.length >= this.settings.triggerChars) {
                currentPrefix = prefix.toLowerCase();
                prefixStart = start;
                return "general";
            }
            
            return false;
        };
        
        const getSuggestions = (prefix, type) => {
            const suggestions = [];
            
            // If type is embedding, only show embeddings
            if (type === "embedding" && this.settings.showEmbeddings) {
                suggestions.push(...this.embeddings.filter(e => 
                    prefix === "" || e.name.toLowerCase().includes(prefix)
                ));
            }
            // If type is lora, only show loras
            else if (type === "lora" && this.settings.showLoras) {
                suggestions.push(...this.loras.filter(l => 
                    prefix === "" || l.name.toLowerCase().includes(prefix)
                ));
            }
            // For general matching, show both
            else if (type === "general") {
                if (this.settings.showEmbeddings) {
                    suggestions.push(...this.embeddings.filter(e => 
                        e.name.toLowerCase().includes(prefix)
                    ));
                }
                
                if (this.settings.showLoras) {
                    suggestions.push(...this.loras.filter(l => 
                        l.name.toLowerCase().includes(prefix)
                    ));
                }
            }
            
            // Sort suggestions - prioritize exact matches and starts-with matches
            suggestions.sort((a, b) => {
                const aName = a.name.toLowerCase();
                const bName = b.name.toLowerCase();
                
                // Exact match
                if (aName === prefix) return -1;
                if (bName === prefix) return 1;
                
                // Starts with
                if (aName.startsWith(prefix) && !bName.startsWith(prefix)) return -1;
                if (!aName.startsWith(prefix) && bName.startsWith(prefix)) return 1;
                
                // Alphabetical
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
            } else if (e.key === "Enter" || e.key === "Tab") {
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
    }
}

// Initialize and register
console.log("[KikoTools] Registering Embedding Autocomplete extension");

app.registerExtension({
    name: "kikotools.embeddingAutocomplete",
    
    async setup() {
        console.log("[KikoTools] Setting up Embedding Autocomplete");
        
        // Add settings
        app.ui.settings.addSetting({
            id: "kikotools.embeddingAutocomplete.enabled",
            name: "Enabled",
            category: ["KikoTools", "Embedding Autocomplete"],
            defaultValue: true,
            type: "boolean",
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.enabled = value;
                    window.kikoAutocomplete.saveSettings();
                }
            }
        });
        
        app.ui.settings.addSetting({
            id: "kikotools.embeddingAutocomplete.triggerChars",
            name: "Trigger After Characters",
            category: ["KikoTools", "Embedding Autocomplete"],
            defaultValue: 2,
            type: "combo",
            options: [
                { value: 1, text: "1 character" },
                { value: 2, text: "2 characters" },
                { value: 3, text: "3 characters" },
                { value: 4, text: "4 characters" }
            ],
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.triggerChars = value;
                    window.kikoAutocomplete.saveSettings();
                }
            }
        });
        
        app.ui.settings.addSetting({
            id: "kikotools.embeddingAutocomplete.maxSuggestions",
            name: "Maximum Suggestions",
            category: ["KikoTools", "Embedding Autocomplete"],
            defaultValue: 20,
            type: "combo",
            options: [
                { value: 10, text: "10" },
                { value: 20, text: "20" },
                { value: 30, text: "30" },
                { value: 50, text: "50" }
            ],
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.maxSuggestions = value;
                    window.kikoAutocomplete.saveSettings();
                }
            }
        });
        
        app.ui.settings.addSetting({
            id: "kikotools.embeddingAutocomplete.showEmbeddings",
            name: "Show Embeddings",
            category: ["KikoTools", "Embedding Autocomplete"],
            defaultValue: true,
            type: "boolean",
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.showEmbeddings = value;
                    window.kikoAutocomplete.saveSettings();
                    window.kikoAutocomplete.fetchResources();
                }
            }
        });
        
        app.ui.settings.addSetting({
            id: "kikotools.embeddingAutocomplete.showLoras",
            name: "Show LoRAs",
            category: ["KikoTools", "Embedding Autocomplete"],
            defaultValue: true,
            type: "boolean",
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.showLoras = value;
                    window.kikoAutocomplete.saveSettings();
                    window.kikoAutocomplete.fetchResources();
                }
            }
        });
        
        // Create autocomplete instance
        window.kikoAutocomplete = new KikoEmbeddingAutocomplete();
        
        // Override STRING widget creation to add autocomplete
        const originalStringWidget = ComfyWidgets.STRING;
        console.log("[KikoAutocomplete] Original STRING widget:", originalStringWidget);
        
        ComfyWidgets.STRING = function(node, inputName, inputData, app) {
            console.log("[KikoAutocomplete] Creating STRING widget for:", inputName, "multiline:", inputData[1]?.multiline);
            const widget = originalStringWidget.apply(this, arguments);
            
            // Only attach to multiline text widgets (prompts)
            if (inputData[1]?.multiline && widget.inputEl) {
                console.log("[KikoAutocomplete] Will attach to multiline widget:", inputName);
                setTimeout(() => {
                    window.kikoAutocomplete.attachToWidget(widget, node);
                }, 100);
            }
            
            return widget;
        };
        
        // Also attach to existing multiline widgets
        console.log("[KikoAutocomplete] Looking for existing widgets to attach to...");
        setTimeout(() => {
            app.graph._nodes.forEach(node => {
                if (node.widgets) {
                    node.widgets.forEach(widget => {
                        // Check for text widgets with textareas
                        if (widget.type === "customtext" && widget.inputEl && widget.inputEl.tagName === "TEXTAREA") {
                            console.log("[KikoAutocomplete] Found existing textarea widget on node:", node.title, "widget:", widget.name);
                            window.kikoAutocomplete.attachToWidget(widget, node);
                        }
                        // Also check for widgets that might be text inputs but not customtext
                        else if (widget.inputEl && widget.inputEl.tagName === "TEXTAREA" && !window.kikoAutocomplete.activeWidgets.has(widget)) {
                            console.log("[KikoAutocomplete] Found textarea widget (non-customtext) on node:", node.title, "widget:", widget.name);
                            window.kikoAutocomplete.attachToWidget(widget, node);
                        }
                    });
                }
            });
        }, 1000); // Wait a bit for all widgets to be created
    }
});