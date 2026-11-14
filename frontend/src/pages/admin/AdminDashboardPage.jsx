import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { usePageData } from '../../hooks/usePageData';
import { usePageAssets } from '../../hooks/usePageAssets';
import rawCss from './AdminDashboardPage.css?raw';
import AdminLoader from '../../layouts/AdminLoader';

/*
 * Admin dashboard home (default `{% block admin_content %}` of `admin_db/admindashboard.html`),
 * redesigned as a premium overview in the same ALVIX green + gold theme.
 * Data: /api/v1/admin/dashboard/ -> total_courses, total_students, pending_reports_count, total_enrollments.
 */

const STATS = [
  { key: 'total_courses', label: 'Active Courses', icon: 'bi-journal-bookmark-fill', tone: 'emerald', to: '/courses_info/', cta: 'View courses' },
  { key: 'total_students', label: 'Enrolled Students', icon: 'bi-mortarboard-fill', tone: 'teal', to: '/user_management/', cta: 'Manage users' },
  { key: 'pending_reports_count', label: 'Pending Reports', icon: 'bi-flag-fill', tone: 'amber', to: '/admin_reports/', cta: 'Review reports' },
  { key: 'total_enrollments', label: 'Total Enrollments', icon: 'bi-check-circle-fill', tone: 'gold', to: '/analytics/', cta: 'See analytics' },
];

const ACTIONS = [
  { to: '/add_course/', icon: 'bi-plus-circle-fill', title: 'Add Course', text: 'Create a new course and its levels.' },
  { to: '/courses_info/', icon: 'bi-collection-fill', title: 'Course List', text: 'Browse, edit and organise courses.' },
  { to: '/user_management/', icon: 'bi-people-fill', title: 'User Management', text: 'Manage students and access.' },
  { to: '/admin_reports/', icon: 'bi-robot', title: 'Reports', text: 'Resolve flagged AI content.' },
  { to: '/analytics/', icon: 'bi-bar-chart-fill', title: 'Analytics', text: 'Track learning performance.' },
  { to: '/admindashboard/avatar-settings/', icon: 'bi-person-badge-fill', title: 'Avatar & AI Teacher', text: 'Tune the AI teacher experience.' },
];

function greeting(date) {
  const h = date.getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

/** Animates 0 -> target once (respects reduced motion). */
function CountUp({ value }) {
  const target = toNumber(value);
  const [shown, setShown] = useState(0);

  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce || target === 0) {
      setShown(target);
      return undefined;
    }
    let frame;
    const start = performance.now();
    const duration = 1100;
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1);
      setShown(Math.round(target * (1 - (1 - p) ** 3)));
      if (p < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  return <>{shown.toLocaleString()}</>;
}

export default function AdminDashboardPage() {
  usePageAssets({ css: rawCss });
  const { data, ready } = usePageData('/admin/dashboard/');
  const [now] = useState(() => new Date());
  if (!ready) return <AdminLoader label="Loading dashboard" />;

  const students = toNumber(data.total_students);
  const enrollments = toNumber(data.total_enrollments);
  const courses = toNumber(data.total_courses);
  const pending = toNumber(data.pending_reports_count);
  const perStudent = students ? (enrollments / students).toFixed(1) : '0.0';
  const perCourse = courses ? (enrollments / courses).toFixed(1) : '0.0';
  const dateLabel = now.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  return (
    <div className="adm-dash">
      {/* Hero */}
      <section className="adm-hero">
        <div className="adm-hero__orb adm-hero__orb--one" aria-hidden="true" />
        <div className="adm-hero__orb adm-hero__orb--two" aria-hidden="true" />
        <div className="adm-hero__grid" aria-hidden="true" />

        <div className="adm-hero__body">
          <span className="adm-hero__date"><i className="bi bi-calendar3"></i> {dateLabel}</span>
          <h2 className="adm-hero__title">
            {greeting(now)}, <span>Admin!</span>
          </h2>
          <p className="adm-hero__text">Manage courses, users, and analytics seamlessly with ALVIX.</p>
          <div className="adm-hero__actions">
            <Link to="/add_course/" className="adm-btn adm-btn--gold">
              <i className="bi bi-plus-lg"></i> Add new course
            </Link>
            <Link to="/analytics/" className="adm-btn adm-btn--ghost">
              <i className="bi bi-graph-up-arrow"></i> View analytics
            </Link>
          </div>
        </div>

        <div className="adm-hero__badge" aria-hidden="true">
          <div className="adm-hero__ring">
            <i className="bi bi-mortarboard-fill"></i>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="adm-stats" aria-label="Platform statistics">
        {STATS.map((s, i) => (
          <Link key={s.key} to={s.to} className={`adm-stat adm-stat--${s.tone}`} style={{ '--i': i }}>
            <div className="adm-stat__top">
              <span className="adm-stat__icon"><i className={`bi ${s.icon}`}></i></span>
              <span className="adm-stat__arrow" aria-hidden="true"><i className="bi bi-arrow-up-right"></i></span>
            </div>
            <span className="adm-stat__value"><CountUp value={data[s.key]} /></span>
            <span className="adm-stat__label">{s.label}</span>
            <span className="adm-stat__cta">{s.cta} <i className="bi bi-chevron-right"></i></span>
          </Link>
        ))}
      </section>

      <div className="adm-columns">
        {/* Quick actions */}
        <section className="adm-panel adm-panel--actions">
          <header className="adm-panel__head">
            <div>
              <p className="adm-panel__eyebrow">Shortcuts</p>
              <h3 className="adm-panel__title">Quick actions</h3>
            </div>
          </header>
          <div className="adm-actions">
            {ACTIONS.map((a, i) => (
              <Link key={a.to} to={a.to} className="adm-action" style={{ '--i': i }}>
                <span className="adm-action__icon"><i className={`bi ${a.icon}`}></i></span>
                <span className="adm-action__body">
                  <strong>{a.title}</strong>
                  <small>{a.text}</small>
                </span>
                <i className="bi bi-arrow-right adm-action__go" aria-hidden="true"></i>
              </Link>
            ))}
          </div>
        </section>

        {/* Snapshot */}
        <section className="adm-panel adm-panel--snapshot">
          <header className="adm-panel__head">
            <div>
              <p className="adm-panel__eyebrow">Overview</p>
              <h3 className="adm-panel__title">Platform snapshot</h3>
            </div>
          </header>

          <div className={`adm-health ${pending ? 'is-warn' : 'is-ok'}`}>
            <span className="adm-health__icon">
              <i className={`bi ${pending ? 'bi-exclamation-triangle-fill' : 'bi-shield-check'}`}></i>
            </span>
            <div>
              <strong>{pending ? `${pending} report${pending === 1 ? '' : 's'} need review` : 'All clear'}</strong>
              <small>{pending ? 'Flagged content is waiting for a decision.' : 'No pending reports right now.'}</small>
            </div>
            {pending ? <Link to="/admin_reports/" className="adm-health__link">Review</Link> : null}
          </div>

          <ul className="adm-metrics">
            <li>
              <span>Enrollments per student</span>
              <strong>{perStudent}</strong>
            </li>
            <li>
              <span>Enrollments per course</span>
              <strong>{perCourse}</strong>
            </li>
            <li>
              <span>Courses available</span>
              <strong>{courses.toLocaleString()}</strong>
            </li>
          </ul>

          <Link to="/analytics/" className="adm-btn adm-btn--soft adm-btn--block">
            Open full analytics <i className="bi bi-arrow-right"></i>
          </Link>
        </section>
      </div>
    </div>
  );
}

