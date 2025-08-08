/**
 * KikoTools Embedding Autocomplete
 * Provides autocomplete functionality for embeddings and LoRAs in ComfyUI text inputs
 */

import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Autocomplete class
class KikoEmbeddingAutocomplete {
    constructor() {
        this.suggestions = [];
        this.currentIndex = -1;
        this.dropdown = null;
        this.activeWidget = null;
        this.activeNode = null;
        
        // Settings
        this.settings = {
            enabled: true,
            triggerChars: 2,
            maxSuggestions: 20,
            showEmbeddings: true,
            showLoras: true,
            caseSensitive: false
        };
        
        // Load settings from ComfyUI
        this.loadSettings();
    }
    
    loadSettings() {
        this.settings.enabled = app.ui.settings.getSettingValue("kikotools.embedding_autocomplete.enabled", true);
        this.settings.triggerChars = app.ui.settings.getSettingValue("kikotools.embedding_autocomplete.trigger_chars", 2);
        this.settings.maxSuggestions = app.ui.settings.getSettingValue("kikotools.embedding_autocomplete.max_suggestions", 20);
        this.settings.showEmbeddings = app.ui.settings.getSettingValue("kikotools.embedding_autocomplete.show_embeddings", true);
        this.settings.showLoras = app.ui.settings.getSettingValue("kikotools.embedding_autocomplete.show_loras", true);
        this.settings.caseSensitive = app.ui.settings.getSettingValue("kikotools.embedding_autocomplete.case_sensitive", false);
    }
    
