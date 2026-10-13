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

// Lazy-initialized color pickers (reused across invocations)
let pickerFull, pickerTitle, pickerBG;
let activeNode;

const isEnabled = () => {
    const setting = app.ui.settings.getSettingValue("kikotools.custom_colors.enabled");
    return setting !== undefined ? setting : true;
};

const getSettings = () => ({
    showFull: app.ui.settings.getSettingValue("kikotools.custom_colors.show_full") !== false,
    showTitle: app.ui.settings.getSettingValue("kikotools.custom_colors.show_title") !== false,
    showBG: app.ui.settings.getSettingValue("kikotools.custom_colors.show_bg") !== false,
    autoShade: app.ui.settings.getSettingValue("kikotools.custom_colors.auto_shade") !== false,
});

// Helper function to apply color to node(s)
// Uses setColorOption like the built-in colors when possible
const applyColorToNodes = (colorValue, colorType, node) => {
    if (!colorValue) return;

    const graphcanvas = LGraphCanvas.active_canvas;
    const nodes = (!graphcanvas.selected_nodes || Object.keys(graphcanvas.selected_nodes).length <= 1)
        ? [node]
        : Object.values(graphcanvas.selected_nodes);

    for (const n of nodes) {
        if (n.constructor === LiteGraph.LGraphGroup) {
            if (colorType === 'full' || colorType === 'bg') {
                if (n.setColorOption) {
                    n.setColorOption({ groupcolor: colorValue });
                } else {
                    n.color = colorValue;
                }
            }
        } else {
            switch(colorType) {
                case 'full':
                    if (n.setColorOption) {
                        n.setColorOption({
                            color: colorShade(colorValue, 20),
                            bgcolor: colorValue
                        });
                    } else {
                        n.color = colorShade(colorValue, 20);
                        n.bgcolor = colorValue;
                    }
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

    node.setDirtyCanvas(true, true);
};

// Create hidden color picker input (lazily, reused)
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

app.registerExtension({
    name: "kikotools.customColors",
    async init() {
        app.ui.settings.addSetting({
            id: "kikotools.custom_colors.enabled",
            name: "🫶 Custom Colors: Enable",
            type: "boolean",
            defaultValue: true,
            tooltip: "Enable custom color picker options in node context menu (Full/Title/BG)",
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

    // New API: return items to append to node right-click menu
    getNodeMenuItems(node) {
        if (!isEnabled()) return [];

        const settings = getSettings();
        const options = [];

        if (settings.showFull) {
            options.push({
                content: "🫶 Custom Full",
                callback: () => {
                    if (!pickerFull) pickerFull = createPicker('full');
                    activeNode = node;
                    pickerFull.value = node.bgcolor || "#000000";
                    pickerFull.click();
                },
            });
        }

        if (settings.showTitle) {
            options.push({
                content: "🫶 Custom Title",
                callback: () => {
                    if (!pickerTitle) pickerTitle = createPicker('title');
                    activeNode = node;
                    pickerTitle.value = node.color || "#000000";
                    pickerTitle.click();
                },
            });
        }

        if (settings.showBG) {
            options.push({
                content: "🫶 Custom BG",
                callback: () => {
                    if (!pickerBG) pickerBG = createPicker('bg');
                    activeNode = node;
                    pickerBG.value = node.bgcolor || "#000000";
                    pickerBG.click();
                },
            });
        }

        if (options.length === 0) return [];

        return [
            null, // separator
            {
                content: "🫶 Custom Colors",
                submenu: {
                    options: options,
                },
            },
        ];
    },
});
