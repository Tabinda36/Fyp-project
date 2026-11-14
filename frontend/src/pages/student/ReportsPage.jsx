import AdminLoader from '../../layouts/AdminLoader';
import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { apiFetch } from '../../api/client';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { useFlash, useFlashMessages } from '../../hooks/useFlash';
import { djDate } from '../../utils/djangoFormat';
import css from './ReportsPage.css?raw';

/* Student reports (/reports/): "Report a problem" form + "My reports" list. */

const FALLBACK_TYPES = [
  ['technical', 'Technical Issue'],
  ['course_content', 'Course Content Error'],
  ['quiz_issue', 'Quiz / Assignment Bug'],
  ['other', 'Other Issue'],
];

const TYPE_ICON = {
  technical: 'bi-cpu-fill',
  course_content: 'bi-journal-x',
  quiz_issue: 'bi-bug-fill',
  other: 'bi-question-circle-fill',
};

const STATUS = {
  pending: { label: 'Pending', tone: 'amber', icon: 'bi-hourglass-split' },
  in_progress: { label: 'In progress', tone: 'blue', icon: 'bi-arrow-repeat' },
  resolved: { label: 'Resolved', tone: 'green', icon: 'bi-check-circle-fill' },
};

const TABS = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'in_progress', label: 'In progress' },
  { key: 'resolved', label: 'Resolved' },
];

const EMPTY = { course_name: '', problem_type: '', problem_title: '', problem_description: '' };

function validate(v) {
  const e = {};
  if (!v.course_name.trim()) e.course_name = 'Course name is required.';
  else if (v.course_name.trim().length > 255) e.course_name = 'Course name must be 255 characters or fewer.';
  if (!v.problem_type) e.problem_type = 'Choose a problem type.';
  if (!v.problem_title.trim()) e.problem_title = 'Problem title is required.';
  else if (v.problem_title.trim().length < 5) e.problem_title = 'Use at least 5 characters.';
  else if (v.problem_title.trim().length > 255) e.problem_title = 'Title must be 255 characters or fewer.';
  if (!v.problem_description.trim()) e.problem_description = 'Please describe the problem.';
  else if (v.problem_description.trim().length < 10) e.problem_description = 'Add a bit more detail (at least 10 characters).';
  return e;
}

// `{% if messages %}` toast block + its "Auto Hide Script (Disappears after 5 seconds)".
function Toasts() {
  const messages = useFlashMessages();
  const { dismiss } = useFlash();
  const batch = messages.map((m) => m.id).join('|');
  const [fade, setFade] = useState(null); // batch currently fading out
  const [gone, setGone] = useState(null); // batch removed from the DOM

  useEffect(() => {
    if (!batch) return undefined;
    let inner;
    const outer = setTimeout(() => {
      setFade(batch);
      inner = setTimeout(() => {
        setGone(batch); // Remove from DOM after fade out
        batch.split('|').forEach(dismiss);
      }, 500);
    }, 5000); // 5000ms = 5 seconds
    return () => {
      clearTimeout(outer);
      clearTimeout(inner);
    };
  }, [batch, dismiss]);

  if (!messages.length || gone === batch) return null;

  // Inline banner at the top of the page (no floating pop-up / Bootstrap alert).
  return (
    <div className={`sr-flash${fade === batch ? ' is-fading' : ''}`} role="status" aria-live="polite">
      {messages.map((message) => {
        const isError = message.tags === 'error' || message.tags === 'danger';
        return (
          <div key={message.id} className={`sr-flash__item${isError ? ' is-error' : ''}`}>
            <i className={`bi ${isError ? 'bi-exclamation-circle-fill' : 'bi-check-circle-fill'}`}></i>
            <strong>{message.message}</strong>
            <button type="button" className="sr-flash__close" aria-label="Dismiss" onClick={() => dismiss(message.id)}>
              <i className="bi bi-x-lg"></i>
            </button>
          </div>
        );
      })}
    </div>
  );
}

function Field({ id, label, icon, error, hint, children, count }) {
  return (
    <div className={`sr-field${error ? ' has-error' : ''}`}>
      <label htmlFor={id}><i className={`bi ${icon}`}></i> {label}{count ? <span className="sr-count">{count}</span> : null}</label>
      {children}
      {error ? <span className="sr-field__error" role="alert"><i className="bi bi-exclamation-circle"></i> {error}</span>
        : hint ? <span className="sr-field__hint">{hint}</span> : null}
    </div>
  );
}

