import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiFetch } from '../api/client';
import { usePageAssets } from '../hooks/usePageAssets';
import { useAuth } from '../hooks/useAuth';
import { BOOTSTRAP_533, FONT_ADMIN, ICONS_1113, LOGO_LIGHT } from '../cdn';
import shellCss from './AdminLayout.css?raw';
import shellExtrasCss from './AdminLayoutExtras.css?raw';
import studentCss from './StudentLayout.css?raw';
import studentShellCss from './StudentShell.css?raw';
import studentDarkCss from './StudentDarkOverrides.css?raw';
import StudentBell from './StudentBell';

/*
 * Student shell: same structure as the admin console (logo sidebar, top bar with
 * theme toggle, notification bell and profile dropdown, slide-in drawer on phones).
 * StudentLayout.css still provides the shared component classes the student pages use
 * (.dashboard-card, .green-btn, .topbar, body.dark-mode …).
 */
const css = shellCss + shellExtrasCss + studentCss + studentShellCss + studentDarkCss;

const DEFAULT_AVATAR =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150' viewBox='0 0 24 24' fill='%231B5E20'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z'/%3E%3C/svg%3E";

// `match`: path prefixes that mark the item active (same as the template's url_name checks,
// plus the pages reached from My Courses so the student always sees where they are).
const NAV = [
  {
    title: 'Learning',
    items: [
      { to: '/dashboard/', icon: 'bi-grid-1x2-fill', label: 'Dashboard', match: ['/dashboard/'] },
      { to: '/mycourse/', icon: 'bi-book-fill', label: 'My Courses', match: ['/mycourse/', '/course_content/', '/course-content/', '/course/', '/certificate/', '/daily-lesson/', '/daily_lesson/', '/quiz/', '/assignment/'] },
      { to: '/performance/', icon: 'bi-graph-up-arrow', label: 'Performance', match: ['/performance/'] },
    ],
  },
  {
    title: 'Account',
    items: [
      { to: '/profile/', icon: 'bi-person-fill', label: 'Profile', match: ['/profile/'] },
      { to: '/notifications/', icon: 'bi-bell-fill', label: 'Notifications', match: ['/notifications/'] },
      { to: '/reports/', icon: 'bi-flag-fill', label: 'Reports', match: ['/reports/'] },
      { to: '/settings/', icon: 'bi-gear-fill', label: 'Settings', match: ['/settings/'] },
    ],
  },
];

const TITLES = [
  ['/dashboard', 'Dashboard'],
  ['/mycourse', 'My Courses'],
  ['/course_content', 'Course Content'],
  ['/course-content', 'Course Content'],
  ['/performance', 'Performance'],
  ['/profile', 'Profile'],
  ['/notifications', 'Notifications'],
  ['/reports', 'Reports'],
  ['/settings', 'Settings'],
  ['/generate_course', 'University Tiers'],
  ['/daily-lesson', 'Lesson'],
  ['/daily_lesson', 'Lesson'],
  ['/assignment', 'Assignment'],
  ['/quiz', 'Quiz'],
  ['/assessment', 'Assessment'],
  ['/certificate', 'Certificate'],
  ['/course/', 'My Courses'],
  ['/enroll-level', 'University Tiers'],
];

function pageTitle(pathname) {
  const hit = TITLES.find(([prefix]) => pathname.startsWith(prefix));
  return hit ? hit[1] : 'ALVIX';
}

/** Student theme comes from their saved settings; the toggle saves it back to /student/settings/. */
function useStudentTheme() {
  const { user, setUser } = useAuth();
  const saved = user?.settings?.theme === 'Dark' ? 'dark' : 'light';
  const [override, setOverride] = useState(null);
  const theme = override || saved;

  useLayoutEffect(() => {
    if (theme === 'dark') document.documentElement.setAttribute('data-bs-theme', 'dark');
    else document.documentElement.removeAttribute('data-bs-theme');
    return () => document.documentElement.removeAttribute('data-bs-theme');
  }, [theme]);

  async function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark';
    setOverride(next);
    try {
      // The form posts every field; without the saved values we would switch the student's
      // notifications/privacy off. Load them first when the auth payload has none.
      const s = user?.settings || (await apiFetch('/student/settings/')).form || {};
      const res = await apiFetch('/student/settings/', {
        method: 'POST',
        body: {
          theme: next === 'dark' ? 'Dark' : 'Light',
          email_notifications: Boolean(s.email_notifications),
          ai_notifications: Boolean(s.ai_notifications),
          public_profile: Boolean(s.public_profile),
        },
      });
      if (res?.user) setUser(res.user);
      setOverride(null);
    } catch {
      setOverride(null);
      toast.error('Could not save your theme. Please try again.');
    }
  }

  return [theme, toggle];
}

