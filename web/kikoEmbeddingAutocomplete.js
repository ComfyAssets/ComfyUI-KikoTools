import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// KikoEmbeddingAutocomplete - Provides autocomplete for embeddings and LoRAs in text widgets
class KikoEmbeddingAutocomplete {
    constructor() {
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
            // Fetch embeddings
            if (this.settings.showEmbeddings) {
                const embResponse = await fetch("/embeddings");
                if (embResponse.ok) {
                    const data = await embResponse.json();
                    this.embeddings = Object.keys(data || {}).map(name => ({
                        name: name,
                        type: "embedding",
                        display: `embedding:${name}`
                    }));
                }
            }
            
            // Fetch LoRAs
            if (this.settings.showLoras) {
                const loraResponse = await fetch("/models/loras");
                if (loraResponse.ok) {
                    const data = await loraResponse.json();
                    this.loras = (data || []).map(name => ({
                        name: name,
                        type: "lora",
                        display: `<lora:${name}:1.0>`
                    }));
                }
            }
            
            console.log(`[KikoTools] Loaded ${this.embeddings.length} embeddings and ${this.loras.length} LoRAs`);
        } catch (error) {
            console.error("[KikoTools] Error fetching resources:", error);
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
            const before = text.substring(0, prefixStart);
            const after = text.substring(textarea.selectionStart);
            
            textarea.value = before + suggestion.display + after;
            textarea.selectionStart = textarea.selectionEnd = prefixStart + suggestion.display.length;
            
            hideSuggestions();
            
            // Trigger change event
            const event = new Event("input", { bubbles: true });
            textarea.dispatchEvent(event);
        };
        
        const findPrefix = () => {
            const text = textarea.value;
            const cursor = textarea.selectionStart;
            
            // Look for embedding or lora prefix
            let start = cursor - 1;
            while (start >= 0 && text[start] !== " " && text[start] !== "\n" && text[start] !== ",") {
                start--;
            }
            start++;
            
            const prefix = text.substring(start, cursor).toLowerCase();
            
            // Check if we should show suggestions
            if (prefix.length >= this.settings.triggerChars) {
                currentPrefix = prefix;
                prefixStart = start;
                return true;
            }
            
            return false;
        };
        
        const getSuggestions = (prefix) => {
            const suggestions = [];
            
            if (this.settings.showEmbeddings) {
                suggestions.push(...this.embeddings.filter(e => 
                    e.name.toLowerCase().includes(prefix) || 
                    e.display.toLowerCase().includes(prefix)
                ));
            }
            
            if (this.settings.showLoras) {
                suggestions.push(...this.loras.filter(l => 
                    l.name.toLowerCase().includes(prefix) || 
                    l.display.toLowerCase().includes(prefix)
                ));
            }
            
            return suggestions.slice(0, this.settings.maxSuggestions);
        };
        
        // Event handlers
        textarea.addEventListener("input", (e) => {
            if (!this.settings.enabled) {
                hideSuggestions();
                return;
            }
            
            if (findPrefix()) {
                currentSuggestions = getSuggestions(currentPrefix);
                
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
    }
});