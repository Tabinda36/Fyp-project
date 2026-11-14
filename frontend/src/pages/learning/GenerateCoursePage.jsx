import AdminLoader from '../../layouts/AdminLoader';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiFetch, ApiError } from '../../api/client';
import { useFlash } from '../../hooks/useFlash';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { dflt, truncatewords } from '../../utils/djangoFormat';
import css from './GenerateCoursePage.css?raw';

/*
 * Port of `student_dashboard/course_data/generate_course.html` (/generate_course/).
 * GET/POST /api/v1/learning/generate-course/.
 *
 * Owner-approved fix: the template wrapped everything in a second `.main-content`
 * (260px margin + padding applied twice). The wrapper is kept, without that class
 * and its padding utilities, so the content sits like every other student page.
 */
export default function GenerateCoursePage() {
  const { data, ready, reload } = usePageData('/learning/generate-course/');
  const navigate = useNavigate();
  const { addMessages } = useFlash();
  const [formKey, setFormKey] = useState(0);
  usePageAssets({ css });

  if (!ready) return <AdminLoader />;
  const { available_courses: availableCourses, suggested_courses: suggestedCourses, assessment } = data;

  const onSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/learning/generate-course/', { method: 'POST', body: new FormData(e.currentTarget) });
      addMessages(res.messages);
      navigate(res.redirect);
    } catch (err) {
      if (!(err instanceof ApiError)) throw err;
      addMessages(err.data.messages);
      // the view redirected back to /generate_course/ (a fresh page with an empty form)
      setFormKey((k) => k + 1);
      reload();
    }
  };

  return (
    <div className="w-100">
      <div className="container-fluid px-0">

        {/* Page Title Banner */}
        <div className="card p-3 mb-4 shadow-sm" style={{ borderRadius: '12px', border: '1.5px solid #D4AF37', background: '#ffffff' }} ref={greenLeftBorder}>
          <div className="d-flex align-items-center justify-content-between flex-wrap gap-2">
            <div>
              <h4 className="fw-bold mb-1" style={{ color: '#01411C' }}>
                <i className="bi bi-mortarboard-fill me-2" style={{ color: '#d4af37' }}></i>Academic Course Catalog &amp; Instant Enrollment
              </h4>
              <p className="text-muted mb-0 small">
                Choose your university-benchmarked curriculum. Pre-generated and loaded from database in milliseconds &mdash; zero wait time!
              </p>
            </div>
            <span className="badge" style={{ background: '#01411C', color: '#D4AF37', border: '1px solid #D4AF37', padding: '6px 14px', borderRadius: '20px', fontWeight: 700, fontSize: '0.8rem' }}>
              ⚡ Instant DB Fetch
            </span>
          </div>
        </div>

        {/* 1. RECOMMENDED COURSES & UNIVERSITY BENCHMARK TIERS */}
        {suggestedCourses.length > 0 && (
          <>
            <div className="mb-4">
              <div className="d-flex align-items-center justify-content-between mb-3">
                <h6 className="fw-bold text-uppercase mb-0 tracking-wide small" style={{ color: '#01411C' }}>
                  <i className="bi bi-stars text-warning me-1"></i> Recommended Curricula Based On Your Assessment
                </h6>
                {assessment && (
                  <span className="small text-muted">
                    Goal: <strong>{dflt(assessment.learning_goal, 'Skill Improvement')}</strong>
                  </span>
                )}
              </div>

              {suggestedCourses.map((course) => (
                <div className="card p-3 p-md-4 shadow-sm mb-4" style={{ border: '2px solid #D4AF37', borderRadius: '14px', background: '#ffffff' }} key={course.id}>
                  {/* Course Master Info */}
                  <div className="d-flex align-items-center justify-content-between flex-wrap gap-3 pb-3 mb-3 border-bottom" ref={goldBottomBorder}>
                    <div className="d-flex align-items-center gap-3">
                      {course.image ? (
                        <img src={course.image} className="rounded-3 shadow-sm object-fit-cover" style={{ width: '70px', height: '70px', border: '1.5px solid #D4AF37' }} alt={course.title} />
                      ) : (
                        <div className="rounded-3 d-flex align-items-center justify-content-center" style={{ width: '70px', height: '70px', background: '#01411C', color: '#D4AF37', border: '1.5px solid #D4AF37' }}>
                          <i className="bi bi-journal-code fs-3"></i>
                        </div>
                      )}
                      <div>
                        <div className="d-flex align-items-center gap-2">
                          <h5 className="fw-bold mb-0 text-dark">{course.title}</h5>
                          {course.course_code && (
                            <span className="badge" style={{ background: 'linear-gradient(135deg, #d4af37, #b8860b)', color: '#064e3b', fontSize: '0.75rem', fontWeight: 800, borderRadius: '10px', padding: '3px 8px' }}>
                              {course.course_code}
                            </span>
                          )}
                        </div>
                        <p className="text-muted small mb-0 mt-1" style={{ maxWidth: '750px' }}>{truncatewords(course.description, 20)}</p>
                      </div>
                    </div>
                  </div>

                  {/* 3 University Benchmark Tiers Grid for this course */}
                  <div className="row g-3">
                    {course.course_levels.length ? course.course_levels.map((lvl) => (
                      <div className="col-md-4" key={lvl.id}>
                        <div className="p-3 rounded-3 h-100 d-flex flex-column justify-content-between" style={{ border: '1.5px solid #D4AF37', background: '#fafaf9' }}>
                          <div>
                            {/* University Header */}
                            <div className="d-flex align-items-center justify-content-between mb-2">
                              <span className="badge" style={{ background: '#01411C', color: '#D4AF37', fontWeight: 700, fontSize: '0.75rem' }}>
                                {lvl.level} Level
                              </span>
                              <span className="small fw-semibold text-muted">7-Day Plan</span>
                            </div>

                            <h6 className="fw-bold mb-1" style={{ color: '#01411C' }}>{lvl.title}</h6>

                            <div className="p-2 rounded-2 mb-2" style={{ background: 'rgba(212, 175, 55, 0.12)', fontSize: '0.78rem' }}>
                              <strong>🏛️ {lvl.benchmark}</strong>
                            </div>

                            <p className="text-muted small mb-3" style={{ fontSize: '0.8rem', lineHeight: 1.5 }}>
                              {truncatewords(lvl.description, 14)}
                            </p>
                          </div>

                          {/* Instant Fetch Action Button */}
                          <Link to={`/enroll-level/${lvl.slug}/`} className="btn w-100 py-2 fw-bold text-white small shadow-sm d-flex align-items-center justify-content-center gap-2" style={{ background: 'linear-gradient(135deg, #01411C, #047857)', border: '1px solid #D4AF37', borderRadius: '8px', textDecoration: 'none' }}>
                            <i className="bi bi-lightning-charge-fill text-warning"></i>
                            <span>Select &amp; Start Learning</span>
                          </Link>
                        </div>
                      </div>
                    )) : (
                      <div className="col-12 text-center py-2 text-muted small">
                        Loading university tiers for this course...
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="text-center my-4 fw-bold small position-relative">
              <span className="bg-light px-3 py-1 position-relative z-1 border rounded-pill shadow-xs" style={{ fontSize: '11px', color: '#01411C' }} ref={goldBorderColor}>─── OR CHOOSE FROM COMPLETE CATALOG ───</span>
            </div>
          </>
        )}

        {/* 2. QUICK ENROLLMENT & TIER SELECTOR BOX */}
        <div className="card p-3 p-md-4 shadow-sm mb-4" style={{ border: '2px solid #D4AF37', borderRadius: '14px', background: '#ffffff' }}>
          <div className="d-flex align-items-center gap-2 mb-3">
            <i className="bi bi-sliders text-warning fs-5"></i>
            <h5 className="fw-bold mb-0" style={{ color: '#01411C' }}>Custom Academic Path Selector</h5>
          </div>

          <form method="POST" action="/generate_course/" onSubmit={onSubmit} key={formKey}>

            {/* 1. Select Course */}
            <div className="mb-3">
              <label htmlFor="course_topic" className="form-label fw-bold small mb-1" style={{ color: '#01411C' }}>1. Select Master Course</label>
              <select name="course_topic" id="course_topic" className="form-select custom-select-style py-2" required defaultValue="">
                <option value="">-- Choose Course --</option>
                {availableCourses.length ? availableCourses.map((course) => (
                  <option value={course.id} key={course.id}>{course.course_code ? `[${course.course_code}] ` : ''}{course.title}</option>
                )) : (
                  <option value="" disabled>No courses available.</option>
                )}
              </select>
            </div>

            {/* 2. Select Academic Benchmark Tier */}
            <div className="mb-3">
              <label className="form-label fw-bold small mb-1" style={{ color: '#01411C' }}>2. Select University Benchmark Tier</label>
              <div className="row g-2">
                <div className="col-md-4">
                  <input type="radio" className="btn-check" name="level" id="level_beginner" value="Beginner" defaultChecked />
                  <label className="btn btn-outline-custom w-100 p-2 text-start small" htmlFor="level_beginner">
                    <div className="fw-bold text-danger">Tier 1: Beginner</div>
                    <div className="text-muted" style={{ fontSize: '0.75rem' }}>🏛️ Harvard CS50 Philosophy</div>
                  </label>
                </div>
                <div className="col-md-4">
                  <input type="radio" className="btn-check" name="level" id="level_intermediate" value="Intermediate" />
                  <label className="btn btn-outline-custom w-100 p-2 text-start small" htmlFor="level_intermediate">
                    <div className="fw-bold text-info">Tier 2: Intermediate</div>
                    <div className="text-muted" style={{ fontSize: '0.75rem' }}>🏛️ MIT Data Structures &amp; Logic</div>
                  </label>
                </div>
                <div className="col-md-4">
                  <input type="radio" className="btn-check" name="level" id="level_advanced" value="Advanced" />
                  <label className="btn btn-outline-custom w-100 p-2 text-start small" htmlFor="level_advanced">
                    <div className="fw-bold text-warning">Tier 3: Advanced</div>
                    <div className="text-muted" style={{ fontSize: '0.75rem' }}>🏛️ Stanford &amp; CMU Systems &amp; AI</div>
                  </label>
                </div>
              </div>
            </div>

            {/* 3. Pace Options */}
            <div className="mb-3">
              <label htmlFor="learning_pace" className="form-label fw-bold small mb-1" style={{ color: '#01411C' }}>3. Weekly Commitment (Pace)</label>
              <select className="form-select custom-select-style py-2" id="learning_pace" name="pace">
                <option value="Standard">Standard (3-5 hours/week)</option>
                <option value="Intense">Intense/Crash Course (10+ hours/week)</option>
              </select>
            </div>

            {/* 4. Goal */}
            <div className="mb-3">
              <label htmlFor="learning_objective" className="form-label fw-bold small mb-1" style={{ color: '#01411C' }}>4. Primary Goal / Objective</label>
              <textarea className="form-control custom-select-style" id="learning_objective" name="objective" rows="2" placeholder="e.g., Master computational algorithms, prepare for interviews, or build scalable systems..." defaultValue={assessment ? (assessment.learning_goal ?? '') : ''}></textarea>
            </div>

            {/* Instant Submit Button */}
            <div className="mt-3">
              <button type="submit" className="btn w-100 py-2 fw-bold text-white shadow-sm d-flex align-items-center justify-content-center gap-2" style={{ background: 'linear-gradient(135deg, #01411C, #047857)', borderRadius: '8px', border: '1.5px solid #D4AF37' }}>
                <i className="bi bi-lightning-charge-fill text-warning"></i>
                <span>Start Learning Instantly (Database Fetch)</span>
              </button>
              <div className="text-center mt-2">
                <span className="text-muted small" style={{ fontSize: '0.78rem' }}>
                  <i className="bi bi-shield-check text-success me-1"></i>Curriculum, assignments, and quizzes load instantaneously from pre-generated records.
                </span>
              </div>
            </div>
          </form>
        </div>

      </div>
    </div>
  );
}

/* Inline `!important` declarations of the template, applied through the CSSOM. */
function greenLeftBorder(el) {
  if (el) el.style.setProperty('border-left', '6px solid #01411C', 'important');
}

function goldBottomBorder(el) {
  if (el) el.style.setProperty('border-color', 'rgba(212, 175, 55, 0.3)', 'important');
}

function goldBorderColor(el) {
  if (el) el.style.setProperty('border-color', '#D4AF37', 'important');
}
