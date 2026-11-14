import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiFetch } from '../api/client';
import { announceNotificationsChanged, postNotificationRead, useNotificationsChanged } from '../hooks/notificationEvents';

/*
 * Student top-bar bell: latest announcements with an unread badge.
 * Data: /api/v1/student/notifications/ ; marking read uses the existing
 * POST /notifications/read/<notification_id>/ endpoint (same as the dashboard popup).
 */

function timeAgo(iso) {
  if (!iso) return '';
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return '';
  const s = Math.max(0, (Date.now() - then.getTime()) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 604800) return `${Math.floor(s / 86400)}d ago`;
  return then.toLocaleDateString();
}

export default function StudentBell() {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState({ loading: true, error: false, items: [] });
  const ref = useRef(null);
  const { pathname } = useLocation();

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: false }));
    try {
      const res = await apiFetch('/student/notifications/');
      setState({ loading: false, error: false, items: (res.notifications || []).filter((n) => n.notification) });
    } catch {
      setState((s) => ({ ...s, loading: false, error: true }));
    }
  }, []);

  useEffect(() => { load(); }, [load, pathname]);
  useNotificationsChanged('bell', load); // marked read on the Notifications page
  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const { loading, error, items } = state;
  const unread = items.filter((n) => !n.is_read).length;

  // Optimistic: flip to read at once, then put back anything the server did not save.
  const markIds = async (pending) => {
    if (!pending.length) return;
    const ids = new Set(pending.map((n) => n.id));
    setState((s) => ({ ...s, items: s.items.map((n) => (ids.has(n.id) ? { ...n, is_read: true } : n)) }));
    const results = await Promise.allSettled(pending.map((n) => postNotificationRead(n.notification.id)));
    const failed = new Set(pending.filter((_, i) => results[i].status === 'rejected').map((n) => n.id));
    if (failed.size) {
      setState((s) => ({ ...s, items: s.items.map((n) => (failed.has(n.id) ? { ...n, is_read: false } : n)) }));
      const first = results.find((r) => r.status === 'rejected');
      toast.error(first?.reason?.message || 'Could not mark the notification as read.');
    }
    if (failed.size < pending.length) announceNotificationsChanged('bell'); // refresh the Notifications page / dashboard card
  };

  const readOne = (item) => {
    if (!item.is_read) markIds([item]);
  };

  const readAll = () => markIds(items.filter((n) => !n.is_read));

  return (
    <div className="adm-bell" ref={ref}>
      <button
        type="button"
        className={`adm-icon-btn adm-bell__btn${open ? ' is-open' : ''}`}
        aria-label={unread ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => { setOpen((v) => !v); if (!open) load(); }}
      >
        <i className={`bi ${open ? 'bi-bell-fill' : 'bi-bell'}`}></i>
        {unread ? <span className="adm-bell__badge">{unread > 9 ? '9+' : unread}</span> : null}
      </button>

      {open ? (
        <div className="adm-bell__menu" role="menu">
          <header className="adm-bell__head">
            <div>
              <strong>Notifications</strong>
              <small>{unread ? `${unread} unread announcement${unread === 1 ? '' : 's'}` : 'You are all caught up'}</small>
            </div>
            {unread ? (
              <button type="button" className="adm-bell__markall" onClick={readAll}>Mark all read</button>
            ) : (
              <button type="button" className="adm-bell__refresh" onClick={load} aria-label="Refresh" disabled={loading}>
                <i className={`bi bi-arrow-clockwise${loading ? ' is-spinning' : ''}`}></i>
              </button>
            )}
          </header>

          <div className="adm-bell__body">
            {error ? (
              <div className="adm-bell__empty">
                <i className="bi bi-wifi-off"></i>
                <span>Couldn&apos;t load notifications.</span>
                <button type="button" className="adm-bell__retry" onClick={load}>Try again</button>
              </div>
            ) : loading && !items.length ? (
              <div className="adm-bell__loading"><span className="adm-loader__ring adm-loader__ring--sm" /></div>
            ) : items.length ? (
              items.slice(0, 6).map((item) => (
                <Link
                  key={item.id}
                  to="/notifications/"
                  className={`adm-bell__item${item.is_read ? '' : ' is-unread'}`}
                  role="menuitem"
                  onClick={() => readOne(item)}
                >
                  <span className="adm-bell__icon"><i className="bi bi-megaphone-fill"></i></span>
                  <span className="adm-bell__text">
                    <strong>{item.notification.subject_heading}</strong>
                    <small>{item.notification.category_type_display || item.notification.notification_body}</small>
                  </span>
                  <span className="adm-bell__time">{timeAgo(item.notification.created_at)}</span>
                </Link>
              ))
            ) : (
              <div className="adm-bell__empty">
                <i className="bi bi-bell-slash"></i>
                <span>No announcements yet.</span>
              </div>
            )}
          </div>

          <footer className="adm-bell__foot">
            <Link to="/reports/">Report a problem</Link>
            <Link to="/notifications/">View all <i className="bi bi-arrow-right"></i></Link>
          </footer>
        </div>
      ) : null}
    </div>
  );
}
