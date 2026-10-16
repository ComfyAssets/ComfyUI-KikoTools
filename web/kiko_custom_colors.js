import { app } from "../../scripts/app.js";
import { createColorPicker } from "./ui/color-picker.js";

// Custom colors feature with extended options based on PR #433
// Adds custom color pickers for nodes with full, title, and background options

const colorShade = (color, amount) => '#' + color.slice(1).match(/../g)
    .map(channel => Math.min(255, parseInt(channel, 16) + amount).toString(16).padStart(2, '0'))
    .join('');

let activePicker;
let pickerNode;

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
    const graphcanvas = globalThis.LGraphCanvas?.active_canvas || app.canvas;
    const nodes = (!graphcanvas.selected_nodes || Object.keys(graphcanvas.selected_nodes).length <= 1)
        ? [node]
        : Object.values(graphcanvas.selected_nodes);
    const titleColor = getSettings().autoShade ? colorShade(colorValue, 20) : colorValue;

    for (const n of nodes) {
        switch (colorType) {
            case 'full':
                if (n.setColorOption) {
                    n.setColorOption({ color: titleColor, bgcolor: colorValue });
                } else {
                    n.color = titleColor;
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

    node.setDirtyCanvas(true, true);
};

// Groups have a single color
const applyColorToGroup = (colorValue, group) => {
    if (group.setColorOption) {
        group.setColorOption({ groupcolor: colorValue });
    } else {
        group.color = colorValue;
    }
    app.canvas.setDirty(true, true);
};

const openPicker = (initialColor, apply, node, label) => {
    activePicker?.remove();
    const previousFocus = document.activeElement;
    const expanded = /^#[0-9a-f]{3}$/i.test(initialColor)
        ? '#' + [...initialColor.slice(1)].map(value => value + value).join('') : initialColor;
    const picker = createColorPicker(expanded, apply, app.ui.settings, label);
    picker.hidden = true;
    activePicker = picker;
    pickerNode = node;
    document.body.append(picker);
    picker.dialog.addEventListener('close', () => {
        picker.remove();
        if (activePicker === picker) {
            activePicker = null;
            pickerNode = null;
            if (previousFocus?.isConnected) previousFocus.focus();
            else app.canvas.canvas?.focus();
        }
    }, { once: true });
    picker.dialog.showModal();
};

// Wrap menu options in the "Custom Colors" submenu (or nothing if empty)
const customColorsMenu = (options) => options.length === 0 ? [] : [
    null, // separator
    { content: "🫶 Custom Colors", submenu: { options } },
];

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

    beforeRegisterNodeDef(nodeType) {
        const onRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            if (pickerNode === this) activePicker?.remove();
            return onRemoved?.apply(this, arguments);
        };
    },

    // New API: return items to append to node right-click menu
    getNodeMenuItems(node) {
        if (!isEnabled()) return [];

        const settings = getSettings();
        const options = [];

        const addOption = (label, type, initialColor) => options.push({
            content: label,
            callback: () => openPicker(
                initialColor, (color) => applyColorToNodes(color, type, node),
                node, `Custom ${type === 'bg' ? 'background' : type} color`,
            ),
        });

        if (settings.showFull) addOption("🫶 Custom Full", 'full', node.bgcolor);
        if (settings.showTitle) addOption("🫶 Custom Title", 'title', node.color);
        if (settings.showBG) addOption("🫶 Custom BG", 'bg', node.bgcolor);

        return customColorsMenu(options);
    },

    // Groups have no node menu hook; like the frontend's own Comfy.GroupOptions,
    // find the group under the mouse when the canvas menu opens.
    getCanvasMenuItems(canvas) {
        if (!isEnabled()) return [];

        const [x, y] = canvas.graph_mouse ?? [];
        const group = canvas.graph?.getGroupOnPos?.(x, y);
        if (!group) return [];

        const settings = getSettings();
        if (!settings.showFull && !settings.showBG) return [];

        return customColorsMenu([{
            content: "🫶 Custom Group Color",
            callback: () => openPicker(group.color, (color) => applyColorToGroup(color, group), null, 'Group color'),
        }]);
    },
});