function ProfileMenu() {
  const { user } = useAuth();
  const profile = user?.profile || {};
  const name = profile.full_name || user?.full_name || user?.username || 'Student';
  const photo = profile.profile_picture || DEFAULT_AVATAR;
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const { pathname } = useLocation();

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

  return (
    <div className="adm-profile" ref={ref}>
      <button type="button" className={`adm-profile__btn${open ? ' is-open' : ''}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
        <img src={photo} alt="" className="adm-profile__avatar" />
        <span className="adm-profile__meta">
          <strong>{name}</strong>
          <small>{profile.student_id ? `ID ${profile.student_id}` : 'Student'}</small>
        </span>
        <i className="bi bi-chevron-down adm-profile__chev" aria-hidden="true"></i>
      </button>

      {open ? (
        <div className="adm-profile__menu" role="menu">
          <div className="adm-profile__card">
            <img src={photo} alt="" className="adm-profile__avatar adm-profile__avatar--lg" />
            <div>
              <strong>{name}</strong>
              <small>{user?.email}</small>
              <span className="adm-profile__badge">{profile.student_id ? `Student · ${profile.student_id}` : 'ALVIX Student'}</span>
            </div>
          </div>
          <Link role="menuitem" to="/profile/"><i className="bi bi-person"></i> My profile</Link>
          <Link role="menuitem" to="/mycourse/"><i className="bi bi-book"></i> My courses</Link>
          <Link role="menuitem" to="/performance/"><i className="bi bi-graph-up-arrow"></i> Performance</Link>
          <Link role="menuitem" to="/settings/"><i className="bi bi-gear"></i> Settings</Link>
          <div className="adm-profile__sep" />
          <Link role="menuitem" to="/logout/" className="is-danger"><i className="bi bi-box-arrow-right"></i> Logout</Link>
        </div>
      ) : null}
    </div>
  );
}

export default function StudentLayout({ children }) {
  const { pathname } = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const [theme, toggleTheme] = useStudentTheme();
  const dark = theme === 'dark';

  usePageAssets({
    links: [BOOTSTRAP_533, ICONS_1113, FONT_ADMIN],
    css,
    bodyClass: dark ? 'dark-mode adm-theme-dark st-body' : 'st-body',
    title: 'ALVIX Student Dashboard',
    layer: 'layout',
  });

  useEffect(() => {
    setNavOpen(false);
    // a clicked sidebar link keeps focus after navigation; drop it so no stale outline shows
    if (document.activeElement?.closest?.(".adm-sidebar")) document.activeElement.blur();
  }, [pathname]);

  useEffect(() => {
    if (!navOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setNavOpen(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [navOpen]);

  const title = pageTitle(pathname);

  return (
    <div className={`adm-shell st-shell${navOpen ? ' nav-open' : ''}`}>
      <aside className="adm-sidebar" aria-label="Student navigation">
        <div className="adm-sidebar__brand">
          <Link to="/dashboard/" className="adm-logo" aria-label="ALVIX home">
            <img src={LOGO_LIGHT} alt="ALVIX" className="adm-logo__img" />
          </Link>
          <button type="button" className="adm-icon-btn adm-sidebar__close" aria-label="Close menu" onClick={() => setNavOpen(false)}>
            <i className="bi bi-x-lg"></i>
          </button>
        </div>

        <nav className="adm-nav">
          {NAV.map((group) => (
            <div key={group.title} className="adm-nav__group">
              <p className="adm-nav__title">{group.title}</p>
              {group.items.map((item) => (
                <Link key={item.to} to={item.to} className={`adm-nav__link${item.match.some((m) => pathname.startsWith(m)) ? ' active' : ''}`}>
                  <i className={`bi ${item.icon}`}></i>
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>
          ))}
          <div className="adm-nav__group">
            <p className="adm-nav__title">Session</p>
            <Link to="/logout/" className="adm-nav__link adm-nav__link--logout">
              <i className="bi bi-box-arrow-right"></i>
              <span>Logout</span>
            </Link>
          </div>
        </nav>

        <div className="adm-sidebar__promo">
          <span className="adm-sidebar__promo-icon"><i className="bi bi-mortarboard-fill"></i></span>
          <strong>Explore university tiers</strong>
          <small>Beginner to advanced paths with daily lessons and quizzes.</small>
          <Link to="/generate_course/" className="adm-sidebar__promo-btn">
            <i className="bi bi-compass"></i> Browse courses
          </Link>
        </div>
      </aside>

      <div className="adm-overlay" onClick={() => setNavOpen(false)} aria-hidden="true" />

      <div className="adm-body">
        <header className="adm-topbar">
          <div className="adm-topbar__left">
            <button type="button" className="adm-icon-btn adm-topbar__menu" aria-label="Open menu" onClick={() => setNavOpen(true)}>
              <i className="bi bi-list"></i>
            </button>
            <div>
              <p className="adm-topbar__crumb">Student <i className="bi bi-chevron-right"></i> {title}</p>
              <h1 className="adm-topbar__title">{title}</h1>
            </div>
          </div>
          <div className="adm-topbar__right">
            <button
              type="button"
              className="adm-icon-btn adm-theme-btn"
              aria-label={dark ? 'Switch to light theme' : 'Switch to dark theme'}
              title={dark ? 'Light theme' : 'Dark theme'}
              onClick={toggleTheme}
            >
              <i key={theme} className={`bi ${dark ? 'bi-sun-fill' : 'bi-moon-stars-fill'}`}></i>
            </button>
            <StudentBell />
            <ProfileMenu />
          </div>
        </header>

        <main className="adm-main st-main" key={pathname}>
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}
