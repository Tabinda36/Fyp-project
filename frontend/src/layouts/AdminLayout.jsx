import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { usePageAssets } from '../hooks/usePageAssets';
import { useAuth } from '../hooks/useAuth';
import { BOOTSTRAP_530, FONT_ADMIN, ICONS_1113, LOGO } from '../cdn';
import layoutCss from './AdminLayout.css?raw';
import extrasCss from './AdminLayoutExtras.css?raw';
import darkOverridesCss from './AdminDarkOverrides.css?raw';
import NotificationBell from './NotificationBell';
import AdminFlash from './AdminFlash';

const css = layoutCss + extrasCss + darkOverridesCss;

/*
 * Admin shell: sidebar (logo + navigation) and a top bar with the page title
 * and a profile dropdown. Pages render inside <main className="adm-main">.
 */

const DEFAULT_ADMIN_PHOTO = '/static/profile_pictures/tbpi.jpeg';
const FALLBACK_NAME = 'Tabinda Rukhsar';
const FALLBACK_EMAIL = 'tabindarukhsar36@gmail.com';

const NAV = [
  {
    title: 'Main',
    items: [
      { to: '/admindashboard/', icon: 'bi-grid-1x2-fill', label: 'Dashboard', end: true },
      { to: '/user_management/', icon: 'bi-people-fill', label: 'User Management' },
    ],
  },
  {
    title: 'Course Management',
    items: [
      { to: '/courses_info/', icon: 'bi-journal-bookmark-fill', label: 'Course List' },
      { to: '/add_course/', icon: 'bi-plus-circle-fill', label: 'Add Course' },
      { to: '/admin_reports/', icon: 'bi-robot', label: 'Reports' },
      { to: '/analytics/', icon: 'bi-bar-chart-fill', label: 'Analytics' },
    ],
  },
  {
    title: 'Settings',
    items: [
      { to: '/admin_notifications/', icon: 'bi-bell-fill', label: 'Notifications' },
      { to: '/admindashboard/avatar-settings/', icon: 'bi-person-badge-fill', label: 'Avatar & AI Teacher' },
    ],
  },
];

const TITLES = [
  ['/admindashboard/avatar-settings', 'Avatar & AI Teacher'],
  ['/admindashboard', 'Dashboard'],
  ['/user_management', 'User Management'],
  ['/courses_info', 'Course List'],
  ['/add_course', 'Add Course'],
  ['/admin_reports', 'Reports'],
  ['/analytics', 'Analytics'],
  ['/admin_notifications', 'Notifications'],
];

const THEME_KEY = 'alvix-admin-theme';

/** Admin appearance (light default). Sets body.adm-theme-dark + Bootstrap's data-bs-theme while mounted. */
function useAdminTheme() {
  const [theme, setTheme] = useState(() => {
    try {
      return window.localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light';
    } catch {
      return 'light';
    }
  });

  useLayoutEffect(() => {
    const dark = theme === 'dark';
    document.body.classList.toggle('adm-theme-dark', dark);
    if (dark) document.documentElement.setAttribute('data-bs-theme', 'dark');
    else document.documentElement.removeAttribute('data-bs-theme');
    try {
      window.localStorage.setItem(THEME_KEY, theme);
    } catch {
      /* storage unavailable */
    }
    return () => {
      document.body.classList.remove('adm-theme-dark');
      document.documentElement.removeAttribute('data-bs-theme');
    };
  }, [theme]);

  return [theme, setTheme];
}

function pageTitle(pathname) {
  if (/^\/user_management\/\d+/.test(pathname)) return 'User Details';
  const hit = TITLES.find(([prefix]) => pathname.startsWith(prefix));
  return hit ? hit[1] : 'Course Management';
}

function useAdminIdentity() {
  const { user } = useAuth();
  const profile = user?.profile || {};
  return {
    name: profile.full_name || user?.full_name || FALLBACK_NAME,
    email: user?.email || FALLBACK_EMAIL,
    photo: profile.profile_picture || DEFAULT_ADMIN_PHOTO,
  };
}

