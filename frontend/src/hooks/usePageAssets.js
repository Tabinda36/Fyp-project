import { useLayoutEffect } from 'react';

/*
 * Reproduces how a Django template "owned" the whole document:
 *  - <link> stylesheets the template loaded (same CDN URLs/versions)
 *  - its inline <style> CSS (imported verbatim with `?raw`)
 *  - a <body> class and the <title>
 * Everything is added on mount and removed on unmount, so one page's global CSS
 * (e.g. `body { ... }` overrides) never leaks into another route — exactly like
 * separate server-rendered pages.
 *
 * Cascade order matches the templates: layout assets (base template <head>) always
 * come BEFORE page assets (child template <style> inside the block). React runs
 * child layout-effects first, so order is enforced with a marker node rather than
 * relying on insertion time:  <head> … [layout layer] <marker> [page layer]
 *
 * Links are reference-counted so a layout and a page that both need the same
 * stylesheet don't load it twice or flash when navigating.
 */

let marker = null;
function getMarker() {
  if (!marker || !marker.isConnected) {
    marker = document.createElement('meta');
    marker.name = 'alvix-layout-assets-end';
    document.head.appendChild(marker);
  }
  return marker;
}

function insert(el, layer) {
  if (layer === 'layout') document.head.insertBefore(el, getMarker());
  else {
    getMarker();
    document.head.appendChild(el);
  }
}

const linkRefs = new Map(); // href -> { el, count }

function acquireLink(href, layer) {
  const entry = linkRefs.get(href);
  if (entry) {
    entry.count += 1;
    // A layout-level stylesheet must sit in the layout layer even if a page requested it first.
    if (layer === 'layout') document.head.insertBefore(entry.el, getMarker());
    return;
  }
  const el = document.createElement('link');
  el.rel = 'stylesheet';
  el.href = href;
  el.dataset.pageAsset = layer;
  insert(el, layer);
  linkRefs.set(href, { el, count: 1 });
}

function releaseLink(href) {
  const entry = linkRefs.get(href);
  if (!entry) return;
  entry.count -= 1;
  if (entry.count <= 0) {
    entry.el.remove();
    linkRefs.delete(href);
  }
}

/**
 * @param {object} opts
 * @param {string[]} [opts.links]  CDN stylesheet URLs the template loaded
 * @param {string}   [opts.css]    the template's <style> CSS, verbatim
 * @param {string}   [opts.bodyClass]
 * @param {string}   [opts.title]
 * @param {'page'|'layout'} [opts.layer='page']  layouts pass 'layout'
 */
export function usePageAssets({ links = [], css = '', bodyClass = '', title, layer = 'page' } = {}) {
  const linksKey = links.join('|');

  useLayoutEffect(() => {
    const hrefs = linksKey ? linksKey.split('|') : [];
    hrefs.forEach((href) => acquireLink(href, layer));

    let styleEl = null;
    if (css) {
      styleEl = document.createElement('style');
      styleEl.dataset.pageAsset = layer;
      styleEl.textContent = css;
      insert(styleEl, layer);
    }

    return () => {
      hrefs.forEach(releaseLink);
      if (styleEl) styleEl.remove();
    };
  }, [linksKey, css, layer]);

  useLayoutEffect(() => {
    const classes = bodyClass.split(/\s+/).filter(Boolean);
    classes.forEach((c) => document.body.classList.add(c));
    return () => classes.forEach((c) => document.body.classList.remove(c));
  }, [bodyClass]);

  useLayoutEffect(() => {
    if (title) document.title = title;
  }, [title]);
}
