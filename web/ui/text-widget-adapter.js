export function watchRendererTextareas(scope, graph, autocomplete) {
    const bridges = new Map();
    const detachMissing = () => {
        for (const [textarea, bridge] of bridges) {
            if (textarea.isConnected) continue;
            autocomplete.detachFromWidget(bridge);
            bridges.delete(textarea);
        }
    };
    scope.listen(document, 'focusin', event => {
        const textarea = event.target;
        if (!(textarea instanceof HTMLTextAreaElement) || textarea.readOnly || textarea.disabled) return;
        const owner = textarea.closest('[node-id]');
        const node = owner && graph.getNodeById(owner.getAttribute('node-id'));
        if (!node) return;
        const label = textarea.labels?.[0]?.textContent.trim();
        const widget = node.widgets?.find(widget => (widget.label || widget.name) === label && widget.inputEl?.tagName === 'TEXTAREA');
        if (!widget || widget.inputEl === textarea || widget.inputEl.readOnly) return;
        let bridge = bridges.get(textarea);
        if (!bridge) {
            bridge = { inputEl: textarea };
            bridges.set(textarea, bridge);
        }
        autocomplete.attachToWidget(bridge, node);
    });
    const observer = new MutationObserver(detachMissing);
    observer.observe(document.body, { childList: true, subtree: true });
    scope.cleanup(() => {
        observer.disconnect();
        for (const bridge of bridges.values()) autocomplete.detachFromWidget(bridge);
        bridges.clear();
    });
}
