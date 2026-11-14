import { announceNotificationsChanged, postNotificationRead, useNotificationsChanged } from '../../hooks/notificationEvents';
import AdminLoader from '../../layouts/AdminLoader';
import { useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { ICONS_1113 } from '../../cdn';
import { djDate } from '../../utils/djangoFormat';
import css from './NotificationsPage.css?raw';

/* Student notifications (/notifications/): counters, filter tabs, search, expandable cards. */

const CATEGORY = {
  announcement: { icon: 'bi-megaphone-fill', tone: 'emerald' },
  course_user: { icon: 'bi-journal-bookmark-fill', tone: 'teal' },
  alert: { icon: 'bi-exclamation-triangle-fill', tone: 'rose' },
  reminder: { icon: 'bi-alarm-fill', tone: 'gold' },
};

const TABS = [
  { key: 'all', label: 'All', test: () => true },
  { key: 'unread', label: 'Unread', test: (n) => !n.is_read },
  { key: 'read', label: 'Read', test: (n) => n.is_read },
];

function timeAgo(iso) {
  if (!iso) return '';
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return '';
  const s = Math.max(0, (Date.now() - then.getTime()) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 604800) return `${Math.floor(s / 86400)}d ago`;
  return djDate(iso, 'd M Y');
}

function NotificationCard({ item, onRead, busy, index }) {
  const n = item.notification;
  const cat = CATEGORY[n.category_type] || CATEGORY.announcement;
  const [expanded, setExpanded] = useState(false);
  const long = (n.notification_body || '').length > 220;

  return (
    <article className={`sn-card sn-card--${cat.tone}${item.is_read ? '' : ' is-unread'}`} style={{ '--i': index }}>
      <span className="sn-card__icon" aria-hidden="true"><i className={`bi ${cat.icon}`}></i></span>
      <div className="sn-card__main">
        <div className="sn-card__top">
          <span className="sn-cat">{n.category_type_display}</span>
          <span className="sn-time" title={djDate(n.created_at, 'd M Y, h:i A')}>
            <i className="bi bi-clock"></i> {timeAgo(n.created_at)}
          </span>
        </div>
        <h3 className="sn-card__subject">
          {!item.is_read ? <span className="sn-dot" aria-label="Unread" /> : null}
          {n.subject_heading}
        </h3>
        <p className={`sn-card__body${long && !expanded ? ' is-clamped' : ''}`}>{n.notification_body}</p>
        {long ? (
          <button type="button" className="sn-more" onClick={() => setExpanded((v) => !v)} aria-expanded={expanded}>
            {expanded ? 'Show less' : 'Read more'} <i className={`bi ${expanded ? 'bi-chevron-up' : 'bi-chevron-down'}`}></i>
          </button>
        ) : null}
        <div className="sn-card__foot">
          <span className="sn-date"><i className="bi bi-calendar3"></i> {djDate(n.created_at, 'd M Y, h:i A')}</span>
          {item.is_read ? (
            <span className="sn-status is-read"><i className="bi bi-check2-all"></i> Read{item.read_at ? ` on ${djDate(item.read_at, 'd M Y, h:i A')}` : ''}</span>
          ) : (
            <button type="button" className="sn-btn sn-btn--primary sn-btn--sm" onClick={() => onRead(n.id)} disabled={busy}>
              <i className="bi bi-check2"></i> Mark as read
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

function NotificationsContent({ data, reload }) {
  // Injected once the data is loaded, i.e. after StudentLayout's CSS (same cascade order as the template).
  usePageAssets({ links: [ICONS_1113], css });
  const [tab, setTab] = useState('all');
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);

  const notifications = useMemo(() => (data.notifications || []).filter((i) => i.notification), [data]);
  const counts = useMemo(
    () => Object.fromEntries(TABS.map((t) => [t.key, notifications.filter(t.test).length])),
    [notifications],
  );
  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    const tabTest = TABS.find((t) => t.key === tab).test;
    return notifications.filter((i) => tabTest(i) && (!term || [
      i.notification.subject_heading, i.notification.notification_body, i.notification.category_type_display,
    ].join(' ').toLowerCase().includes(term)));
  }, [notifications, tab, query]);

  const markAsRead = async (notificationId) => {
    setBusy(true);
    try {
      await postNotificationRead(notificationId);
      announceNotificationsChanged('page'); // refresh the top-bar bell badge
      reload();
    } catch (error) {
      toast.error(error.message || 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  };

  const markAllRead = async () => {
    const unread = notifications.filter((i) => !i.is_read);
    if (!unread.length) return;
    setBusy(true);
    const loading = toast.loading('Marking all as read…');
    const results = await Promise.allSettled(unread.map((i) => postNotificationRead(i.notification.id)));
    const failed = results.filter((r) => r.status === 'rejected').length;
    if (failed < results.length) announceNotificationsChanged('page'); // once for the batch, not per item
    if (failed) toast.error(`${failed} notification${failed === 1 ? '' : 's'} could not be updated.`, { id: loading });
    else toast.success('All notifications marked as read.', { id: loading });
    setBusy(false);
    reload();
  };

  return (
    <div className="sn">
      <header className="sn-head">
        <div>
          <p className="sn-eyebrow">Inbox</p>
          <h2 className="sn-title">Notifications &amp; announcements</h2>
          <p className="sn-sub">Stay updated with the latest announcements and course reminders.</p>
        </div>
        {counts.unread ? (
          <button type="button" className="sn-btn sn-btn--soft" onClick={markAllRead} disabled={busy}>
            <i className="bi bi-check2-all"></i> Mark all as read
          </button>
        ) : null}
      </header>

      <section className="sn-summary" aria-label="Notification summary">
        {[
          { label: 'All notifications', value: counts.all, icon: 'bi-bell-fill', tone: 'emerald' },
          { label: 'Unread', value: counts.unread, icon: 'bi-envelope-fill', tone: 'gold' },
          { label: 'Read', value: counts.read, icon: 'bi-envelope-open-fill', tone: 'teal' },
        ].map((s, i) => (
          <div key={s.label} className={`sn-sum sn-sum--${s.tone}`} style={{ '--i': i }}>
            <span className="sn-sum__icon"><i className={`bi ${s.icon}`}></i></span>
            <div>
              <strong>{s.value}</strong>
              <small>{s.label}</small>
            </div>
          </div>
        ))}
      </section>

      <div className="sn-toolbar">
        <div className="sn-tabs" role="tablist" aria-label="Filter notifications">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              className={`sn-tab${tab === t.key ? ' is-active' : ''}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
              <span className="sn-tab__count">{counts[t.key]}</span>
            </button>
          ))}
        </div>
        <label className="sn-search">
          <i className="bi bi-search" aria-hidden="true"></i>
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search notifications…" aria-label="Search notifications" />
          {query ? (
            <button type="button" className="sn-search__clear" onClick={() => setQuery('')} aria-label="Clear search">
              <i className="bi bi-x-circle-fill"></i>
            </button>
          ) : null}
        </label>
      </div>

      {visible.length ? (
        <div className="sn-list">
          {visible.map((item, i) => (
            <NotificationCard key={item.id} item={item} index={i} onRead={markAsRead} busy={busy} />
          ))}
        </div>
      ) : (
        <div className="sn-empty">
          <span className="sn-empty__icon"><i className={`bi ${notifications.length ? 'bi-search' : 'bi-bell-slash'}`}></i></span>
          <strong>{notifications.length ? 'Nothing matches your filters' : 'All caught up!'}</strong>
          <small>{notifications.length ? 'Try another tab or search term.' : 'You have no new notifications at the moment.'}</small>
          {notifications.length && (query || tab !== 'all') ? (
            <button type="button" className="sn-btn sn-btn--soft" onClick={() => { setQuery(''); setTab('all'); }}>Reset filters</button>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default function NotificationsPage() {
  const { data, ready, reload } = usePageData('/student/notifications/');
  useNotificationsChanged('page', reload); // e.g. an item marked read from the bell
  if (!ready) return <AdminLoader />;
  return <NotificationsContent data={data} reload={reload} />;
}
