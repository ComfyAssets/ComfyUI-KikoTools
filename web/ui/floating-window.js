export function fitWindowRect(rect, viewport) {
    const width = Math.min(Math.max(280, rect.width), Math.max(1, viewport.width - 16));
    const height = Math.min(Math.max(200, rect.height), Math.max(1, viewport.height - 16));
    return {
        width, height,
        x: Math.max(8, Math.min(rect.x, viewport.width - width - 8)),
        y: Math.max(8, Math.min(rect.y, viewport.height - height - 8)),
    };
}

export function mountFloatingWindow(element, scope, onClose) {
    const stylesheet = new URL('./window.css', import.meta.url).href;
    if (![...document.querySelectorAll('link[rel="stylesheet"]')].some(link => link.href === stylesheet)) {
        const link = document.createElement('link');
        Object.assign(link, { rel: 'stylesheet', href: stylesheet });
        document.head.append(link);
    }
    let gesture;
    const viewport = () => ({ width: innerWidth, height: innerHeight });
    const move = (x, y) => {
        const rect = element.getBoundingClientRect();
        const next = fitWindowRect({ x, y, width: rect.width, height: rect.height }, viewport());
        element.style.left = `${next.x}px`;
        element.style.top = `${next.y}px`;
        element.style.right = 'auto';
    };
    const resize = (width, height) => {
        const rect = element.getBoundingClientRect();
        const next = fitWindowRect({ x: rect.x, y: rect.y, width, height }, viewport());
        element.style.setProperty('--ca-window-width', `${next.width}px`);
        element.style.setProperty('--ca-window-height', `${next.height}px`);
        move(next.x, next.y);
    };
    const end = () => {
        if (gesture && element.hasPointerCapture(gesture.id)) element.releasePointerCapture(gesture.id);
        gesture = null;
        element.classList.remove('ca-dragging');
    };
    scope.listen(element, 'pointerdown', event => {
        const handle = event.target.closest('[data-window-move], [data-window-resize]');
        if (!handle || event.button !== 0) return;
        const rect = element.getBoundingClientRect();
        gesture = { id: event.pointerId, kind: handle.hasAttribute('data-window-resize') ? 'resize' : 'move', rect, x: event.clientX, y: event.clientY };
        handle.focus();
        element.setPointerCapture(event.pointerId);
        element.classList.add('ca-dragging');
        event.preventDefault();
    });
    scope.listen(element, 'pointermove', event => {
        if (!gesture || event.pointerId !== gesture.id) return;
        const dx = event.clientX - gesture.x;
        const dy = event.clientY - gesture.y;
        if (gesture.kind === 'resize') resize(gesture.rect.width + dx, gesture.rect.height + dy);
        else move(gesture.rect.x + dx, gesture.rect.y + dy);
    });
    for (const event of ['pointerup', 'pointercancel', 'lostpointercapture']) scope.listen(element, event, end);
    scope.listen(element, 'keydown', event => {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); onClose(); return; }
        const handle = event.target.closest('[data-window-move], [data-window-resize]');
        if (!handle || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        const delta = event.shiftKey ? 40 : 16;
        const dx = event.key === 'ArrowLeft' ? -delta : event.key === 'ArrowRight' ? delta : 0;
        const dy = event.key === 'ArrowUp' ? -delta : event.key === 'ArrowDown' ? delta : 0;
        const rect = element.getBoundingClientRect();
        if (handle.hasAttribute('data-window-resize')) resize(rect.width + dx, rect.height + dy);
        else move(rect.x + dx, rect.y + dy);
    });
    const keepReachable = () => {
        if (element.hidden) return;
        const rect = element.getBoundingClientRect();
        move(rect.x, rect.y);
    };
    scope.listen(window, 'resize', keepReachable);
    const observer = new ResizeObserver(keepReachable);
    observer.observe(element);
    scope.cleanup(() => { observer.disconnect(); end(); });
    return { fit: keepReachable };
}
