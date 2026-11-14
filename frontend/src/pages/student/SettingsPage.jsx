import AdminLoader from '../../layouts/AdminLoader';
import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { apiFetch } from '../../api/client';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { useAuth } from '../../hooks/useAuth';
import css from './SettingsPage.css?raw';

/*
 * Student settings (/settings/), same UserSettingsForm fields as `student_dashboard/settings.html`:
 *   theme ('Dark' | 'Light') -> two radio tiles named "theme"
 *   booleans                 -> <input type="checkbox" name="..."> styled as switches
 * Submitted as FormData to /student/settings/ exactly like before. Fields that are not on the
 * form (reminders, sound, autoplay) are kept by the ModelForm instance on the server.
 *
 * The inputs are controlled so the page always agrees with the saved values, including a theme
 * changed from the top-bar toggle while this page is open.
 */

const THEMES = [
  { value: 'Light', label: 'Light', icon: 'bi-sun-fill', text: 'Bright and clean, best in daylight.' },
  { value: 'Dark', label: 'Dark', icon: 'bi-moon-stars-fill', text: 'Easy on the eyes at night.' },
];

const TOGGLES = [
  { group: 'notifications', name: 'email_notifications', icon: 'bi-envelope-paper-fill', label: 'Email notifications', text: 'Course updates and announcements in your inbox.' },
  { group: 'notifications', name: 'ai_notifications', icon: 'bi-robot', label: 'AI assistant notifications', text: 'Tips and reminders from your AI teacher.' },
  { group: 'privacy', name: 'public_profile', icon: 'bi-globe2', label: 'Public profile', text: 'Let others see your name and learning progress.' },
];

const FIELDS = ['theme', ...TOGGLES.map((t) => t.name)];

function toValues(form) {
  const src = form || {};
  return {
    theme: src.theme === 'Light' ? 'Light' : 'Dark', // model default is Dark
    ...Object.fromEntries(TOGGLES.map((t) => [t.name, Boolean(src[t.name])])),
  };
}

function Switch({ name, icon, label, text, checked, onChange, disabled }) {
  const id = `id_${name}`;
  return (
    <label className="ss-toggle" htmlFor={id}>
      <span className="ss-toggle__icon"><i className={`bi ${icon}`}></i></span>
      <span className="ss-toggle__text">
        <strong>{label}</strong>
        <small>{text}</small>
      </span>
      <input
        type="checkbox"
        name={name}
        id={id}
        className="ss-switch__input"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(name, e.target.checked)}
      />
      <span className="ss-switch" aria-hidden="true"><span className="ss-switch__knob" /></span>
    </label>
  );
}

