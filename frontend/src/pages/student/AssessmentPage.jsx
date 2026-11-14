import AdminLoader from '../../layouts/AdminLoader';
import { useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiFetch } from '../../api/client';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { bootstrapTag, useFlash, useFlashMessages } from '../../hooks/useFlash';
import { useAuth } from '../../hooks/useAuth';
import DismissibleAlert from './DismissibleAlert';
import css from './AssessmentPage.css?raw';

/* Port of `student_dashboard/assessment.html` (/assessment/, ?retake=true). */

const INTEREST_OPTIONS = [
  { value: 'Creativity', icon: 'bi-palette-fill' },
  { value: 'Development', icon: 'bi-code-slash' },
  { value: 'Designing', icon: 'bi-bezier2' },
  { value: 'Marketing', icon: 'bi-megaphone-fill' },
];

const GOAL_OPTIONS = [
  { value: 'Practical', icon: 'bi-tools' },
  { value: 'Theory', icon: 'bi-book-half' },
  { value: 'Mixed', icon: 'bi-intersect' },
];

function AssessmentContent({ data, query }) {
  // Injected once the data is loaded, i.e. after StudentLayout's CSS (same cascade order as the template).
  usePageAssets({ css });

  const navigate = useNavigate();
  const { addMessages } = useFlash();
  const messages = useFlashMessages();
  const { refresh } = useAuth();
  const textareaRef = useRef(null);

  const [isRetake, setIsRetake] = useState(data.is_retake);
  const [values, setValues] = useState({
    interest_area: data.form.interest_area ?? '',
    goal: data.form.goal ?? '',
    expectations: data.form.expectations ?? '',
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const count = values.expectations.trim().length;
  const remaining = 20 - count;

  const setField = (name) => (event) => setValues((v) => ({ ...v, [name]: event.target.value }));

  const handleAssessmentSubmit = async (event) => {
    event.preventDefault();
    const val = textareaRef.current ? textareaRef.current.value.trim() : '';

    if (val.length < 20) {
      alert('Please provide at least 20 characters in the Expectations field before submitting.');
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
      return;
    }

    // Show loading state
    setSubmitting(true);
    const body = new FormData(event.currentTarget);
    try {
      const res = await apiFetch('/student/assessment/', { method: 'POST', body, query });
      await refresh();
      addMessages(res.messages); // added right before navigating so it shows on the next page
      navigate(res.redirect || '/suggested_courses/');
    } catch (err) {
      setSubmitting(false);
      if (err.status === 400) {
        setErrors(err.errors || {});
        if (err.data.form) {
          setValues({
            interest_area: err.data.form.interest_area ?? '',
            goal: err.data.form.goal ?? '',
            expectations: err.data.form.expectations ?? '',
          });
        }
        if (typeof err.data.is_retake === 'boolean') setIsRetake(err.data.is_retake);
        addMessages(err.data.messages);
        window.scrollTo(0, 0);
      } else {
        console.error('Error:', err);
        toast.error(!err.status || err.status >= 500
          ? 'Server is not responding. Your answers are still here, please try again.'
          : 'Could not submit your assessment. Please try again.');
      }
    }
  };

  const errorEntries = Object.entries(errors);

  const renderTiles = (group, options) =>
    options.map((opt) => (
      <label key={opt.value} className={`option-tile${values[group] === opt.value ? ' selected' : ''}`} data-group={group}>
        <input type="radio" name={group} value={opt.value} checked={values[group] === opt.value} onChange={setField(group)} required />
        <i className={`bi ${opt.icon} option-icon`}></i>
        <span>{opt.value}</span>
      </label>
    ));

  return (
    <div className="container">
      <div className="row justify-content-center">
        <div className="col-xl-9 col-lg-10">

          <div className="assessment-card">
            {/* Header */}
            <div className="assessment-header">
              <div className="assessment-badge">
                <i className="bi bi-patch-check-fill text-warning"></i>
                {isRetake ? 'Personal Assessment Update' : 'First-Login Student Assessment'}
              </div>
              <h1 className="assessment-title">
                {isRetake ? 'Retake Learning Assessment' : 'Welcome to ALVIX Learning'}
              </h1>
              <p className="assessment-subtitle">
                Please answer the 3 quick questions below to configure your adaptive learning profile and optimize your curriculum delivery.
              </p>
            </div>

            {/* Messages / Errors */}
            {messages.length > 0 && (
              <div className="mb-4">
                {messages.map((message) => (
                  <DismissibleAlert key={message.id} id={message.id} className={`alert alert-${bootstrapTag(message.tags)} alert-dismissible fade`}>
                    <i className="bi bi-info-circle-fill me-2"></i>{message.message}
                  </DismissibleAlert>
                ))}
              </div>
            )}

            {errorEntries.length > 0 && (
              <div className="alert alert-danger mb-4 rounded-3" role="alert">
                <div className="fw-bold mb-1"><i className="bi bi-exclamation-triangle-fill me-2"></i>Please resolve the following:</div>
                <ul className="mb-0 ps-3">
                  {errorEntries.map(([field, fieldErrors]) =>
                    fieldErrors.map((error, i) => <li key={`${field}-${i}`}>{error}</li>),
                  )}
                </ul>
              </div>
            )}

            <form method="POST" id="assessmentForm" onSubmit={handleAssessmentSubmit}>

              {/* QUESTION 1: Interest Area */}
              <div className="question-block">
                <div className="d-flex align-items-center mb-1">
                  <span className="question-number">1</span>
                  <span className="question-title">Interest Area</span>
                </div>
                <div className="question-desc">Select exactly one primary domain of interest for your studies.</div>

                <div className="option-grid">
                  {renderTiles('interest_area', INTEREST_OPTIONS)}
                </div>
              </div>

              {/* QUESTION 2: Goal */}
              <div className="question-block">
                <div className="d-flex align-items-center mb-1">
                  <span className="question-number">2</span>
                  <span className="question-title">Learning Goal</span>
                </div>
                <div className="question-desc">Choose your preferred pedagogical orientation and delivery style.</div>

                <div className="option-grid">
                  {renderTiles('goal', GOAL_OPTIONS)}
                </div>
              </div>

              {/* QUESTION 3: Expectations */}
              <div className="question-block">
                <div className="d-flex align-items-center mb-1">
                  <span className="question-number">3</span>
                  <span className="question-title">Expectations</span>
                </div>
                <div className="question-desc">
                  What do you actually want to learn from this course, and what do you expect to be able to do after it?
                </div>

                <div className="expectations-wrapper">
                  <textarea
                    name="expectations"
                    id="expectationsTextarea"
                    ref={textareaRef}
                    className="expectations-textarea"
                    placeholder="What do you actually want to learn from this course, and what do you expect to be able to do after it? (Minimum 20 characters)"
                    required
                    value={values.expectations}
                    onChange={setField('expectations')}
                  ></textarea>

                  <div className={`char-counter ${count >= 20 ? 'valid' : 'invalid'}`} id="charCounter">
                    <span id="charCountText">
                      <i className="bi bi-exclamation-circle me-1"></i>
                      {' '}<span id="currentCharCount">{count}</span> / 20 characters minimum
                    </span>
                    {count >= 20 ? (
                      <span id="charStatusText"><i className="bi bi-check-circle-fill me-1"></i> Requirement met</span>
                    ) : (
                      <span id="charStatusText">{`${remaining} more character${remaining === 1 ? '' : 's'} needed`}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Submission Action */}
              <div className="text-center mt-4 pt-2">
                <button type="submit" className="btn btn-submit-assessment px-5" id="submitBtn" disabled={submitting}>
                  {submitting ? (
                    <><span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Saving Assessment...</>
                  ) : (
                    <>
                      <i className="bi bi-check2-circle me-2"></i>
                      {' '}{isRetake ? 'Save & Update Profile' : 'Save Assessment & Continue'}
                    </>
                  )}
                </button>

                {isRetake && (
                  <div className="mt-3">
                    <Link to="/profile/" className="btn btn-link text-decoration-none text-muted fw-semibold">
                      <i className="bi bi-arrow-left me-1"></i> Back to Profile
                    </Link>
                  </div>
                )}
              </div>
            </form>

          </div>

        </div>
      </div>
    </div>
  );
}

export default function AssessmentPage() {
  const [searchParams] = useSearchParams();
  const retake = searchParams.get('retake') || undefined;
  const query = retake ? { retake } : undefined;
  const { data, ready } = usePageData('/student/assessment/', query);

  if (!ready) return <AdminLoader />;
  return <AssessmentContent key={retake || ''} data={data} query={query} />;
}
