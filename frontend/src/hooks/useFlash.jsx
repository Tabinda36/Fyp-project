import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';

/*
 * Replacement for Django's `messages` framework with the same semantics:
 * a message is shown on the next page that renders (the same page for
 * "redirect to self", or the destination page after navigate()), and it is
 * gone after the following navigation.
 *
 *   const { addMessage } = useFlash();
 *   addMessage('success', 'Settings updated successfully!');
 *   navigate('/settings/');                       // optional
 *
 *   // in the page, render with the ORIGINAL template markup:
 *   const messages = useFlashMessages();
 *   messages.map(m => <div className={`alert alert-${bootstrapTag(m.tags)}`}>{m.message}</div>)
 *
 * `tags` uses Django level names: debug | info | success | warning | error.
 * Must be rendered inside <BrowserRouter>.
 */
const FlashContext = createContext(null);

export function FlashProvider({ children }) {
  const [queue, setQueue] = useState([]);
  const { pathname, search } = useLocation();
  const here = pathname + search;

  // A new action is a new "request": like Django, messages already displayed are consumed
  // and only the new ones are shown (prevents old + new stacking after a redirect-to-self).
  const addMessage = useCallback((tags, message) => {
    if (!message) return;
    setQueue((q) => [
      ...q.filter((m) => !m.shownOn),
      { id: `${Date.now()}-${Math.random()}`, tags: tags || 'info', message, shownOn: null },
    ]);
  }, []);

  /** Accepts the API's `messages: [{tags, message}]` payload. */
  const addMessages = useCallback(
    (list) => (list || []).forEach((m) => addMessage(m.tags || m.level, m.message)),
    [addMessage],
  );

  const markShown = useCallback((path) => {
    setQueue((q) => (q.some((m) => !m.shownOn) ? q.map((m) => (m.shownOn ? m : { ...m, shownOn: path })) : q));
  }, []);

  const dismiss = useCallback((id) => setQueue((q) => q.filter((m) => m.id !== id)), []);

  // On navigation, drop messages that were already displayed on another page.
  useEffect(() => {
    setQueue((q) => {
      const kept = q.filter((m) => !m.shownOn || m.shownOn === here);
      return kept.length === q.length ? q : kept;
    });
  }, [here]);

  const value = useMemo(
    () => ({ queue, addMessage, addMessages, markShown, dismiss, here }),
    [queue, addMessage, addMessages, markShown, dismiss, here],
  );
  return <FlashContext.Provider value={value}>{children}</FlashContext.Provider>;
}

export function useFlash() {
  const ctx = useContext(FlashContext);
  if (!ctx) throw new Error('useFlash must be used inside <FlashProvider>');
  return ctx;
}

/** Messages to render on the current page (marks them as displayed here). */
export function useFlashMessages() {
  const { queue, markShown, here } = useFlash();
  useEffect(() => {
    markShown(here);
  }, [queue, markShown, here]);
  return queue;
}

export const bootstrapTag = (tags) => (tags === 'error' ? 'danger' : tags || 'info');