function ProfileMenu() {
  const { name, email, photo } = useAdminIdentity();
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
      <button
        type="button"
        className={`adm-profile__btn${open ? ' is-open' : ''}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <img src={photo} alt="" className="adm-profile__avatar" />
        <span className="adm-profile__meta">
          <strong>{name}</strong>
          <small>Administrator</small>
        </span>
        <i className="bi bi-chevron-down adm-profile__chev" aria-hidden="true"></i>
      </button>

      {open ? (
        <div className="adm-profile__menu" role="menu">
          <div className="adm-profile__card">
            <img src={photo} alt="" className="adm-profile__avatar adm-profile__avatar--lg" />
            <div>
              <strong>{name}</strong>
              <small>{email}</small>
              <span className="adm-profile__badge">ALVIX Admin</span>
            </div>
          </div>
          <Link role="menuitem" to="/admindashboard/"><i className="bi bi-grid-1x2"></i> Dashboard</Link>
          <Link role="menuitem" to="/admin_notifications/"><i className="bi bi-bell"></i> Notifications</Link>
          <Link role="menuitem" to="/admindashboard/avatar-settings/"><i className="bi bi-person-badge"></i> Avatar &amp; AI Teacher</Link>
          <div className="adm-profile__sep" />
          <Link role="menuitem" to="/logout/" className="is-danger"><i className="bi bi-box-arrow-right"></i> Logout</Link>
        </div>
      ) : null}
    </div>
  );
}

export default function AdminLayout({ children }) {
  const { pathname } = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const [theme, setTheme] = useAdminTheme();
  usePageAssets({ links: [BOOTSTRAP_530, ICONS_1113, FONT_ADMIN], css, title: 'ALVIX Admin Dashboard', layer: 'layout' });

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

  return (
    <div className={`adm-shell${navOpen ? ' nav-open' : ''}`}>
      <aside className="adm-sidebar" aria-label="Admin navigation">
        <div className="adm-sidebar__brand">
          <Link to="/admindashboard/" className="adm-logo" aria-label="ALVIX admin home">
            <img src={LOGO} alt="ALVIX" className="adm-logo__img" />
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
                <NavLink key={item.to} to={item.to} end={item.end} className="adm-nav__link">
                  <i className={`bi ${item.icon}`}></i>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}

          <div className="adm-nav__group">
            <p className="adm-nav__title">Account</p>
            <NavLink to="/logout/" className="adm-nav__link adm-nav__link--logout">
              <i className="bi bi-box-arrow-right"></i>
              <span>Logout</span>
            </NavLink>
          </div>
        </nav>

        <div className="adm-sidebar__promo">
          <span className="adm-sidebar__promo-icon"><i className="bi bi-stars"></i></span>
          <strong>Build a new course</strong>
          <small>AI generates all three tiers with lessons and quizzes.</small>
          <Link to="/add_course/" className="adm-sidebar__promo-btn">
            <i className="bi bi-plus-lg"></i> Add course
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
              <p className="adm-topbar__crumb">Admin <i className="bi bi-chevron-right"></i> {pageTitle(pathname)}</p>
              <h1 className="adm-topbar__title">{pageTitle(pathname)}</h1>
            </div>
          </div>
          <div className="adm-topbar__right">
            <button
              type="button"
              className="adm-icon-btn adm-theme-btn"
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              title={theme === 'dark' ? 'Light theme' : 'Dark theme'}
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            >
              <i key={theme} className={`bi ${theme === 'dark' ? 'bi-sun-fill' : 'bi-moon-stars-fill'}`}></i>
            </button>
            <NotificationBell />
            <ProfileMenu />
          </div>
        </header>

        <main className="adm-main" key={pathname}>
          <AdminFlash disabled={pathname.startsWith('/admindashboard/avatar-settings')} />
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}
