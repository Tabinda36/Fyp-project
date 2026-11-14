import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import NotFoundPage from '../NotFoundPage';
import ConfirmDialog from './ConfirmDialog';
import { UserAvatar } from './UserManagementPage';
import { apiMessage, deleteUser, errorText, normalizeUser, updateUser } from './userUtils';
import css from './UserManagementPage.css?raw';
import AdminLoader from '../../layouts/AdminLoader';

/* /user_management/:userId/ — full profile with editable tabs (replaces the old edit modal). */

const TABS = [
  { key: 'overview', label: 'Overview', icon: 'bi-person-vcard' },
  { key: 'edit', label: 'Edit profile', icon: 'bi-pencil-square' },
  { key: 'security', label: 'Security', icon: 'bi-shield-lock' },
  { key: 'danger', label: 'Danger zone', icon: 'bi-exclamation-octagon' },
];

const EMAIL_RE = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)*\.[A-Za-z]{2,}$/;
const USERNAME_RE = /^[A-Za-z0-9_.@+-]{3,150}$/;
const PHONE_RE = /^\+?[0-9\s()-]{7,20}$/;

function validateProfile(v) {
  const e = {};
  if (!v.username.trim()) e.username = 'Username is required.';
  else if (!USERNAME_RE.test(v.username.trim())) e.username = '3–150 characters: letters, numbers and @ . + - _ only (no spaces).';
  if (!v.email.trim()) e.email = 'Email address is required.';
  else if (!EMAIL_RE.test(v.email.trim())) e.email = 'Enter a valid email address.';
  if (v.phone.trim() && !PHONE_RE.test(v.phone.trim())) e.phone = 'Enter a valid phone number (7–20 digits, + allowed).';
  if (v.dob) {
    const d = new Date(v.dob);
    if (Number.isNaN(d.getTime())) e.dob = 'Enter a valid date.';
    else if (d > new Date()) e.dob = 'Date of birth cannot be in the future.';
    else if (d.getFullYear() < 1900) e.dob = 'Enter a realistic date of birth.';
  }
  return e;
}

function validatePassword(v) {
  const e = {};
  if (!v.password) e.password = 'Enter a new password.';
  else if (v.password.length < 8) e.password = 'Use at least 8 characters.';
  else if (!/[A-Za-z]/.test(v.password) || !/\d/.test(v.password)) e.password = 'Use letters and at least one number.';
  if (!v.confirm) e.confirm = 'Confirm the new password.';
  else if (v.confirm !== v.password) e.confirm = 'Passwords do not match.';
  return e;
}

