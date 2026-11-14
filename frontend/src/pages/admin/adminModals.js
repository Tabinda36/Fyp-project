/*
 * Small DOM helpers for the admin core pages.
 *
 * rawStyle: React's `style` prop cannot express `!important`, but several admin
 * templates use it inline (style="color: #047857 !important;"). `ref={rawStyle('...')}`
 * applies the template's inline style text verbatim (cached per text so React never
 * re-applies it on re-render).
 *
 * hideModal / cleanupModals: Bootstrap modals opened through `data-bs-toggle` are
 * closed after a successful submit (the template page reloaded instead), and are
 * disposed on unmount so no backdrop or `modal-open` body class leaks into the next route.
 */
const styleRefs = new Map();

export function rawStyle(cssText) {
  if (!styleRefs.has(cssText)) {
    styleRefs.set(cssText, (el) => {
      if (el) el.style.cssText = cssText;
    });
  }
  return styleRefs.get(cssText);
}

export function hideModal(el) {
  const Modal = window.bootstrap?.Modal;
  if (el && Modal) Modal.getOrCreateInstance(el).hide();
}

export function cleanupModals(elements) {
  const Modal = window.bootstrap?.Modal;
  elements.forEach((el) => {
    if (el && Modal) Modal.getInstance(el)?.dispose();
  });
  document.querySelectorAll('.modal-backdrop').forEach((b) => b.remove());
  document.body.classList.remove('modal-open');
  document.body.style.removeProperty('overflow');
  document.body.style.removeProperty('padding-right');
}