function ReportsContent({ data, reload }) {
  // Injected once the data is loaded, i.e. after StudentLayout's CSS (same cascade order as the template).
  usePageAssets({ css });
  const { addMessages } = useFlash();
  const [values, setValues] = useState(EMPTY);
  const [touched, setTouched] = useState({});
  const [serverErrors, setServerErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [tab, setTab] = useState('all');

  const types = useMemo(() => {
    const list = (data.form?.problem_type_choices || []).filter(([v]) => v);
    return list.length ? list : FALLBACK_TYPES;
  }, [data]);

  const reports = useMemo(() => data.reports || [], [data]);
  const counts = useMemo(() => {
    const c = { all: reports.length };
    TABS.slice(1).forEach((t) => { c[t.key] = reports.filter((r) => r.status === t.key).length; });
    return c;
  }, [reports]);
  const visible = tab === 'all' ? reports : reports.filter((r) => r.status === tab);

  const errors = validate(values);
  const errorFor = (name) => (touched[name] && errors[name]) || serverErrors[name] || '';

  const set = (name) => (e) => {
    setValues((v) => ({ ...v, [name]: e.target.value }));
    if (serverErrors[name]) setServerErrors((s) => ({ ...s, [name]: '' }));
  };
  const blur = (name) => () => setTouched((t) => ({ ...t, [name]: true }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    setTouched({ course_name: true, problem_type: true, problem_title: true, problem_description: true });
    const first = Object.keys(errors)[0];
    if (first) {
      toast.error(errors[first]);
      document.getElementById(`sr-${first}`)?.focus();
      return;
    }
    setSubmitting(true);
    try {
      const res = await apiFetch('/student/reports/', { method: 'POST', body: new FormData(form) });
      // Django redirected back to /reports/: fresh (empty) form + the toast.
      form.reset();
      setValues(EMPTY);
      setTouched({});
      setServerErrors({});
      addMessages(res.messages);
      window.scrollTo(0, 0);
      setTab('all');
      reload();
    } catch (err) {
      const fieldErrors = err?.data?.errors || {};
      const mapped = Object.fromEntries(
        Object.entries(fieldErrors).map(([k, v]) => [k, Array.isArray(v) ? v.map((x) => x.message || x).join(' ') : String(v)]),
      );
      setServerErrors(mapped);
      toast.error(
        !err?.status || err.status >= 500
          ? 'Server is not responding. Please try again.'
          : Object.values(mapped)[0] || 'Could not submit your report. Please check the form.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="sr">
      <Toasts />

      <header className="sr-head">
        <p className="sr-eyebrow">Support</p>
        <h2 className="sr-title">Reports</h2>
        <p className="sr-sub">Experiencing an issue with your course? Tell us about it and our team will review it.</p>
      </header>

      <div className="sr-columns">
        {/* Form */}
        <section className="sr-panel sr-form-panel">
          <div className="sr-panel__head">
            <span className="sr-panel__icon"><i className="bi bi-flag-fill"></i></span>
            <div>
              <h3 className="sr-panel__title">Report a problem</h3>
              <p className="sr-panel__sub">We usually review reports within a day.</p>
            </div>
          </div>

          <div className="sr-tips">
            <strong><i className="bi bi-lightbulb-fill"></i> Before submitting</strong>
            <ul>
              <li>Describe your issue clearly and concisely.</li>
              <li>Mention the lesson or quiz name if applicable.</li>
              <li>Include any exact error messages shown.</li>
              <li>Explain what happened and what you expected.</li>
            </ul>
          </div>

          <form method="POST" noValidate onSubmit={handleSubmit}>
            <Field id="sr-course_name" label="Course name" icon="bi-book" error={errorFor('course_name')}>
              <input id="sr-course_name" type="text" name="course_name" className="sr-input" placeholder="Enter course name" maxLength={255}
                value={values.course_name} onChange={set('course_name')} onBlur={blur('course_name')} aria-invalid={Boolean(errorFor('course_name'))} required />
            </Field>

            <Field id="sr-problem_type" label="Problem type" icon="bi-folder2-open" error={errorFor('problem_type')}>
              <select id="sr-problem_type" name="problem_type" className="sr-input" value={values.problem_type}
                onChange={set('problem_type')} onBlur={blur('problem_type')} aria-invalid={Boolean(errorFor('problem_type'))} required>
                <option value="" disabled>Select problem type</option>
                {types.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </Field>

            <Field id="sr-problem_title" label="Problem title" icon="bi-type" error={errorFor('problem_title')} count={`${values.problem_title.length}/255`}>
              <input id="sr-problem_title" type="text" name="problem_title" className="sr-input" placeholder="e.g. Quiz 3 does not submit" maxLength={255}
                value={values.problem_title} onChange={set('problem_title')} onBlur={blur('problem_title')} aria-invalid={Boolean(errorFor('problem_title'))} required />
            </Field>

            <Field id="sr-problem_description" label="Describe your problem" icon="bi-chat-left-text" error={errorFor('problem_description')} hint="Include steps to reproduce and what you expected to happen.">
              <textarea id="sr-problem_description" name="problem_description" className="sr-input sr-textarea" placeholder="Explain your problem in detail…"
                value={values.problem_description} onChange={set('problem_description')} onBlur={blur('problem_description')} aria-invalid={Boolean(errorFor('problem_description'))} required></textarea>
            </Field>

            <button type="submit" className="sr-btn sr-btn--primary sr-btn--block" disabled={submitting}>
              {submitting ? <span className="sr-spinner" aria-hidden="true" /> : <i className="bi bi-send-fill"></i>}
              {submitting ? 'Submitting…' : 'Submit report'}
            </button>
          </form>
        </section>

        {/* My reports */}
        <section className="sr-panel">
          <div className="sr-panel__head sr-panel__head--split">
            <div>
              <p className="sr-eyebrow">History</p>
              <h3 className="sr-panel__title">My reports</h3>
            </div>
            <span className="sr-total">{reports.length} total</span>
          </div>

          <div className="sr-tabs" role="tablist" aria-label="Filter reports by status">
            {TABS.map((t) => (
              <button key={t.key} type="button" role="tab" aria-selected={tab === t.key}
                className={`sr-tab${tab === t.key ? ' is-active' : ''}`} onClick={() => setTab(t.key)}>
                {t.label}<span className="sr-tab__count">{counts[t.key] || 0}</span>
              </button>
            ))}
          </div>

          {visible.length ? (
            <ul className="sr-list">
              {visible.map((r, i) => {
                const st = STATUS[r.status] || { label: r.status_display || r.status, tone: 'grey', icon: 'bi-dot' };
                return (
                  <li key={r.id} className="sr-item" style={{ '--i': i }}>
                    <span className="sr-item__icon"><i className={`bi ${TYPE_ICON[r.problem_type] || 'bi-flag-fill'}`}></i></span>
                    <div className="sr-item__main">
                      <div className="sr-item__top">
                        <h4 className="sr-item__title">{r.problem_title}</h4>
                        <span className={`sr-status sr-status--${st.tone}`}><i className={`bi ${st.icon}`}></i> {r.status_display || st.label}</span>
                      </div>
                      <div className="sr-item__meta">
                        <span><i className="bi bi-book"></i> {r.course_name}</span>
                        <span><i className="bi bi-tag"></i> {r.problem_type_display || r.problem_type}</span>
                        <span><i className="bi bi-calendar3"></i> {djDate(r.created_at, 'd M Y, h:i A')}</span>
                      </div>
                      {r.problem_description ? <p className="sr-item__desc">{r.problem_description}</p> : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="sr-empty">
              <span className="sr-empty__icon"><i className={`bi ${reports.length ? 'bi-funnel' : 'bi-emoji-smile'}`}></i></span>
              <strong>{reports.length ? 'No reports with this status' : 'No reports yet'}</strong>
              <small>{reports.length ? 'Try another tab.' : 'Problems you report will appear here with their review status.'}</small>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const { data, ready, reload } = usePageData('/student/reports/');
  if (!ready) return <AdminLoader />;
  return <ReportsContent data={data || {}} reload={reload} />;
}
