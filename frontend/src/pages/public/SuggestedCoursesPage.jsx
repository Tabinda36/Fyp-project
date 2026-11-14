// Port of main_front/suggested_courses.html (login required, standalone, dark background).
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { bootstrapTag, useFlash, useFlashMessages } from '../../hooks/useFlash';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { BOOTSTRAP_533, ICONS_1113, LOGO } from '../../cdn';
import rawCss from './SuggestedCoursesPage.css?raw';
import { ROOT_PASSTHROUGH } from './rootPassthrough';

const css = rawCss + ROOT_PASSTHROUGH;

const SELF = '/suggested_courses/';

export default function SuggestedCoursesPage() {
  usePageAssets({ links: [BOOTSTRAP_533, ICONS_1113], css, title: 'AI Course Recommendation & Next Steps | ALVIX' });
  const { data, ready, reload, setData } = usePageData('/public/suggested-courses/');
  const messages = useFlashMessages();
  const { addMessages, dismiss } = useFlash();
  const navigate = useNavigate();
  // { id: button id, text: loading text } while a choice form is submitting (handleChoiceSubmit)
  const [busy, setBusy] = useState(null);

  async function submitChoice(e, buttonId, loadingText) {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.currentTarget).entries());
    setBusy({ id: buttonId, text: loadingText });
    try {
      const res = await apiFetch('/public/suggested-courses/', { method: 'POST', body });
      if (res.redirect) {
        addMessages(res.messages);
        if (res.redirect === SELF) {
          setBusy(null);
          reload();
        } else {
          navigate(res.redirect);
        }
        return;
      }
      // The view re-rendered the page (payload + messages); usePageData pushes the messages.
      setBusy(null);
      setData(res);
    } catch (err) {
      setBusy(null);
      if (err.data?.messages) addMessages(err.data.messages);
      else reload();
    }
  }

  // data-bs-dismiss="alert" would remove a React-owned node; reproduce Bootstrap's fade + removal instead.
  function closeAlert(e, id) {
    e.stopPropagation();
    const el = e.currentTarget.closest('.alert');
    if (el) el.classList.remove('show');
    setTimeout(() => dismiss(id), 150);
  }

  const btnContent = (id, normal) =>
    busy && busy.id === id
      ? <><span className="spinner-border spinner-border-sm me-2" role="status"></span> {busy.text}</>
      : normal;

  if (!ready) return null;

  const sc = data.suggested_course;
  const level = data.suggested_level;

  return (
    <div className="container-box">
      {/* Header */}
      <div className="logo-wrapper">
        <div className="logo-circle">
          <img src={LOGO} alt="ALVIX Logo" />
        </div>
      </div>
      <h1 className="page-title">Personalized Course Placement</h1>
      <p className="subtitle">Based on your learning assessment, here is your AI-recommended path. The choice is always yours.</p>

      {/* Assessment Recap Bar */}
      <div className="recap-bar">
        <div className="recap-item">
          <i className="bi bi-person-fill me-1 text-warning"></i> Student: <strong>{data.student_name}</strong>
        </div>
        <div className="recap-item">
          <i className="bi bi-palette-fill me-1 text-warning"></i> Interest: <strong>{data.interest_area}</strong>
        </div>
        <div className="recap-item">
          <i className="bi bi-bullseye me-1 text-warning"></i> Goal: <strong>{data.goal}</strong>
        </div>
        <div className="recap-item">
          <i className="bi bi-lightning-fill me-1 text-warning"></i> Suggested Level: <strong>{level}</strong>
        </div>
      </div>

      {/* Alerts */}
      {messages.length > 0 && (
        <div className="mb-4">
          {messages.map((m) => (
            <div key={m.id} className={`alert alert-${bootstrapTag(m.tags)} alert-dismissible fade show`} role="alert">
              <i className="bi bi-info-circle-fill me-2"></i>{m.message}
              <button type="button" className="btn-close" data-bs-dismiss="alert" aria-label="Close" onClick={(e) => closeAlert(e, m.id)}></button>
            </div>
          ))}
        </div>
      )}

      {/* ================= 1. AI RECOMMENDED COURSE CARD ================= */}
      {sc && (
        <div className="recommendation-card">
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <span className="ai-badge">
              <i className="bi bi-stars"></i> Top AI Recommendation
            </span>
            <span className="badge" style={{ background: 'rgba(212, 175, 55, 0.15)', border: '1px solid #d4af37', color: '#064e3b', fontWeight: 700, padding: '6px 12px', borderRadius: '12px' }}>
              <i className="bi bi-award-fill me-1 text-warning"></i> Suggested Level: {level}
            </span>
          </div>

          <h2 className="course-title-lg">
            {sc.title}
            {sc.course_code ? (
              <>
                {' '}
                <span className="badge" style={{ background: 'linear-gradient(135deg, #d4af37, #b8860b)', color: '#064e3b', fontSize: '0.75rem', fontWeight: 800, borderRadius: '10px', padding: '4px 8px', verticalAlign: 'middle' }}>
                  {sc.course_code}
                </span>
              </>
            ) : null}
          </h2>

          <p className="text-muted small mb-0">{sc.description || 'Comprehensive academic curriculum designed for mastery.'}</p>

          {/* 2-Sentence AI Reason Referring to Student's Expectations */}
          <div className="ai-reason-box">
            <h6><i className="bi bi-chat-quote-fill text-warning"></i> Why This Course Was Selected For You</h6>
            <p>{data.ai_reason}</p>
          </div>
        </div>
      )}

      {/* ================= 2. THE THREE CHOICES (Always Student's Choice) ================= */}
      <h3 className="choices-section-title">
        <i className="bi bi-hand-index-thumb text-warning"></i> Select Your Next Step
      </h3>

      {/* CHOICE (b): Start the suggested course (student picks the level; suggested level is pre-selected) */}
      {sc && (
        <div className="choice-card" style={{ border: '2px solid #d4af37' }}>
          <div className="choice-header">
            <div className="d-flex align-items-center">
              <span className="choice-tag">B</span>
              <h4 className="choice-title">Start Suggested Course: {sc.title}</h4>
            </div>
            <span className="badge bg-success text-white small px-3 py-1">Recommended Choice</span>
          </div>
          <p className="choice-desc">
            Enroll directly in the recommended course. The AI-suggested benchmark level is pre-selected below, but you may choose whichever tier fits you best.
          </p>

          <form method="POST" id="formChoiceB" onSubmit={(e) => submitChoice(e, 'btnChoiceB', 'Enrolling in Course...')}>
            <input type="hidden" name="action" value="start_suggested" />

            {/* Level Selector with Suggested Level Pre-selected */}
            <div className="level-selector-grid">
              <div>
                <input type="radio" className="level-pill-radio" name="level" id="b_beg" value="Beginner" defaultChecked={level === 'Beginner'} />
                <label className="level-pill-label" htmlFor="b_beg">
                  Tier 1: Beginner
                  <small>CS50 Philosophy</small>
                </label>
              </div>
              <div>
                <input type="radio" className="level-pill-radio" name="level" id="b_int" value="Intermediate" defaultChecked={level === 'Intermediate'} />
                <label className="level-pill-label" htmlFor="b_int">
                  Tier 2: Intermediate
                  <small>MIT Logic &amp; Algorithms</small>
                </label>
              </div>
              <div>
                <input type="radio" className="level-pill-radio" name="level" id="b_adv" value="Advanced" defaultChecked={level === 'Advanced'} />
                <label className="level-pill-label" htmlFor="b_adv">
                  Tier 3: Advanced
                  <small>Stanford &amp; CMU Systems</small>
                </label>
              </div>
            </div>

            <div className="ms-md-5 ps-md-2">
              <button type="submit" className="btn-action-primary" id="btnChoiceB" disabled={busy?.id === 'btnChoiceB'}>
                {btnContent('btnChoiceB', <><i className="bi bi-play-circle-fill"></i> Start {sc.title}</>)}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* CHOICE (c): Pick any other existing course, or ask system to generate a new course from a title */}
      <div className="choice-card">
        <div className="choice-header">
          <div className="d-flex align-items-center">
            <span className="choice-tag">C</span>
            <h4 className="choice-title">Pick Another Existing Course or Generate a New Course</h4>
          </div>
        </div>
        <p className="choice-desc">
          Prefer a different subject? Pick another course from our active catalog, or type any course title to have our AI generate a complete university-benchmarked curriculum on demand.
        </p>

        <div className="ms-md-5 ps-md-2">
          {/* Tabs between Existing Catalog vs AI Generation */}
          <ul className="nav nav-tabs mb-3" id="choiceCTabs" role="tablist">
            <li className="nav-item" role="presentation">
              <button className="nav-link active" id="existing-tab" data-bs-toggle="tab" data-bs-target="#tabExisting" type="button" role="tab">
                <i className="bi bi-collection me-1"></i> Pick Other Existing Course
              </button>
            </li>
            <li className="nav-item" role="presentation">
              <button className="nav-link" id="custom-tab" data-bs-toggle="tab" data-bs-target="#tabCustom" type="button" role="tab">
                <i className="bi bi-magic me-1"></i> Generate New Course from Title
              </button>
            </li>
          </ul>

          <div className="tab-content" id="choiceCTabsContent">
            {/* Option C1: Pick other existing course */}
            <div className="tab-pane fade show active" id="tabExisting" role="tabpanel">
              <form method="POST" id="formChoiceC1" onSubmit={(e) => submitChoice(e, 'btnChoiceC1', 'Enrolling in Course...')}>
                <input type="hidden" name="action" value="pick_other_course" />

                <div className="row g-3 mb-3">
                  <div className="col-md-7">
                    <label className="form-label small fw-bold text-dark-green">Choose Existing Course</label>
                    <select name="other_course_id" className="form-select py-2" required defaultValue="">
                      <option value="" disabled>-- Select an Existing Course --</option>
                      {data.other_courses.length ? data.other_courses.map((oc) => (
                        <option key={oc.id} value={oc.id}>{oc.title}{oc.course_code ? ` [${oc.course_code}]` : ''}</option>
                      )) : (
                        <option value="" disabled>No other courses available.</option>
                      )}
                    </select>
                  </div>
                  <div className="col-md-5">
                    <label className="form-label small fw-bold text-dark-green">Select Level</label>
                    <select name="other_level" className="form-select py-2" defaultValue="Beginner">
                      <option value="Beginner">Tier 1: Beginner (Harvard)</option>
                      <option value="Intermediate">Tier 2: Intermediate (MIT)</option>
                      <option value="Advanced">Tier 3: Advanced (Stanford/CMU)</option>
                    </select>
                  </div>
                </div>

                <button type="submit" className="btn-action-primary" id="btnChoiceC1" disabled={busy?.id === 'btnChoiceC1'}>
                  {btnContent('btnChoiceC1', <><i className="bi bi-check-circle-fill"></i> Enroll in Selected Course</>)}
                </button>
              </form>
            </div>

            {/* Option C2: Generate new course from title (Prompt 3 flow) */}
            <div className="tab-pane fade" id="tabCustom" role="tabpanel">
              <form method="POST" id="formChoiceC2" onSubmit={(e) => submitChoice(e, 'btnChoiceC2', 'Generating Course via AI (Zero Wait)...')}>
                <input type="hidden" name="action" value="generate_new_course" />

                <div className="mb-3">
                  <label className="form-label small fw-bold text-dark-green">Type Custom Course Title</label>
                  <input type="text" name="custom_course_title" className="form-control py-2" placeholder="e.g. Cloud Computing with Kubernetes, or Cyber Defense Engineering" required />
                  <small className="text-muted" style={{ fontSize: '11px' }}>
                    <i className="bi bi-cpu me-1"></i>Our AI will architect a 7-day university-benchmarked curriculum tailored specifically to your title.
                  </small>
                </div>

                <div className="row g-3 mb-3">
                  <div className="col-md-6">
                    <label className="form-label small fw-bold text-dark-green">Select Benchmark Tier</label>
                    <select name="custom_level" className="form-select py-2" defaultValue="Beginner">
                      <option value="Beginner">Beginner (Foundations &amp; Clean Code)</option>
                      <option value="Intermediate">Intermediate (Data Structures &amp; Logic)</option>
                      <option value="Advanced">Advanced (Systems Architecture &amp; AI)</option>
                    </select>
                  </div>
                  <div className="col-md-6">
                    <label className="form-label small fw-bold text-dark-green">Weekly Commitment</label>
                    <select name="custom_pace" className="form-select py-2" defaultValue="Standard">
                      <option value="Standard">Standard (3-5 hrs/week)</option>
                      <option value="Intense">Intense (10+ hrs/week)</option>
                    </select>
                  </div>
                </div>

                <button type="submit" className="btn-action-primary" id="btnChoiceC2" disabled={busy?.id === 'btnChoiceC2'}>
                  {btnContent('btnChoiceC2', <><i className="bi bi-sparkles"></i> Generate &amp; Enroll in Course</>)}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      {/* CHOICE (a): Go directly to the dashboard */}
      <div className="choice-card">
        <div className="choice-header">
          <div className="d-flex align-items-center">
            <span className="choice-tag">A</span>
            <h4 className="choice-title">Go Directly to Dashboard</h4>
          </div>
        </div>
        <p className="choice-desc">
          You don&apos;t have to start a course right now. You can jump directly to your student dashboard to review notifications, manage settings, and explore at your own pace.
        </p>

        <div className="ms-md-5 ps-md-2">
          <Link to="/dashboard/" className="btn-action-outline">
            <i className="bi bi-speedometer2"></i> Skip to Dashboard
          </Link>
        </div>
      </div>

    </div>
  );
}
