import { useSyncExternalStore } from 'react';

/*
 * Tiny shared store for "the current page's data request failed" (server/network error).
 * usePageData publishes it; AdminLoader (shown while a page has no data) reads it and
 * swaps the spinner for an error card with Retry, so a failed load never spins forever.
 */
let current = null;
const listeners = new Set();

export function setPageError(value) {
  current = value;
  listeners.forEach((listener) => listener());
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function usePageError() {
  return useSyncExternalStore(subscribe, () => current, () => null);
}
