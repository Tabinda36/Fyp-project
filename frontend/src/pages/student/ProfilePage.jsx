import AdminLoader from '../../layouts/AdminLoader';
import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiFetch } from '../../api/client';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { useAuth } from '../../hooks/useAuth';
import css from './ProfilePage.css?raw';

/* Student profile (/profile/): same API as `student_dashboard/profile.html`, redesigned. */

const DEFAULT_AVATAR =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150' viewBox='0 0 24 24' fill='%231B5E20'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z'/%3E%3C/svg%3E";

const EMAIL_RE = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)*\.[A-Za-z]{2,}$/;
const PHONE_RE = /^\+?[0-9\s()-]{7,20}$/;
const MAX_IMAGE_MB = 5;

function validate(v) {
  const e = {};
  if (v.full_name.trim().length > 100) e.full_name = 'Full name must be 100 characters or fewer.';
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

function Field({ id, label, icon, error, hint, children, full }) {
  return (
    <div className={`sp-field${full ? ' sp-field--full' : ''}${error ? ' has-error' : ''}`}>
      <label htmlFor={id}>{icon ? <i className={`bi ${icon}`}></i> : null} {label}</label>
      {children}
      {error ? (
        <span className="sp-field__error" id={`${id}-error`} role="alert"><i className="bi bi-exclamation-circle"></i> {error}</span>
      ) : hint ? <span className="sp-field__hint">{hint}</span> : null}
    </div>
  );
}

function ProfileContent({ data, onSaved }) {
  // Injected once the data is loaded, i.e. after StudentLayout's CSS (same cascade order as the template).
  usePageAssets({ css });

  const { profile, user, enrolled_course: enrolledCourse } = data;
  const fileInputRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [saving, setSaving] = useState(false);
  const [touched, setTouched] = useState({});
  const initial = {
    full_name: profile.full_name || '',
    email: user.email || '',
    phone: profile.phone || '',
    dob: profile.dob || '',
    gender: profile.gender === 'Male' || profile.gender === 'Female' ? profile.gender : '',
  };
  const [values, setValues] = useState(initial);
  const errors = validate(values);
  const err = (k) => (touched[k] ? errors[k] : '');

  const set = (k) => (e) => setValues((v) => ({ ...v, [k]: e.target.value }));
  const blur = (k) => () => setTouched((t) => ({ ...t, [k]: true }));

  const previewImage = (input) => {
    const file = input.files && input.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Please choose an image file (JPG, PNG or WebP).');
      input.value = '';
      return;
    }
    if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
      toast.error(`Image is too large. Maximum size is ${MAX_IMAGE_MB} MB.`);
      input.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setTouched({ full_name: true, email: true, phone: true, dob: true });
    const first = Object.keys(errors)[0];
    if (first) {
      toast.error(errors[first]);
      document.getElementById(`sp-${first}`)?.focus();
      return;
    }
    const body = new FormData(event.currentTarget);
    setSaving(true);
    const loading = toast.loading('Saving your profile…');
    try {
      await apiFetch('/student/profile/', { method: 'POST', body });
      toast.success('Profile updated successfully.', { id: loading });
      await onSaved();
    } catch (e) {
      if (e.status === 400 && e.data?.error) toast.error(e.data.error, { id: loading });
      else {
        console.error('Error:', e);
        toast.error(!e.status || e.status >= 500 ? 'Server is not responding. Please try again.' : 'Could not save your profile.', { id: loading });
      }
      setSaving(false);
    }
  };

  const avatarSrc = preview || profile.profile_picture || DEFAULT_AVATAR;
  const displayName = profile.full_name || profile.user?.username || user.username;
  const dirty = Boolean(preview) || Object.keys(initial).some((k) => initial[k] !== values[k]);

  return (
    <div className="sp">
      <form method="POST" encType="multipart/form-data" onSubmit={handleSubmit} noValidate>
        {/* Hero */}
        <section className="sp-hero">
          <div className="sp-hero__cover" aria-hidden="true">
            <span className="sp-hero__orb" />
          </div>
          <div className="sp-hero__body">
            <button type="button" className="sp-avatar" onClick={() => fileInputRef.current?.click()} aria-label="Change profile photo">
              <img src={avatarSrc} alt="" id="avatar-preview" />
              <span className="sp-avatar__edit"><i className="bi bi-camera-fill"></i></span>
            </button>
            <input type="file" id="profile_picture_input" ref={fileInputRef} name="profile_picture" className="sp-hidden" accept="image/*" onChange={(e) => previewImage(e.target)} />

            <div className="sp-hero__info">
              <h2 className="sp-hero__name">{displayName}</h2>
              <div className="sp-chips">
                {profile.student_id ? <span className="sp-chip sp-chip--gold"><i className="bi bi-person-badge-fill"></i> ID {profile.student_id}</span> : null}
                <span className="sp-chip"><i className="bi bi-envelope"></i> {user.email || 'No email'}</span>
                {enrolledCourse?.title ? <span className="sp-chip"><i className="bi bi-journal-bookmark"></i> {enrolledCourse.title}</span> : null}
              </div>
              <p className="sp-hero__hint">
                {preview ? <><i className="bi bi-check-circle-fill"></i> New photo selected — save to apply.</> : 'Tap your photo to upload a new one (max 5 MB).'}
              </p>
            </div>
          </div>
        </section>

        <div className="sp-grid">
          {/* Personal information */}
          <section className="sp-card">
            <header className="sp-card__head">
              <span className="sp-card__icon"><i className="bi bi-person-vcard"></i></span>
              <div>
                <p className="sp-eyebrow">Account</p>
                <h3 className="sp-title">Personal information</h3>
              </div>
            </header>

            <div className="sp-form">
              <Field id="sp-student-id" label="Student ID" icon="bi-hash" hint="Your unique ALVIX identity.">
                <input id="sp-student-id" type="text" className="sp-input sp-input--id" value={profile.student_id || 'Generating...'} readOnly />
              </Field>
              <Field id="sp-full_name" label="Full name" icon="bi-person" error={err('full_name')}>
                <input id="sp-full_name" type="text" className="sp-input" name="full_name" value={values.full_name} onChange={set('full_name')} onBlur={blur('full_name')} maxLength={100} autoComplete="name" aria-invalid={Boolean(err('full_name'))} />
              </Field>
              <Field id="sp-email" label="Email" icon="bi-envelope" error={err('email')}>
                <input id="sp-email" type="email" className="sp-input" name="email" value={values.email} onChange={set('email')} onBlur={blur('email')} autoComplete="email" aria-invalid={Boolean(err('email'))} />
              </Field>
              <Field id="sp-phone" label="Phone number" icon="bi-telephone" error={err('phone')} hint="Optional, e.g. +92 300 1234567.">
                <input id="sp-phone" type="tel" className="sp-input" name="phone" value={values.phone} onChange={set('phone')} onBlur={blur('phone')} autoComplete="tel" aria-invalid={Boolean(err('phone'))} />
              </Field>
              <Field id="sp-dob" label="Date of birth" icon="bi-calendar-event" error={err('dob')}>
                <input id="sp-dob" type="date" className="sp-input" name="dob" value={values.dob} onChange={set('dob')} onBlur={blur('dob')} max={new Date().toISOString().slice(0, 10)} aria-invalid={Boolean(err('dob'))} />
              </Field>
              <Field id="sp-gender" label="Gender" icon="bi-gender-ambiguous">
                <select id="sp-gender" className="sp-input" name="gender" value={values.gender} onChange={set('gender')}>
                  <option value="">Select gender</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                </select>
              </Field>
              <Field id="sp-course" label="Course enrolled" icon="bi-journal-bookmark" full>
                <input id="sp-course" type="text" className="sp-input sp-input--readonly" value={enrolledCourse?.title || 'All Enrolled Courses Active'} readOnly />
              </Field>
            </div>
          </section>

          {/* Learning assessment */}
          <section className="sp-card sp-card--assessment">
            <header className="sp-card__head">
              <span className="sp-card__icon sp-card__icon--gold"><i className="bi bi-clipboard2-data"></i></span>
              <div>
                <p className="sp-eyebrow">Learning</p>
                <h3 className="sp-title">Learning assessment</h3>
              </div>
            </header>

            <dl className="sp-info">
              <div>
                <dt><i className="bi bi-compass"></i> Interest area</dt>
                <dd>{profile.interest_area || <span className="sp-muted">Not set yet</span>}</dd>
              </div>
              <div>
                <dt><i className="bi bi-bullseye"></i> Goal</dt>
                <dd>{profile.goal || <span className="sp-muted">Not set yet</span>}</dd>
              </div>
            </dl>

            <div className="sp-quote">
              <span className="sp-quote__label"><i className="bi bi-chat-left-quote"></i> Expectations</span>
              <p>{profile.expectations || 'No expectations recorded yet. Click Retake Assessment to set them.'}</p>
            </div>

            <Link to="/assessment/?retake=true" className="sp-btn sp-btn--soft sp-btn--block">
              <i className="bi bi-arrow-repeat"></i> Retake assessment
            </Link>
          </section>
        </div>

        {/* Actions */}
        <div className="sp-actions">
          {dirty ? <span className="sp-unsaved"><i className="bi bi-dot"></i> Unsaved changes</span> : null}
          <Link to="/logout/" className="sp-btn sp-btn--danger-soft">
            <i className="bi bi-box-arrow-right"></i> Logout
          </Link>
          <button type="submit" className="sp-btn sp-btn--primary" disabled={saving}>
            {saving ? <span className="sp-spinner" aria-hidden="true" /> : <i className="bi bi-check-circle"></i>}
            {saving ? 'Saving…' : 'Save profile'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function ProfilePage() {
  const { data, ready, reload } = usePageData('/student/profile/');
  const { refresh } = useAuth();
  const [version, setVersion] = useState(0);

  // Django redirected back to /profile/ after saving: reload the data and reset the form.
  const onSaved = async () => {
    await Promise.all([refresh(), reload()]);
    setVersion((v) => v + 1);
  };

  if (!ready) return <AdminLoader />;
  return <ProfileContent key={version} data={data} onSaved={onSaved} />;
}
