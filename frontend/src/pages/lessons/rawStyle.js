/*
 * React's `style` prop cannot express `!important`, but several template elements use it
 * inline (e.g. style="max-width: 100% !important;"). `ref={rawStyle('...')}` applies the
 * template's inline style text verbatim. Ref callbacks are cached per text so React never
 * re-applies them on re-render.
 */
const cache = new Map();

export function rawStyle(cssText) {
  if (!cache.has(cssText)) {
    cache.set(cssText, (el) => {
      if (el) el.style.cssText = cssText;
    });
  }
  return cache.get(cssText);
}