    async fetchSuggestions(prefix) {
        if (!this.settings.enabled || prefix.length < this.settings.triggerChars) {
            return [];
        }
        
        try {
            const params = new URLSearchParams({
                prefix: prefix,
                max: this.settings.maxSuggestions,
                embeddings: this.settings.showEmbeddings,
                loras: this.settings.showLoras,
                case_sensitive: this.settings.caseSensitive
            });
            
            const response = await fetch(`/kikotools/autocomplete/suggestions?${params}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error("[KikoAutocomplete] Error fetching suggestions:", error);
        }
        
        return [];
    }
    
    extractCurrentWord(text, cursorPos) {
        // Extract word at cursor position
        const beforeCursor = text.substring(0, cursorPos);
        
        // Look for special triggers
        const embeddingMatch = beforeCursor.match(/embedding:([^,\s]*)$/);
        if (embeddingMatch) {
            return {
                word: embeddingMatch[1],
                start: beforeCursor.length - embeddingMatch[1].length,
                type: "embedding"
            };
        }
        
        const loraMatch = beforeCursor.match(/<lora:([^:>]*)$/);
        if (loraMatch) {
            return {
                word: loraMatch[1],
                start: beforeCursor.length - loraMatch[1].length,
                type: "lora"
            };
        }
        
        // General word extraction
        const wordMatch = beforeCursor.match(/([^,\s]+)$/);
        if (wordMatch) {
            return {
                word: wordMatch[1],
                start: beforeCursor.length - wordMatch[1].length,
                type: "general"
            };
        }
        
        return null;
    }
    
    createDropdown() {
        if (this.dropdown) {
            this.removeDropdown();
        }
        
        this.dropdown = document.createElement("div");
        this.dropdown.className = "kiko-autocomplete-dropdown";
        this.dropdown.style.cssText = `
            position: absolute;
            background: var(--comfy-menu-bg, #353535);
            border: 1px solid var(--border-color, #4e4e4e);
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 10000;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            min-width: 200px;
        `;
        
        document.body.appendChild(this.dropdown);
    }
    
    removeDropdown() {
        if (this.dropdown) {
            this.dropdown.remove();
            this.dropdown = null;
            this.currentIndex = -1;
        }
    }
    
    positionDropdown(textarea) {
        if (!this.dropdown) return;
        
        const rect = textarea.getBoundingClientRect();
        
        // Simple positioning below the textarea
        // In a more advanced version, we'd calculate caret position
        this.dropdown.style.left = rect.left + "px";
        this.dropdown.style.top = (rect.bottom + 2) + "px";
        this.dropdown.style.width = rect.width + "px";
    }
    
    showSuggestions(suggestions, textarea, wordInfo) {
        if (!suggestions || suggestions.length === 0) {
            this.removeDropdown();
            return;
        }
        
        this.suggestions = suggestions;
        this.createDropdown();
        this.positionDropdown(textarea);
        
        // Populate dropdown
        this.dropdown.innerHTML = "";
        suggestions.forEach((suggestion, index) => {
            const item = document.createElement("div");
            item.className = "kiko-autocomplete-item";
            item.style.cssText = `
                padding: 5px 10px;
                cursor: pointer;
                color: var(--fg-color, #fff);
                display: flex;
                justify-content: space-between;
                align-items: center;
            `;
            
            // Highlight matching part
            const displayText = suggestion.display || suggestion.value;
            const matchIndex = displayText.toLowerCase().indexOf(wordInfo.word.toLowerCase());
            
            if (matchIndex >= 0 && wordInfo.word) {
                const before = displayText.substring(0, matchIndex);
                const match = displayText.substring(matchIndex, matchIndex + wordInfo.word.length);
                const after = displayText.substring(matchIndex + wordInfo.word.length);
                
                item.innerHTML = `
                    <span>${before}<strong style="color: var(--primary-color, #ff6b6b);">${match}</strong>${after}</span>
                    <span style="opacity: 0.6; font-size: 0.9em;">${suggestion.type}</span>
                `;
            } else {
                item.innerHTML = `
                    <span>${displayText}</span>
                    <span style="opacity: 0.6; font-size: 0.9em;">${suggestion.type}</span>
                `;
            }
            
            // Hover effect
            item.addEventListener("mouseenter", () => {
                this.selectIndex(index);
            });
            
            // Click to select
            item.addEventListener("click", () => {
                this.applySuggestion(textarea, wordInfo, suggestion);
            });
            
            this.dropdown.appendChild(item);
        });
        
        // Select first item by default
        if (suggestions.length > 0) {
            this.selectIndex(0);
        }
    }
    
    selectIndex(index) {
        // Remove previous selection
        const items = this.dropdown?.querySelectorAll(".kiko-autocomplete-item");
        if (!items) return;
        
        items.forEach((item, i) => {
            if (i === index) {
                item.style.background = "var(--comfy-input-bg, #222)";
                this.currentIndex = i;
            } else {
                item.style.background = "";
            }
        });
    }
    
    applySuggestion(textarea, wordInfo, suggestion) {
        const text = textarea.value;
        const beforeWord = text.substring(0, wordInfo.start);
        const afterWord = text.substring(wordInfo.start + wordInfo.word.length);
        
        // Determine what to insert based on context
        let insertion = suggestion.value;
        
        // Handle different insertion contexts
        if (wordInfo.type === "embedding" && !suggestion.value.startsWith("embedding:")) {
            insertion = "embedding:" + suggestion.value;
        } else if (wordInfo.type === "lora" && !suggestion.value.startsWith("<lora:")) {
            insertion = `<lora:${suggestion.value}:1.0>`;
        }
        
        // Apply the suggestion
        textarea.value = beforeWord + insertion + afterWord;
        
        // Position cursor after insertion
        const newPos = beforeWord.length + insertion.length;
        textarea.setSelectionRange(newPos, newPos);
        
        // Trigger input event to update the widget
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        
        // Remove dropdown
        this.removeDropdown();
    }
    
    attachToWidget(widget, node) {
        const textarea = widget.inputEl;
        if (!textarea || textarea.kikoAutocompleteAttached) return;
        
        textarea.kikoAutocompleteAttached = true;
        
        // Input handler with debouncing
        let debounceTimer;
        textarea.addEventListener("input", async (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(async () => {
                const cursorPos = textarea.selectionStart;
                const wordInfo = this.extractCurrentWord(textarea.value, cursorPos);
                
                if (wordInfo && wordInfo.word.length >= this.settings.triggerChars) {
                    const suggestions = await this.fetchSuggestions(wordInfo.word);
                    this.showSuggestions(suggestions, textarea, wordInfo);
                    this.activeWidget = widget;
                    this.activeNode = node;
                } else {
                    this.removeDropdown();
                }
            }, 200);
        });
        
        // Keyboard navigation
        textarea.addEventListener("keydown", (e) => {
            if (!this.dropdown || this.suggestions.length === 0) return;
            
            switch(e.key) {
                case "ArrowDown":
                    e.preventDefault();
                    this.selectIndex((this.currentIndex + 1) % this.suggestions.length);
                    break;
                    
                case "ArrowUp":
                    e.preventDefault();
                    this.selectIndex(this.currentIndex <= 0 ? this.suggestions.length - 1 : this.currentIndex - 1);
                    break;
                    
                case "Enter":
                case "Tab":
                    if (this.currentIndex >= 0) {
                        e.preventDefault();
                        const cursorPos = textarea.selectionStart;
                        const wordInfo = this.extractCurrentWord(textarea.value, cursorPos);
                        if (wordInfo) {
                            this.applySuggestion(textarea, wordInfo, this.suggestions[this.currentIndex]);
                        }
                    }
                    break;
                    
                case "Escape":
                    e.preventDefault();
                    this.removeDropdown();
                    break;
            }
        });
        
        // Hide on blur
        textarea.addEventListener("blur", () => {
            // Delay to allow click events to fire
            setTimeout(() => this.removeDropdown(), 200);
        });
    }
}

// Initialize and register
app.registerExtension({
    name: "kikotools.embeddingAutocomplete",
    
    async init() {
        // Add settings
        app.ui.settings.addSetting({
            id: "kikotools.embedding_autocomplete.enabled",
            name: "🫶 Embedding Autocomplete: Enabled",
            defaultValue: true,
            type: "boolean",
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.enabled = value;
                }
            }
        });
        
        app.ui.settings.addSetting({
            id: "kikotools.embedding_autocomplete.trigger_chars",
            name: "🫶 Embedding Autocomplete: Trigger After Characters",
            defaultValue: 2,
            type: "combo",
            options: (value) => [
                { value: 1, text: "1", selected: value === 1 },
                { value: 2, text: "2", selected: value === 2 },
                { value: 3, text: "3", selected: value === 3 },
                { value: 4, text: "4", selected: value === 4 }
            ],
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.triggerChars = value;
                }
            }
        });
        
        app.ui.settings.addSetting({
            id: "kikotools.embedding_autocomplete.max_suggestions",
            name: "🫶 Embedding Autocomplete: Maximum Suggestions",
            defaultValue: 20,
            type: "combo",
            options: (value) => [
                { value: 10, text: "10", selected: value === 10 },
                { value: 20, text: "20", selected: value === 20 },
                { value: 30, text: "30", selected: value === 30 },
                { value: 50, text: "50", selected: value === 50 }
            ],
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.maxSuggestions = value;
                }
            }
        });
        
        app.ui.settings.addSetting({
            id: "kikotools.embedding_autocomplete.show_embeddings",
            name: "🫶 Embedding Autocomplete: Show Embeddings",
            defaultValue: true,
            type: "boolean",
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.showEmbeddings = value;
                }
            }
        });
        
        app.ui.settings.addSetting({
            id: "kikotools.embedding_autocomplete.show_loras",
            name: "🫶 Embedding Autocomplete: Show LoRAs",
            defaultValue: true,
            type: "boolean",
            onChange(value) {
                if (window.kikoAutocomplete) {
                    window.kikoAutocomplete.settings.showLoras = value;
                }
            }
        });
    },
    
    async setup() {
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