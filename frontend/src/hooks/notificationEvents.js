import { useEffect, useRef } from 'react';
import { getCookie } from '../api/client';

/*
 * Keeps the top-bar bell and the Notifications page in sync: whoever marks something
 * as read announces it, and the other side reloads.
 */
const EVENT = 'alvix:notifications-changed';

export function announceNotificationsChanged(source) {
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { source } }));
}

/**
 * POST /notifications/read/<notification_id>/ -> {status: 'success'}.
 * Throws on HTTP errors, non-JSON replies (e.g. the login page after the session expired)
 * and {status: 'error'}, so callers can roll back and show a real message.
 */
export async function postNotificationRead(notificationId) {
  let response;
  try {
    response = await fetch(`/notifications/read/${notificationId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') || '', 'Content-Type': 'application/json' },
      credentials: 'same-origin',
    });
  } catch {
    throw new Error('Server is not responding. Please try again.');
  }
  // @login_required answers an expired session with a redirect to the login page.
  if (response.redirected || response.status === 401) {
    window.location.assign(`/login/?next=${encodeURIComponent(window.location.pathname)}`);
    throw new Error('Your session has expired. Please log in again.');
  }
  if (response.status === 403) throw new Error('Your session has expired. Please refresh the page and try again.');
  if (response.status === 404) throw new Error('This notification no longer exists.');
  const isJson = (response.headers.get('content-type') || '').includes('application/json');
  const result = isJson ? await response.json().catch(() => ({})) : {};
  if (!response.ok || result.status !== 'success') throw new Error(result.message || 'Something went wrong.');
  return result;
}

/** Calls `onChange` when another component (not `source`) changed notification state. */
export function useNotificationsChanged(source, onChange) {
  const handler = useRef(onChange);
  useEffect(() => {
    handler.current = onChange;
  }, [onChange]);

  useEffect(() => {
    const listener = (event) => {
      if (event.detail?.source !== source) handler.current?.();
    };
    window.addEventListener(EVENT, listener);
    return () => window.removeEventListener(EVENT, listener);
  }, [source]);
}
