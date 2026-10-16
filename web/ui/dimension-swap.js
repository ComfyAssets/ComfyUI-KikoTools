import { createButton, createScope, mountTheme } from './core.js';

export function mountDimensionSwap(node, app) {
    if (node.swapScope && !node.swapScope.signal.aborted) return node.swapButtonWidget;
    const scope = createScope();
    node.swapScope = scope;
    const container = document.createElement('div');
    container.className = 'ca-tools ca-dimension-swap';
    const button = createButton('Swap W×H', 'ca-primary');
    button.setAttribute('aria-label', 'Swap width and height');
    button.title = 'Swap width and height';
    container.append(button);
    mountTheme(container, app.ui.settings, scope);
    scope.listen(button, 'click', () => node.swapDimensions());
    node.swapButtonWidget = node.addDOMWidget('swap_button', 'div', container, {
        serialize: false, hideOnZoom: false, getMinHeight: () => 46, getMaxHeight: () => 46,
    });
    scope.cleanup(() => container.remove());
    const onRemoved = node.onRemoved;
    node.onRemoved = function () {
        scope.dispose();
        return onRemoved?.apply(this, arguments);
    };
    return node.swapButtonWidget;
}