function Field({ id, label, error, hint, children }) {
  return (
    <div className={`ud-field${error ? ' has-error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      {children}
      {error ? <span className="ud-field__error" role="alert"><i className="bi bi-exclamation-circle"></i> {error}</span>
        : hint ? <span className="ud-field__hint">{hint}</span> : null}
    </div>
  );
}

export default function UserDetailPage() {
  usePageAssets({ css });
  const { userId } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { data, ready, reload } = usePageData('/admin/users/');

  const user = useMemo(() => {
    if (!ready) return null;
    const raw = (data.users || []).find((u) => String(u.id) === String(userId));
    return raw ? normalizeUser(raw) : null;
  }, [ready, data, userId]);

  const tab = TABS.some((t) => t.key === params.get('tab')) ? params.get('tab') : 'overview';
  const setTab = (key) => setParams(key === 'overview' ? {} : { tab: key }, { replace: true });

  const [profile, setProfile] = useState({ username: '', email: '', phone: '', dob: '' });
  const [profileTouched, setProfileTouched] = useState({});
  const [pw, setPw] = useState({ password: '', confirm: '' });
  const [pwTouched, setPwTouched] = useState({});
  const [showPw, setShowPw] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (user) setProfile({ username: user.username, email: user.email || '', phone: user.phone, dob: user.dob });
  }, [user]);

  const profileErrors = validateProfile(profile);
  const pwErrors = validatePassword(pw);
  const dirty = user && (profile.username !== user.username || profile.email !== (user.email || '')
    || profile.phone !== user.phone || profile.dob !== user.dob);

  if (!/^\d+$/.test(userId)) return <NotFoundPage />;

  if (!ready) return <AdminLoader label="Loading user" />;

  if (!user) {
    return (
      <div className="um-page">
        <div className="um-card um-empty">
          <span className="um-empty__icon"><i className="bi bi-person-x"></i></span>
          <strong>User not found</strong>
          <small>This account may have been deleted.</small>
          <Link to="/user_management/" className="um-btn um-btn--soft"><i className="bi bi-arrow-left"></i> Back to users</Link>
        </div>
      </div>
    );
  }

  async function saveProfile(e) {
    e.preventDefault();
    setProfileTouched({ username: true, email: true, phone: true, dob: true });
    const first = Object.keys(profileErrors)[0];
    if (first) {
      toast.error(profileErrors[first]);
      document.getElementById(`ud-${first}`)?.focus();
      return;
    }
    if (!dirty) {
      toast('Nothing to save — no changes made.', { icon: 'ℹ️' });
      return;
    }
    setSaving(true);
    const loading = toast.loading('Saving changes…');
    try {
      const res = await updateUser(user.id, {
        username: profile.username.trim(),
        email: profile.email.trim(),
        phone: profile.phone.trim(),
        dob: profile.dob,
      });
      toast.success(apiMessage(res, 'User updated successfully.'), { id: loading });
      setProfileTouched({});
      reload();
    } catch (err) {
      toast.error(errorText(err, 'Could not save changes.'), { id: loading });
    } finally {
      setSaving(false);
    }
  }

  async function savePassword(e) {
    e.preventDefault();
    setPwTouched({ password: true, confirm: true });
    const first = Object.keys(pwErrors)[0];
    if (first) {
      toast.error(pwErrors[first]);
      document.getElementById(`ud-${first}`)?.focus();
      return;
    }
    setSaving(true);
    const loading = toast.loading('Updating password…');
    try {
      await updateUser(user.id, { password: pw.password });
      toast.success(`Password updated for ${user.username}.`, { id: loading });
      setPw({ password: '', confirm: '' });
      setPwTouched({});
      setShowPw(false);
    } catch (err) {
      toast.error(errorText(err, 'Could not update the password.'), { id: loading });
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    setDeleting(true);
    const loading = toast.loading(`Deleting ${user.username}…`);
    try {
      const res = await deleteUser(user.id);
      toast.success(apiMessage(res, `User ${user.username} deleted.`), { id: loading });
      navigate('/user_management/', { replace: true });
    } catch (err) {
      toast.error(errorText(err, 'Could not delete this user.'), { id: loading });
      setDeleting(false);
      setConfirmOpen(false);
    }
  }

  const pErr = (k) => (profileTouched[k] ? profileErrors[k] : '');
  const wErr = (k) => (pwTouched[k] ? pwErrors[k] : '');

  return (
    <div className="um-page">
      <Link to="/user_management/" className="ud-back"><i className="bi bi-arrow-left"></i> All users</Link>

      {/* Profile hero */}
      <section className="ud-hero">
        <div className="ud-hero__cover" aria-hidden="true" />
        <div className="ud-hero__body">
          <UserAvatar name={user.username} size="xl" />
          <div className="ud-hero__info">
            <h2>{user.username}</h2>
            <p>{user.email || 'No email on file'}</p>
            <div className="ud-hero__tags">
              <span className={`um-status ${user.is_active ? 'is-active' : 'is-inactive'}`}>
                <span className="um-status__dot" />{user.is_active ? 'Active' : 'Inactive'}
              </span>
              <span className="ud-tag"><i className="bi bi-mortarboard"></i> Student</span>
              <span className="ud-tag"><i className="bi bi-hash"></i> ID {user.id}</span>
            </div>
          </div>
          <div className="ud-hero__actions">
            <button type="button" className="um-btn um-btn--primary" onClick={() => setTab('edit')}>
              <i className="bi bi-pencil-square"></i> Edit profile
            </button>
          </div>
        </div>
      </section>

      {/* Tabs */}
      <div className="um-tabs ud-tabs" role="tablist" aria-label="User sections">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={`um-tab${tab === t.key ? ' is-active' : ''}${t.key === 'danger' ? ' um-tab--danger' : ''}`}
            onClick={() => setTab(t.key)}
          >
            <i className={`bi ${t.icon}`}></i> {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="ud-grid" key="overview">
          <section className="um-card ud-panel">
            <h3 className="ud-panel__title">Contact & personal</h3>
            <dl className="ud-info">
              <div><dt><i className="bi bi-person"></i> Username</dt><dd>{user.username}</dd></div>
              <div><dt><i className="bi bi-envelope"></i> Email</dt><dd>{user.email || '—'}</dd></div>
              <div><dt><i className="bi bi-telephone"></i> Phone</dt><dd>{user.phone || <span className="um-empty-text">Not provided</span>}</dd></div>
              <div><dt><i className="bi bi-calendar-event"></i> Date of birth</dt><dd>{user.dob || <span className="um-empty-text">Not provided</span>}</dd></div>
              <div><dt><i className="bi bi-key"></i> Password</dt><dd>•••••••• <button type="button" className="ud-link" onClick={() => setTab('security')}>Reset</button></dd></div>
            </dl>
          </section>

          <section className="um-card ud-panel">
            <h3 className="ud-panel__title">
              Enrolled courses <span className="um-tab__count">{user.courses.length}</span>
            </h3>
            {user.courses.length ? (
              <ul className="ud-courses">
                {user.courses.map((c, i) => (
                  <li key={i}>
                    <span className="ud-courses__icon"><i className="bi bi-journal-bookmark-fill"></i></span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="um-empty um-empty--inline">
                <span className="um-empty__icon"><i className="bi bi-journal-x"></i></span>
                <strong>No courses yet</strong>
                <small>This student hasn&apos;t enrolled in a course.</small>
              </div>
            )}
          </section>
        </div>
      )}

      {tab === 'edit' && (
        <section className="um-card ud-panel ud-form-panel" key="edit">
          <h3 className="ud-panel__title">Edit profile</h3>
          <p className="ud-panel__sub">Update the student&apos;s account details. Changes apply immediately.</p>
          <form noValidate onSubmit={saveProfile}>
            <div className="ud-form-grid">
              <Field id="ud-username" label="Username" error={pErr('username')}>
                <input id="ud-username" className="ud-input" value={profile.username} autoComplete="off"
                  onChange={(e) => setProfile({ ...profile, username: e.target.value })}
                  onBlur={() => setProfileTouched((t) => ({ ...t, username: true }))} aria-invalid={Boolean(pErr('username'))} />
              </Field>
              <Field id="ud-email" label="Email address" error={pErr('email')}>
                <input id="ud-email" type="email" className="ud-input" value={profile.email} autoComplete="off"
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  onBlur={() => setProfileTouched((t) => ({ ...t, email: true }))} aria-invalid={Boolean(pErr('email'))} />
              </Field>
              <Field id="ud-phone" label="Phone number" error={pErr('phone')} hint="Optional. Include the country code, e.g. +92 300 1234567.">
                <input id="ud-phone" type="tel" className="ud-input" value={profile.phone} placeholder="+92 300 1234567"
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  onBlur={() => setProfileTouched((t) => ({ ...t, phone: true }))} aria-invalid={Boolean(pErr('phone'))} />
              </Field>
              <Field id="ud-dob" label="Date of birth" error={pErr('dob')} hint="Optional.">
                <input id="ud-dob" type="date" className="ud-input" value={profile.dob} max={new Date().toISOString().slice(0, 10)}
                  onChange={(e) => setProfile({ ...profile, dob: e.target.value })}
                  onBlur={() => setProfileTouched((t) => ({ ...t, dob: true }))} aria-invalid={Boolean(pErr('dob'))} />
              </Field>
            </div>
            <p className="ud-note"><i className="bi bi-info-circle"></i> Clearing phone or date of birth keeps the current value on file.</p>
            <div className="ud-form-actions">
              <button type="button" className="um-btn um-btn--ghost" disabled={saving || !dirty}
                onClick={() => { setProfile({ username: user.username, email: user.email || '', phone: user.phone, dob: user.dob }); setProfileTouched({}); }}>
                Discard changes
              </button>
              <button type="submit" className="um-btn um-btn--primary" disabled={saving}>
                {saving ? <span className="adm-dialog__spinner" aria-hidden="true" /> : <i className="bi bi-check2-circle"></i>}
                {saving ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </form>
        </section>
      )}

      {tab === 'security' && (
        <section className="um-card ud-panel ud-form-panel" key="security">
          <h3 className="ud-panel__title">Reset password</h3>
          <p className="ud-panel__sub">Set a new password if the student forgot theirs. Share it with them securely.</p>
          <form noValidate onSubmit={savePassword}>
            <div className="ud-form-grid">
              <Field id="ud-password" label="New password" error={wErr('password')} hint="At least 8 characters with letters and a number.">
                <div className="ud-input-wrap">
                  <input id="ud-password" type={showPw ? 'text' : 'password'} className="ud-input" value={pw.password} autoComplete="new-password"
                    onChange={(e) => setPw({ ...pw, password: e.target.value })}
                    onBlur={() => setPwTouched((t) => ({ ...t, password: true }))} aria-invalid={Boolean(wErr('password'))} />
                  <button type="button" className="ud-eye" onClick={() => setShowPw((s) => !s)} aria-label={showPw ? 'Hide password' : 'Show password'}>
                    <i className={`bi ${showPw ? 'bi-eye-slash' : 'bi-eye'}`}></i>
                  </button>
                </div>
              </Field>
              <Field id="ud-confirm" label="Confirm password" error={wErr('confirm')}>
                <input id="ud-confirm" type={showPw ? 'text' : 'password'} className="ud-input" value={pw.confirm} autoComplete="new-password"
                  onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
                  onBlur={() => setPwTouched((t) => ({ ...t, confirm: true }))} aria-invalid={Boolean(wErr('confirm'))} />
              </Field>
            </div>
            <div className="ud-form-actions">
              <button type="submit" className="um-btn um-btn--primary" disabled={saving}>
                {saving ? <span className="adm-dialog__spinner" aria-hidden="true" /> : <i className="bi bi-shield-check"></i>}
                {saving ? 'Updating…' : 'Update password'}
              </button>
            </div>
          </form>
        </section>
      )}

      {tab === 'danger' && (
        <section className="um-card ud-panel ud-danger" key="danger">
          <h3 className="ud-panel__title">Delete this account</h3>
          <p className="ud-panel__sub">
            Permanently remove <strong>{user.username}</strong> and their related data. This cannot be undone.
          </p>
          <button type="button" className="um-btn um-btn--danger" onClick={() => setConfirmOpen(true)}>
            <i className="bi bi-trash3"></i> Delete user
          </button>
        </section>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title="Delete this user?"
        message={`${user.username} will be permanently removed.`}
        detail="Their account, enrollments and learning progress will be deleted. This cannot be undone."
        confirmLabel="Yes, delete user"
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
