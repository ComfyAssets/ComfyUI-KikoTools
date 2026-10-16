import { createScope, mountTheme, createButton } from './core.js';

let nextDialog = 0;

export function createDialog({ title, settings, fallbackFocus, onCancel }) {
    const scope = createScope();
    const element = document.createElement('dialog');
    element.id = `ca-dialog-${++nextDialog}`;
    element.className = 'ca-tools ca-dialog kikotools-dialog';
    const header = document.createElement('header');
    const heading = document.createElement('h2');
    heading.id = `${element.id}-title`;
    heading.textContent = title;
    element.setAttribute('aria-labelledby', heading.id);
    const brand = document.createElement('span');
    brand.textContent = 'ComfyAssets';
    header.append(heading, brand);
    const body = document.createElement('div');
    body.className = 'ca-dialog-body';
    const actions = document.createElement('footer');
    element.append(header, body, actions);
    mountTheme(element, settings, scope);
    let opener;
    const nativeClose = element.close.bind(element);
    const finish = reason => {
        if (scope.signal.aborted) return;
        scope.dispose();
        if (opener?.isConnected && opener !== document.body) opener.focus();
        else fallbackFocus?.focus();
        if (reason === 'cancel') onCancel?.();
    };
    element.close = (reason = 'dismiss') => {
        if (scope.signal.aborted) return;
        nativeClose(reason);
        finish(reason);
    };
    scope.cleanup(() => element.remove());
    scope.listen(element, 'close', () => finish(element.returnValue));
    scope.listen(element, 'cancel', event => {
        event.preventDefault();
        element.close('cancel');
    });
    scope.listen(element, 'keydown', event => event.stopPropagation());
    scope.listen(element, 'keyup', event => event.stopPropagation());
    return {
        element, scope, body, actions,
        close: element.close,
        open(initialFocus) {
            opener = document.activeElement;
            document.body.append(element);
            element.showModal();
            initialFocus?.focus();
        },
    };
}

export function createLegacyDialog(htmlContent, onOK, onCancel, settings, fallbackFocus) {
    const dialog = createDialog({ title: 'KikoTools', settings, fallbackFocus, onCancel });
    const form = document.createElement('form');
    form.id = `${dialog.element.id}-form`;
    form.innerHTML = htmlContent;
    dialog.body.append(form);
    const cancel = createButton('Cancel');
    const ok = createButton('OK', 'ca-primary');
    ok.type = 'submit';
    ok.setAttribute('form', form.id);
    dialog.actions.append(cancel, ok);
    dialog.scope.listen(cancel, 'click', () => dialog.close('cancel'));
    dialog.scope.listen(form, 'keydown', event => {
        if (event.key === 'Enter' && !event.isComposing && event.target.matches('select')) {
            event.preventDefault();
            event.stopPropagation();
            form.requestSubmit();
        }
    });
    dialog.scope.listen(form, 'submit', event => {
        event.preventDefault();
        onOK?.(dialog.element, [...form.querySelectorAll('input, select')].map(input => input.value));
        dialog.close('apply');
    });
    const firstInput = form.querySelector('input, select');
    dialog.open(firstInput);
    if (firstInput?.tagName === 'INPUT') firstInput.select();
    return dialog.element;
}