function SettingsContent({ form, onSaved }) {
  // Injected once the data is loaded, i.e. after StudentLayout's CSS (same cascade order as the template).
  usePageAssets({ css });
  const { user } = useAuth();
  const [saved, setSaved] = useState(() => toValues(form));
  const [values, setValues] = useState(saved);
  const [saving, setSaving] = useState(false);

  // The top-bar toggle saves the theme on its own: adopt it here as the saved value
  // (and as the current value unless the student already picked something else).
  const liveTheme = user?.settings?.theme;
  const savedTheme = saved.theme;
  useEffect(() => {
    if ((liveTheme !== 'Dark' && liveTheme !== 'Light') || liveTheme === savedTheme) return;
    setValues((v) => (v.theme === savedTheme ? { ...v, theme: liveTheme } : v));
    setSaved((s) => ({ ...s, theme: liveTheme }));
  }, [liveTheme, savedTheme]);

  const dirty = useMemo(() => FIELDS.some((f) => values[f] !== saved[f]), [values, saved]);
  const update = (name, value) => setValues((v) => ({ ...v, [name]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    const loading = toast.loading('Saving your settings…');
    try {
      const res = await apiFetch('/student/settings/', { method: 'POST', body: new FormData(event.currentTarget) });
      // Shown here as a toast only: queuing it as a flash message made it pop up later on other pages.
      toast.success(res.messages?.[0]?.message || 'Settings saved.', { id: loading });
      setSaved(values);
      await onSaved();
    } catch (err) {
      if (err.status === 400) {
        const fieldError = Object.values(err.data?.errors || {}).flat()[0];
        toast.error(fieldError || err.data?.messages?.[0]?.message || 'Please check your settings and try again.', { id: loading });
      } else {
        console.error('Error:', err);
        toast.error(!err.status || err.status >= 500 ? 'Server is not responding. Please try again.' : 'Could not save your settings.', { id: loading });
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="ss">
      <header className="ss-head">
        <span className="ss-head__icon"><i className="bi bi-sliders"></i></span>
        <div>
          <p className="ss-eyebrow">Preferences</p>
          <h2 className="ss-head__title">Account settings</h2>
          <p className="ss-head__sub">Choose how ALVIX looks and how we keep in touch with you.</p>
        </div>
      </header>

      <form method="POST" onSubmit={handleSubmit}>
        {/* Appearance */}
        <section className="ss-card">
          <div className="ss-card__head">
            <span className="ss-card__icon"><i className="bi bi-palette-fill"></i></span>
            <div>
              <p className="ss-eyebrow">Appearance</p>
              <h3 className="ss-title">Theme mode</h3>
            </div>
          </div>
          <div className="ss-themes" role="radiogroup" aria-label="Theme mode">
            {THEMES.map((t) => (
              <label key={t.value} className={`ss-theme ss-theme--${t.value.toLowerCase()}`} htmlFor={`id_theme_${t.value}`}>
                <input
                  type="radio"
                  name="theme"
                  id={`id_theme_${t.value}`}
                  value={t.value}
                  checked={values.theme === t.value}
                  onChange={() => update('theme', t.value)}
                  disabled={saving}
                  required
                  className="ss-theme__input"
                />
                <span className="ss-theme__preview" aria-hidden="true">
                  <span className="ss-theme__bar" />
                  <span className="ss-theme__side" />
                  <span className="ss-theme__card" />
                  <span className="ss-theme__card ss-theme__card--b" />
                </span>
                <span className="ss-theme__meta">
                  <span className="ss-theme__name"><i className={`bi ${t.icon}`}></i> {t.label}</span>
                  <small>{t.text}</small>
                </span>
                <span className="ss-theme__check" aria-hidden="true"><i className="bi bi-check-lg"></i></span>
              </label>
            ))}
          </div>
        </section>

        {/* Notifications */}
        <section className="ss-card">
          <div className="ss-card__head">
            <span className="ss-card__icon ss-card__icon--teal"><i className="bi bi-bell-fill"></i></span>
            <div>
              <p className="ss-eyebrow">Stay informed</p>
              <h3 className="ss-title">Notifications</h3>
            </div>
          </div>
          <div className="ss-toggles">
            {TOGGLES.filter((t) => t.group === 'notifications').map((t) => (
              <Switch key={t.name} {...t} checked={values[t.name]} onChange={update} disabled={saving} />
            ))}
          </div>
        </section>

        {/* Privacy */}
        <section className="ss-card">
          <div className="ss-card__head">
            <span className="ss-card__icon ss-card__icon--gold"><i className="bi bi-shield-lock-fill"></i></span>
            <div>
              <p className="ss-eyebrow">Privacy</p>
              <h3 className="ss-title">Profile visibility</h3>
            </div>
          </div>
          <div className="ss-toggles">
            {TOGGLES.filter((t) => t.group === 'privacy').map((t) => (
              <Switch key={t.name} {...t} checked={values[t.name]} onChange={update} disabled={saving} />
            ))}
          </div>
        </section>

        <div className="ss-actions">
          {dirty ? (
            <span className="ss-unsaved" role="status"><i className="bi bi-dot"></i> Unsaved changes</span>
          ) : (
            <span className="ss-saved" role="status"><i className="bi bi-check2-circle"></i> All changes saved</span>
          )}
          <div className="ss-actions__btns">
            {dirty && !saving ? (
              <button type="button" className="ss-btn ss-btn--ghost" onClick={() => setValues(saved)}>
                <i className="bi bi-arrow-counterclockwise"></i> Discard
              </button>
            ) : null}
            <button type="submit" className="ss-btn" disabled={saving || !dirty}>
              {saving ? <span className="ss-spinner" aria-hidden="true" /> : <i className="bi bi-check-circle"></i>}
              {saving ? 'Saving…' : 'Save settings'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

export default function SettingsPage() {
  const { data, ready, reload } = usePageData('/student/settings/');
  const { refresh } = useAuth();

  // Django redirected back to /settings/ and the base template re-read user.settings.theme:
  // refresh auth so StudentLayout applies dark mode immediately.
  const onSaved = async () => {
    await Promise.all([refresh(), reload()]);
  };

  if (!ready) return <AdminLoader />;
  return <SettingsContent form={data.form} onSaved={onSaved} />;
}
