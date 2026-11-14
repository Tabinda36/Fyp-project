import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { apiFetch } from '../api/client';
import { useNotificationsChanged } from '../hooks/notificationEvents';

/*
 * Top-bar bell for admins. Shows reports waiting for review (the admin's "inbox")
 * and the latest notifications sent to students.
 * Data: /api/v1/admin/reports/ and /api/v1/admin/notifications/.
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

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState({ loading: true, error: false, pending: [], pendingCount: 0, sent: [] });
  const ref = useRef(null);
  const { pathname } = useLocation();

  const load = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: false }));
    try {
      const [reports, notes] = await Promise.all([
        apiFetch('/admin/reports/'),
        apiFetch('/admin/notifications/').catch(() => ({ dispatch_history: [] })),
      ]);
      const pending = (reports.reports || []).filter((r) => r.status === 'pending');
      setState({
        loading: false,
        error: false,
        pending: pending.slice(0, 5),
        pendingCount: Number(reports.pending_reports ?? pending.length) || 0,
        sent: (notes.dispatch_history || []).slice(0, 3),
      });
    } catch {
      setState((s) => ({ ...s, loading: false, error: true }));
    }
  }, []);

  // Badge count on load and whenever the admin changes page.
  useEffect(() => { load(); }, [load, pathname]);
  useNotificationsChanged('bell', load); // a report was answered/deleted
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

  const { loading, error, pending, pendingCount, sent } = state;

  return (
    <div className="adm-bell" ref={ref}>
      <button
        type="button"
        className={`adm-icon-btn adm-bell__btn${open ? ' is-open' : ''}`}
        aria-label={pendingCount ? `Notifications, ${pendingCount} pending` : 'Notifications'}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => { setOpen((v) => !v); if (!open) load(); }}
      >
        <i className={`bi ${open ? 'bi-bell-fill' : 'bi-bell'}`}></i>
        {pendingCount ? <span className="adm-bell__badge">{pendingCount > 9 ? '9+' : pendingCount}</span> : null}
      </button>

      {open ? (
        <div className="adm-bell__menu" role="menu">
          <header className="adm-bell__head">
            <div>
              <strong>Notifications</strong>
              <small>{pendingCount ? `${pendingCount} report${pendingCount === 1 ? '' : 's'} need attention` : 'You are all caught up'}</small>
            </div>
            <button type="button" className="adm-bell__refresh" onClick={load} aria-label="Refresh" disabled={loading}>
              <i className={`bi bi-arrow-clockwise${loading ? ' is-spinning' : ''}`}></i>
            </button>
          </header>

          <div className="adm-bell__body">
            {error ? (
              <div className="adm-bell__empty">
                <i className="bi bi-wifi-off"></i>
                <span>Couldn&apos;t load notifications.</span>
                <button type="button" className="adm-bell__retry" onClick={load}>Try again</button>
              </div>
            ) : loading && !pending.length && !sent.length ? (
              <div className="adm-bell__loading"><span className="adm-loader__ring adm-loader__ring--sm" /></div>
            ) : (
              <>
                <p className="adm-bell__section">Pending reports</p>
                {pending.length ? (
                  pending.map((r) => (
                    <Link key={r.id} to="/admin_reports/" className="adm-bell__item" role="menuitem">
                      <span className="adm-bell__icon is-warn"><i className="bi bi-flag-fill"></i></span>
                      <span className="adm-bell__text">
                        <strong>{r.problem_title || r.problem_type_display || 'New report'}</strong>
                        <small>{r.student_name || 'A student'}{r.course_name ? ` · ${r.course_name}` : ''}</small>
                      </span>
                      <span className="adm-bell__time">{timeAgo(r.created_at)}</span>
                    </Link>
                  ))
                ) : (
                  <div className="adm-bell__empty adm-bell__empty--sm">
                    <i className="bi bi-check2-circle"></i>
                    <span>No pending reports.</span>
                  </div>
                )}

                {sent.length ? (
                  <>
                    <p className="adm-bell__section">Recently sent</p>
                    {sent.map((n) => (
                      <Link key={n.id} to="/admin_notifications/" className="adm-bell__item" role="menuitem">
                        <span className="adm-bell__icon"><i className="bi bi-send-fill"></i></span>
                        <span className="adm-bell__text">
                          <strong>{n.subject_heading}</strong>
                          <small>{[n.get_category_type_display, n.get_target_recipient_display].filter(Boolean).join(' · ')}</small>
                        </span>
                        <span className="adm-bell__time">{timeAgo(n.created_at)}</span>
                      </Link>
                    ))}
                  </>
                ) : null}
              </>
            )}
          </div>

          <footer className="adm-bell__foot">
            <Link to="/admin_reports/">Review reports</Link>
            <Link to="/admin_notifications/">Send notification <i className="bi bi-arrow-right"></i></Link>
          </footer>
        </div>
      ) : null}
    </div>
  );
}
