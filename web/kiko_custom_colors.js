import { app } from "../../scripts/app.js";
import { $el } from "../../scripts/ui.js";

// Custom colors feature with extended options based on PR #433
// Adds custom color pickers for nodes with full, title, and background options

const colorShade = (col, amt) => {
    col = col.replace(/^#/, "");
    if (col.length === 3) col = col[0] + col[0] + col[1] + col[1] + col[2] + col[2];

    let [r, g, b] = col.match(/.{2}/g);
    [r, g, b] = [parseInt(r, 16) + amt, parseInt(g, 16) + amt, parseInt(b, 16) + amt];

    r = Math.max(Math.min(255, r), 0).toString(16);
    g = Math.max(Math.min(255, g), 0).toString(16);
    b = Math.max(Math.min(255, b), 0).toString(16);

    const rr = (r.length < 2 ? "0" : "") + r;
    const gg = (g.length < 2 ? "0" : "") + g;
    const bb = (b.length < 2 ? "0" : "") + b;

    return `#${rr}${gg}${bb}`;
};

app.registerExtension({
    name: "kikotools.customColors",
    async init() {
        // Register settings
        app.ui.settings.addSetting({
            id: "kikotools.custom_colors.enabled",
            name: "🫶 Custom Colors: Enable",
            type: "boolean",
            defaultValue: false,
            tooltip: "Enable custom color picker options in node context menu",
        });

        app.ui.settings.addSetting({
            id: "kikotools.custom_colors.show_full",
            name: "🫶 Custom Colors: Show Full Color Option",
            type: "boolean",
            defaultValue: true,
            tooltip: "Show option to change both title and background colors",
        });

        app.ui.settings.addSetting({
            id: "kikotools.custom_colors.show_title",
            name: "🫶 Custom Colors: Show Title Color Option",
            type: "boolean",
            defaultValue: true,
            tooltip: "Show option to change only title color",
        });

        app.ui.settings.addSetting({
            id: "kikotools.custom_colors.show_bg",
            name: "🫶 Custom Colors: Show Background Color Option",
            type: "boolean",
            defaultValue: true,
            tooltip: "Show option to change only background color",
        });

        app.ui.settings.addSetting({
            id: "kikotools.custom_colors.auto_shade",
            name: "🫶 Custom Colors: Auto-shade Title",
            type: "boolean",
            defaultValue: true,
            tooltip: "Automatically apply shading to title color for better contrast",
        });
    },

    setup() {
        let pickerFull, pickerTitle, pickerBG;
        let activeNode;
        
        // Check if feature is enabled
        const isEnabled = () => {
            const setting = app.ui.settings.getSettingValue("kikotools.custom_colors.enabled");
            return setting !== undefined ? setting : false;
        };

        const getSettings = () => ({
            showFull: app.ui.settings.getSettingValue("kikotools.custom_colors.show_full") !== false,
            showTitle: app.ui.settings.getSettingValue("kikotools.custom_colors.show_title") !== false,
            showBG: app.ui.settings.getSettingValue("kikotools.custom_colors.show_bg") !== false,
            autoShade: app.ui.settings.getSettingValue("kikotools.custom_colors.auto_shade") !== false,
        });

        // Helper function to apply color to node(s)
        const applyColorToNodes = (colorValue, colorType, node) => {
            const settings = getSettings();
            const graphcanvas = LGraphCanvas.active_canvas;
            const nodes = (!graphcanvas.selected_nodes || Object.keys(graphcanvas.selected_nodes).length <= 1) 
                ? [node] 
                : Object.values(graphcanvas.selected_nodes);

            nodes.forEach(n => {
                if (colorValue) {
                    if (n.constructor === LiteGraph.LGraphGroup) {
                        // For groups, only set the main color
                        if (colorType === 'full' || colorType === 'bg') {
                            n.color = colorValue;
                        }
                    } else {
                        // For regular nodes
                        switch(colorType) {
                            case 'full':
                                n.color = settings.autoShade ? colorShade(colorValue, 20) : colorValue;
                                n.bgcolor = colorValue;
                                break;
                            case 'title':
                                n.color = colorValue;
                                break;
                            case 'bg':
                                n.bgcolor = colorValue;
                                break;
                        }
                    }
                }
            });

            node.setDirtyCanvas(true, true);
        };

        // Create color picker input if not exists
        const createPicker = (type) => {
            const picker = $el("input", {
                type: "color",
                parent: document.body,
                style: {
                    display: "none",
                },
            });
            
            picker.onchange = () => {
                if (activeNode) {
                    applyColorToNodes(picker.value, type, activeNode);
                }
            };
            
            return picker;
        };

        // Hook into the node colors menu
        const onMenuNodeColors = LGraphCanvas.onMenuNodeColors;
        LGraphCanvas.onMenuNodeColors = function (value, options, e, menu, node) {
            const r = onMenuNodeColors.apply(this, arguments);
            
            // Only add custom options if enabled
            if (!isEnabled()) return r;
            
            const settings = getSettings();
            
            requestAnimationFrame(() => {
                const menus = document.querySelectorAll(".litecontextmenu");
                for (let i = menus.length - 1; i >= 0; i--) {
                    if (menus[i].firstElementChild.textContent.includes("No color") || 
                        menus[i].firstElementChild.value?.content?.includes("No color")) {
                        
                        // Add Custom Full option
                        if (settings.showFull) {
                            $el(
                                "div.litemenu-entry.submenu",
                                {
                                    parent: menus[i],
                                    $: (el) => {
                                        el.onclick = () => {
                                            LiteGraph.closeAllContextMenus();
                                            if (!pickerFull) {
                                                pickerFull = createPicker('full');
                                            }
                                            activeNode = null;
                                            pickerFull.value = node.bgcolor || "#000000";
                                            activeNode = node;
                                            pickerFull.click();
                                        };
                                    },
                                },
                                [
                                    $el("span", {
                                        style: {
                                            paddingLeft: "4px",
                                            display: "block",
                                        },
                                        textContent: "🫶 Custom Full",
                                    }),
                                ]
                            );
                        }

                        // Add Custom Title option
                        if (settings.showTitle) {
                            $el(
                                "div.litemenu-entry.submenu",
                                {
                                    parent: menus[i],
                                    $: (el) => {
                                        el.onclick = () => {
                                            LiteGraph.closeAllContextMenus();
                                            if (!pickerTitle) {
                                                pickerTitle = createPicker('title');
                                            }
                                            activeNode = null;
                                            pickerTitle.value = node.color || "#000000";
                                            activeNode = node;
                                            pickerTitle.click();
                                        };
                                    },
                                },
                                [
                                    $el("span", {
                                        style: {
                                            paddingLeft: "4px",
                                            display: "block",
                                        },
                                        textContent: "🫶 Custom Title",
                                    }),
                                ]
                            );
                        }

                        // Add Custom BG option
                        if (settings.showBG) {
                            $el(
                                "div.litemenu-entry.submenu",
                                {
                                    parent: menus[i],
                                    $: (el) => {
                                        el.onclick = () => {
                                            LiteGraph.closeAllContextMenus();
                                            if (!pickerBG) {
                                                pickerBG = createPicker('bg');
                                            }
                                            activeNode = null;
                                            pickerBG.value = node.bgcolor || "#000000";
                                            activeNode = node;
                                            pickerBG.click();
                                        };
                                    },
                                },
                                [
                                    $el("span", {
                                        style: {
                                            paddingLeft: "4px",
                                            display: "block",
                                        },
                                        textContent: "🫶 Custom BG",
                                    }),
                                ]
                            );
                        }
                        
                        break;
                    }
                }
            });
            return r;
        };
    },
});