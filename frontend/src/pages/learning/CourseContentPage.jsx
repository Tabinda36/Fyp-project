import AdminLoader from '../../layouts/AdminLoader';
import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { dflt } from '../../utils/djangoFormat';
import css from './CourseContentPage.css?raw';

/*
 * Port of `student_dashboard/course_data/course_content.html`
 * (/course_content/ and /course-content/, query `course_id`).
 * Data: GET /api/v1/learning/course-content/ — self-healing like the view (may enrol lessons on first load).
 */
export default function CourseContentPage() {
  const { search } = useLocation();
  const courseId = new URLSearchParams(search).get('course_id');
  const { data, ready } = usePageData('/learning/course-content/', { course_id: courseId });
  usePageAssets({ css });
  if (!ready) return <AdminLoader />;
  return <CourseContent key={search} data={data} />;
}

function CourseContent({ data }) {
  const {
    active_course: activeCourse,
    content_topics: contentTopics,
    course_type: courseType,
    plan_duration: planDuration,
    lessons,
  } = data;
  const ac = activeCourse?.admin_course;

  // Template script: swap the topic button between "Extend" and "Collapse" on show/hide.bs.collapse.
  const topicsRef = useRef(null);
  const [expanded, setExpanded] = useState({});
  useEffect(() => {
    const root = topicsRef.current;
    if (!root) return undefined;
    // Delegated (Bootstrap collapse events bubble), so topics rendered after a data change are covered.
    const isTopic = (el) => el?.matches?.('.topic-card .collapse');
    const onShow = (e) => { if (isTopic(e.target)) setExpanded((s) => ({ ...s, [e.target.id]: true })); };
    const onHide = (e) => { if (isTopic(e.target)) setExpanded((s) => ({ ...s, [e.target.id]: false })); };
    root.addEventListener('show.bs.collapse', onShow);
    root.addEventListener('hide.bs.collapse', onHide);
    return () => {
      root.removeEventListener('show.bs.collapse', onShow);
      root.removeEventListener('hide.bs.collapse', onHide);
    };
  }, []);

  return (
    <div className="container-fluid px-0">

      {/* HERO HEADER SHOWCASE BANNER */}
      <div className="hero-course-banner p-4 p-md-5 mb-4 rounded-4 shadow-lg text-white position-relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #022C22 0%, #064E3B 55%, #0F5A44 100%)', border: '2px solid #D4AF37' }}
        ref={heroShadow}>
        <div className="position-relative" style={{ zIndex: 2 }}>
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-3">
            <div className="d-flex align-items-center gap-2 flex-wrap">
              {activeCourse && ac?.course_code && (
                <span className="badge" style={{ background: 'linear-gradient(135deg, #D4AF37, #B8860B)', color: '#064E3B', fontWeight: 800, fontSize: '0.85rem', borderRadius: '20px', padding: '7px 16px' }}>
                  <i className="bi bi-tag-fill me-1"></i>{ac.course_code}
                </span>
              )}
              <span className="badge" style={{ background: 'rgba(212, 175, 55, 0.18)', color: '#FEF9E7', border: '1.5px solid #D4AF37', fontSize: '0.85rem', padding: '7px 16px', borderRadius: '20px', fontWeight: 700 }}>
                <i className="bi bi-clock-history me-1 text-warning"></i>{dflt(planDuration, 12)}-Day {dflt(courseType, 'Mixed')} Track
              </span>
              {activeCourse?.course_level ? (
                <span className="badge" style={{ background: '#064E3B', color: '#D4AF37', border: '1.5px solid #D4AF37', fontSize: '0.85rem', padding: '7px 16px', borderRadius: '20px', fontWeight: 700 }}>
                  <i className="bi bi-trophy-fill text-warning me-1"></i>{activeCourse.course_level.benchmark}
                </span>
              ) : activeCourse?.level ? (
                <span className="badge" style={{ background: '#064E3B', color: '#D4AF37', border: '1.5px solid #D4AF37', fontSize: '0.85rem', padding: '7px 16px', borderRadius: '20px', fontWeight: 700 }}>
                  <i className="bi bi-award-fill text-warning me-1"></i>{activeCourse.level} Benchmark
                </span>
              ) : null}
            </div>
            <div>
              <span className="badge bg-black bg-opacity-40 text-light border border-warning border-opacity-50 px-3 py-2 rounded-pill small">
                <i className="bi bi-shield-check text-warning me-1"></i> Verified Academic Syllabus
              </span>
            </div>
          </div>

          <h1 className="display-6 fw-bold mb-2 text-white" style={{ letterSpacing: '-0.5px', textShadow: '0 2px 8px rgba(0,0,0,0.4)' }}>
            <i className="bi bi-mortarboard-fill text-warning me-2"></i>
            {ac ? ac.title : dflt(activeCourse?.title, 'Masterclass Course')}
          </h1>
          <p className="mb-0 text-white-50" style={{ maxWidth: '820px', fontSize: '1rem', lineHeight: 1.6 }}>
            World-class university curriculum structured into core topics, interactive daily lessons, hands-on assignments, and concept quizzes with Inara, your personal AI teacher.
          </p>

          {/* Quick Metrics Strip */}
          <div className="d-flex align-items-center gap-4 mt-4 pt-3 border-top border-warning border-opacity-25 flex-wrap">
            <div className="d-flex align-items-center gap-2">
              <span className="badge rounded-circle p-2" style={{ background: 'rgba(212, 175, 55, 0.25)', color: '#D4AF37' }}><i className="bi bi-layers-half fs-6"></i></span>
              <span className="small text-light"><strong>{contentTopics.length}</strong> Syllabus Topics</span>
            </div>
            <div className="d-flex align-items-center gap-2">
              <span className="badge rounded-circle p-2" style={{ background: 'rgba(212, 175, 55, 0.25)', color: '#D4AF37' }}><i className="bi bi-play-circle-fill fs-6"></i></span>
              <span className="small text-light"><strong>{lessons.length}</strong> Masterclass Lectures</span>
            </div>
            <div className="d-flex align-items-center gap-2">
              <span className="badge rounded-circle p-2" style={{ background: 'rgba(212, 175, 55, 0.25)', color: '#D4AF37' }}><i className="bi bi-file-earmark-slides-fill fs-6"></i></span>
              <span className="small text-light"><strong>13+ Slides</strong> Per Lecture</span>
            </div>
            <div className="d-flex align-items-center gap-2">
              <span className="badge rounded-circle p-2" style={{ background: 'rgba(212, 175, 55, 0.25)', color: '#D4AF37' }}><i className="bi bi-patch-check-fill fs-6"></i></span>
              <span className="small text-light"><strong>35%</strong> Passing Grade</span>
            </div>
          </div>
        </div>
      </div>

      {/* MAIN TWO-COLUMN LAYOUT */}
      <div className="row g-4">
        {/* Left Column: Unified Course Content & Lesson Plan Container (Zero Awkward Gaps) */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm rounded-4 overflow-hidden mb-4" style={{ background: '#ffffff' }} ref={goldBorder2}>

            {/* UNIFIED CONTAINER HEADER & NAVIGATION TABS */}
            <div className="card-header bg-white border-bottom border-warning-subtle p-3 px-md-4">
              <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
                <div>
                  <span className="badge" style={{ background: '#064E3B', color: '#D4AF37', fontWeight: 700, fontSize: '0.78rem', padding: '5px 12px', borderRadius: '8px' }}>
                    <i className="bi bi-diagram-3-fill me-1"></i> CURRICULUM HUB
                  </span>
                  <h4 className="fw-bold text-success mb-0 mt-1">Course Content &amp; Lesson Schedule</h4>
                </div>

                {/* Seamless Tab Buttons */}
                <ul className="nav nav-pills gap-2" id="curriculumTabs" role="tablist">
                  <li className="nav-item" role="presentation">
                    <button className="nav-link active px-3 py-2 fw-bold rounded-pill shadow-xs" id="schedule-tab-btn" data-bs-toggle="pill" data-bs-target="#schedule-tab" type="button" role="tab" style={{ fontSize: '0.88rem' }}>
                      <i className="bi bi-calendar2-week-fill me-1 text-warning"></i> Lesson Plan ({planDuration}-Day {courseType} Track)
                    </button>
                  </li>
                  <li className="nav-item" role="presentation">
                    <button className="nav-link px-3 py-2 fw-bold rounded-pill shadow-xs" id="topics-tab-btn" data-bs-toggle="pill" data-bs-target="#topics-tab" type="button" role="tab" style={{ fontSize: '0.88rem' }}>
                      <i className="bi bi-layers-half me-1 text-warning"></i> Course Content ({contentTopics.length} Topics)
                    </button>
                  </li>
                </ul>
              </div>
            </div>

            <div className="card-body p-3 p-md-4">
              <div className="tab-content" id="curriculumTabContent">

                {/* TAB 1: INTERACTIVE DAILY LESSON PLAN */}
                <div className="tab-pane fade show active" id="schedule-tab" role="tabpanel">
                  <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-light-subtle">
                    <div>
                      <h5 className="fw-bold mb-1 text-success"><i className="bi bi-calendar2-week-fill me-2 text-warning"></i>Lesson Plan</h5>
                      <p className="text-muted small mb-0">
                        <strong>{planDuration}-Day {courseType} Track:</strong> Topics distributed across the schedule. Each day contains exactly one lesson, one assignment, and one quiz.
                      </p>
                    </div>
                    <span className="badge golden-badge px-3 py-2 rounded-pill fs-7">{lessons.length} of {planDuration} Days</span>
                  </div>

                  <div className="ai-generated-content">
                    {lessons.length ? (
                      <div className="d-flex flex-column gap-3" id="lessonsAccordion">
                        {lessons.map((lesson) => (
                          <div className="card lesson-card border-0 shadow-sm rounded-4 overflow-hidden" style={{ background: '#fdfcf9' }} ref={greyBorder} key={lesson.id}>
                            <div className="card-header bg-white border-bottom border-warning-subtle d-flex justify-content-between align-items-center py-3 px-3 px-md-4 flex-wrap gap-2">
                              <div className="d-flex align-items-center gap-3">
                                <span className="badge rounded-circle p-2 fw-bold shadow-xs" style={{ background: 'linear-gradient(135deg, #064E3B, #106E53)', color: '#D4AF37', minWidth: '42px', minHeight: '42px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.95rem', border: '1.5px solid #D4AF37' }}>
                                  D{lesson.day_number}
                                </span>
                                <div>
                                  <h5 className="mb-1 fw-bold text-success">{lesson.title}</h5>
                                  <div className="d-flex align-items-center gap-2 flex-wrap">
                                    <span className="badge bg-success-subtle text-success border border-success small" style={{ fontSize: '0.72rem' }}>
                                      <i className="bi bi-check-circle-fill me-1"></i>1 Lesson
                                    </span>
                                    <span className="badge bg-warning-subtle text-dark border border-warning small" style={{ fontSize: '0.72rem' }}>
                                      <i className="bi bi-pencil-square me-1"></i>1 Assignment
                                    </span>
                                    <span className="badge bg-primary-subtle text-primary border border-primary small" style={{ fontSize: '0.72rem' }}>
                                      <i className="bi bi-question-square me-1"></i>1 Quiz
                                    </span>
                                  </div>
                                </div>
                              </div>

                              {/* ACTION BUTTONS */}
                              <div className="d-flex gap-2 align-items-center flex-wrap">
                                <Link to={`/daily-lesson/${lesson.id}/`} className="btn btn-sm btn-golden fw-bold rounded-pill px-3 shadow-sm" title="Launch Lesson Presentation Player">
                                  <i className="bi bi-play-circle-fill me-1"></i> Lesson
                                </Link>
                                {lesson.has_real_video && (
                                  <Link to={`/daily-lesson/${lesson.id}/?mode=video`} className="btn btn-sm btn-success fw-semibold rounded-pill px-3 shadow-sm video-status-btn" id={`video-btn-${lesson.id}`} title="Watch Masterclass Video Lecture">
                                    <i className="bi bi-camera-video-fill me-1 text-warning"></i> Video
                                  </Link>
                                )}
                                <a href={`/lesson/${lesson.id}/download-ppt/`} className="btn btn-sm fw-semibold text-dark shadow-sm rounded-pill px-3" style={{ backgroundColor: '#D4AF37', border: '1px solid #c49f27' }} title="Download Teacher Masterclass PPT (.pptx)">
                                  <i className="bi bi-file-earmark-slides-fill me-1 text-dark"></i> PPT
                                </a>
                                <Link to={`/assignment/?lesson_id=${lesson.id}`} className="btn btn-sm btn-outline-golden rounded-pill px-3 fw-semibold shadow-xs" title="View Assignment">
                                  <i className="bi bi-pencil-square me-1"></i> Assignment
                                </Link>
                                <Link to={`/quiz/?lesson_id=${lesson.id}`} className="btn btn-sm btn-outline-success rounded-pill px-3 fw-semibold shadow-xs" title="Take Quiz">
                                  <i className="bi bi-question-square-fill me-1"></i> Quiz
                                </Link>
                              </div>
                            </div>
                            <div className="card-body p-3 p-md-4">
                              <div className="text-secondary mb-3" style={{ fontSize: '0.95rem', lineHeight: 1.6 }} dangerouslySetInnerHTML={{ __html: lesson.content }} />
                              {lesson.video_script && (
                                <div className="mt-2">
                                  <button className="btn btn-sm btn-outline-golden fw-semibold rounded-pill px-3" type="button" data-bs-toggle="collapse" data-bs-target={`#script-${lesson.id}`}>
                                    <i className="bi bi-code-square me-1"></i> View Video Script / Notes
                                  </button>
                                  <div className="collapse mt-2" id={`script-${lesson.id}`}>
                                    <div className="card card-body bg-dark text-light font-monospace small border-0 golden-border rounded-3">
                                      <pre className="mb-0 text-wrap text-warning" style={{ fontSize: '0.85rem' }}>{lesson.video_script}</pre>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-5">
                        <i className="bi bi-journal-x fs-1 text-muted mb-3 d-block"></i>
                        <p className="text-muted fw-semibold">No active lessons found. Please select a course tier to get started.</p>
                        <Link to="/generate_course/" className="btn btn-golden rounded-pill px-4">Browse University Courses</Link>
                      </div>
                    )}
                  </div>
                </div>

                {/* TAB 2: UNIVERSITY SYLLABUS TOPICS */}
                <div className="tab-pane fade" id="topics-tab" role="tabpanel">
                  <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-light-subtle">
                    <div>
                      <h5 className="fw-bold mb-1 text-success"><i className="bi bi-layers-half me-2 text-warning"></i>Course Content</h5>
                      <p className="text-muted small mb-0">Main topics taught by top-ranked universities. Click <strong>Extend</strong> on any topic to inspect what you will study.</p>
                    </div>
                    <span className="badge golden-badge px-3 py-2 rounded-pill fs-7">{contentTopics.length} Main Topics</span>
                  </div>

                  <div className="topics-accordion" id="courseTopicsList" ref={topicsRef}>
                    {contentTopics.length ? (
                      <div className="d-flex flex-column gap-3">
                        {contentTopics.map((topic, i) => {
                          const n = i + 1;
                          const open = Boolean(expanded[`topic-collapse-${n}`]);
                          return (
                            <div className="card topic-card border-0 shadow-sm rounded-4 overflow-hidden" style={{ background: '#ffffff' }} ref={greyBorder} key={n}>
                              <div className="card-header bg-white d-flex justify-content-between align-items-center py-3 px-3 px-md-4 flex-wrap gap-2">
                                <div className="d-flex align-items-center gap-3">
                                  <span className="badge golden-badge rounded-pill px-3 py-2 fs-7">
                                    Topic {n}
                                  </span>
                                  <h5 className="mb-0 fw-bold text-success">{topic.title}</h5>
                                </div>
                                <button className={`btn btn-sm ${open ? '' : 'btn-golden '}extend-btn px-3 py-1 fw-bold rounded-pill shadow-xs${open ? ' btn-outline-golden' : ''}`}
                                  type="button"
                                  data-bs-toggle="collapse"
                                  data-bs-target={`#topic-collapse-${n}`}
                                  aria-expanded="false"
                                  aria-controls={`topic-collapse-${n}`}
                                  id={`extend-btn-${n}`}>
                                  {open
                                    ? <><i className="bi bi-arrows-angle-contract me-1"></i>Collapse</>
                                    : <><i className="bi bi-arrows-angle-expand me-1"></i>Extend</>}
                                </button>
                              </div>
                              <div className="collapse" id={`topic-collapse-${n}`}>
                                <div className="card-body bg-light border-top border-warning-subtle p-3 p-md-4">
                                  <div className="d-flex align-items-center justify-content-between mb-3">
                                    <span className="text-uppercase small fw-bold text-success">
                                      <i className="bi bi-mortarboard-fill me-1 text-warning"></i>What You Will Study in this Topic ({topic.bullets.length} Modules):
                                    </span>
                                    <span className="badge bg-success-subtle text-success border border-success small">University Syllabus Standard</span>
                                  </div>
                                  <ul className="list-unstyled mb-0">
                                    {topic.bullets.length ? topic.bullets.map((bullet, j) => (
                                      <li className="py-2 px-3 mb-2 bg-white rounded-3 border border-light-subtle d-flex align-items-start gap-2 shadow-xs" key={j}>
                                        <span className="badge rounded-pill bg-success text-white fw-bold mt-1" style={{ fontSize: '0.7rem' }}>{j + 1}</span>
                                        <span className="small text-dark fw-medium" style={{ lineHeight: 1.6 }}>{bullet}</span>
                                      </li>
                                    )) : (
                                      <li className="text-muted small">Topic syllabus details will appear here.</li>
                                    )}
                                  </ul>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="p-4 bg-light rounded-4 text-center text-muted">
                        <i className="bi bi-journal-text fs-2 text-warning mb-2 d-block"></i>
                        Course topics are being calibrated according to university benchmarks.
                      </div>
                    )}
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>

        {/* Right Side: AI Tutor Insights & Curriculum Architecture Summary */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm rounded-4 overflow-hidden p-4 mb-4" style={{ background: '#ffffff' }} ref={goldBorder2}>
            {activeCourse && ac && ac.image && (
              <div className="mb-3 rounded-3 overflow-hidden shadow-sm" style={{ height: '160px', border: '1.5px solid #d4af37' }}>
                <img src={ac.image} className="w-100 h-100 object-fit-cover" alt={ac.title} />
              </div>
            )}
            <div className="text-center mb-3">
              <span className="badge rounded-circle p-3 mb-2 shadow-xs" style={{ background: '#064E3B', color: '#D4AF37' }}>
                <i className="bi bi-cpu fs-3"></i>
              </span>
              <h5 className="fw-bold text-success mb-1">Curriculum Architecture</h5>
              {activeCourse && (
                <p className="text-muted small mb-0">Benchmarked for <strong>{dflt(activeCourse.level, 'Beginner')}</strong> level based on academic rank.</p>
              )}
            </div>

            {activeCourse ? (
              <>
                <hr className="golden-hr my-3" />
                <div className="d-flex flex-column gap-2 mb-3">
                  <div className="d-flex justify-content-between align-items-center py-2 px-3 rounded-3 bg-light border border-light-subtle">
                    <span className="small text-muted"><i className="bi bi-compass me-1 text-success"></i> Course Track:</span>
                    <strong className="small text-success">{courseType}</strong>
                  </div>
                  <div className="d-flex justify-content-between align-items-center py-2 px-3 rounded-3 bg-light border border-light-subtle">
                    <span className="small text-muted"><i className="bi bi-clock me-1 text-warning"></i> Total Duration:</span>
                    <strong className="small text-dark">{planDuration} Days</strong>
                  </div>
                  <div className="d-flex justify-content-between align-items-center py-2 px-3 rounded-3 bg-light border border-light-subtle">
                    <span className="small text-muted"><i className="bi bi-layers me-1 text-primary"></i> Main Topics:</span>
                    <strong className="small text-dark">{contentTopics.length} Topics</strong>
                  </div>
                  <div className="d-flex justify-content-between align-items-center py-2 px-3 rounded-3 bg-light border border-light-subtle">
                    <span className="small text-muted"><i className="bi bi-check2-circle me-1 text-success"></i> Daily Plan:</span>
                    <strong className="small text-success">1 Lesson, 1 Task, 1 Quiz</strong>
                  </div>
                  <div className="d-flex justify-content-between align-items-center py-2 px-3 rounded-3 bg-light border border-light-subtle">
                    <span className="small text-muted"><i className="bi bi-file-earmark-slides me-1 text-warning"></i> Slide Decks:</span>
                    <strong className="small text-warning">Web View + PPTX</strong>
                  </div>
                </div>

                <div className="card border-0 p-3 rounded-3 mb-3" style={{ background: '#FEF9E7' }} ref={goldBorder1}>
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <i className="bi bi-patch-check-fill text-success fs-5"></i>
                    <h6 className="fw-bold text-dark mb-0">Certificate Qualification</h6>
                  </div>
                  <p className="small text-muted mb-0" style={{ lineHeight: 1.5 }}>
                    Achieve a cumulative score of at least <strong>35%</strong> across lesson watch-time, assignments, and quizzes to unlock your verified course certificate.
                  </p>
                </div>

                <hr className="golden-hr my-3" />
                <div className="row g-2 text-center">
                  <div className="col-4">
                    <div className="p-2 rounded-3 bg-light border">
                      <h5 className="fw-bold text-success mb-0">{lessons.length}</h5>
                      <small className="text-muted" style={{ fontSize: '0.72rem' }}>Lessons</small>
                    </div>
                  </div>
                  <div className="col-4">
                    <div className="p-2 rounded-3 bg-light border">
                      <h5 className="fw-bold text-success mb-0">{lessons.length}</h5>
                      <small className="text-muted" style={{ fontSize: '0.72rem' }}>Assignments</small>
                    </div>
                  </div>
                  <div className="col-4">
                    <div className="p-2 rounded-3 bg-light border">
                      <h5 className="fw-bold text-success mb-0">{lessons.length}</h5>
                      <small className="text-muted" style={{ fontSize: '0.72rem' }}>Quizzes</small>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-muted small text-center mb-0">No course active. Generate your personalized learning plan.</p>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}

/*
 * Inline `!important` declarations of the template (React's style prop cannot express them),
 * applied through the CSSOM with the same priority.
 */
function heroShadow(el) {
  if (el) el.style.setProperty('box-shadow', '0 12px 35px rgba(6, 78, 59, 0.3)', 'important');
}

function goldBorder2(el) {
  if (el) el.style.setProperty('border', '2px solid #D4AF37', 'important');
}

function goldBorder1(el) {
  if (el) el.style.setProperty('border', '1px solid #D4AF37', 'important');
}

function greyBorder(el) {
  if (el) el.style.setProperty('border', '1.5px solid #e2e8f0', 'important');
}
