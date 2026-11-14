import AdminLoader from '../../layouts/AdminLoader';
import { useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import css from './CourseDetailsPage.css?raw';
import NotFoundPage from '../NotFoundPage';
import { important } from './CoursePageUtils';

/* Port of admin_db/course_details.html. Tabs/collapses/accordions are Bootstrap data-API
   (Bootstrap JS is now loaded globally); "Expand All Topics" is the template's script. */

function QuizAccordion({ lessonId, quiz }) {
  return (
    <div className="accordion accordion-flush" id={`quizAccCourse_${lessonId}`}>
      {quiz.map((q, i) => {
        const n = i + 1;
        return (
          <div className="accordion-item bg-transparent" key={n}>
            <h2 className="accordion-header" id={`heading_cq_${lessonId}_${n}`}>
              <button className="accordion-button collapsed py-2 px-0 bg-transparent text-dark small fw-bold" type="button" data-bs-toggle="collapse" data-bs-target={`#collapse_cq_${lessonId}_${n}`}>
                Q{n}: {q.question_short}
              </button>
            </h2>
            <div id={`collapse_cq_${lessonId}_${n}`} className="accordion-collapse collapse" data-bs-parent={`#quizAccCourse_${lessonId}`}>
              <div className="accordion-body px-0 py-2 small">
                <p className="fw-semibold mb-2" style={{ color: '#064e3b' }}>{q.question}</p>
                <ul className="list-unstyled mb-2">
                  {q.options.map((opt, j) => (
                    <li key={j} className={`mb-1 ${opt.is_correct ? 'text-success fw-bold' : 'text-muted'}`}>
                      {opt.is_correct ? '✓' : '•'} {opt.text}
                    </li>
                  ))}
                </ul>
                {q.explanation && (
                  <div className="p-2 rounded bg-light border small text-muted">
                    <strong>Explanation:</strong> {q.explanation}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LessonTopic({ lesson }) {
  return (
    <div className="topic-item-card rounded-3 overflow-hidden" style={{ border: '1px solid rgba(212, 175, 55, 0.35)', background: '#fafaf9' }}>

      {/* Main Topic Trigger: Click to Expand / Collapse */}
      <button className="topic-btn-trigger collapsed w-100 p-3 text-start d-flex justify-content-between align-items-center gap-3 border-0" type="button" data-bs-toggle="collapse" data-bs-target={`#topicDetails_${lesson.id}`} aria-expanded="false" style={{ background: '#ffffff', cursor: 'pointer', transition: 'all 0.2s ease' }}>
        <div className="d-flex align-items-center gap-3">
          <span className="badge" style={{ background: '#064e3b', color: '#d4af37', borderRadius: '8px', fontSize: '0.82rem', padding: '6px 10px', fontWeight: 800 }}>
            L{lesson.order}
          </span>
          <div>
            <h6 className="fw-bold mb-0 text-success" style={{ fontSize: '1.02rem' }}>{lesson.title}</h6>
            <span className="small text-muted" style={{ fontSize: '0.82rem' }}>{lesson.summary}</span>
          </div>
        </div>
        <div className="d-flex align-items-center gap-2">
          <span className="badge bg-light text-dark border small fw-semibold">
            {lesson.estimated_minutes || '45'} mins
          </span>
          <span className="badge bg-warning-subtle text-warning-emphasis small fw-semibold d-none d-md-inline-block">
            Click to View Content
          </span>
          <i className="bi bi-chevron-down fs-6 text-muted topic-chevron"></i>
        </div>
      </button>

      {/* Collapsed Content Details (Hidden by Default) */}
      <div id={`topicDetails_${lesson.id}`} className="collapse topic-content-collapse">
        <div className="p-4" style={{ background: '#ffffff', borderTop: '1px dashed rgba(212, 175, 55, 0.3)' }}>

          {/* Reading Content */}
          <div className="mb-4">
            <h6 className="fw-bold text-uppercase small text-muted mb-2 tracking-wide">
              <i className="bi bi-book-fill text-warning me-1"></i> Core Long-form Reading Material
            </h6>
            <div className="p-3 rounded-3" style={{ background: '#fbfcfd', border: '1px solid rgba(212, 175, 55, 0.25)', maxHeight: '380px', overflowY: 'auto', fontSize: '0.9rem', lineHeight: 1.6 }} dangerouslySetInnerHTML={{ __html: lesson.reading_content }} />
          </div>

          {/* Code Examples Blueprints */}
          {lesson.code_examples.length > 0 && (
            <div className="mb-4">
              <h6 className="fw-bold text-uppercase small text-muted mb-2 tracking-wide">
                <i className="bi bi-code-slash text-info me-1"></i> Production Code Blueprints
              </h6>
              {lesson.code_examples.map((codeEx, i) => (
                <div className="mb-3 rounded-3 overflow-hidden" style={{ border: '1.5px solid rgba(212, 175, 55, 0.4)' }} key={i}>
                  <div className="px-3 py-2 bg-dark text-white d-flex justify-content-between align-items-center small">
                    <span className="fw-bold" style={{ color: '#d4af37' }}><i className="bi bi-file-earmark-code me-1"></i>{codeEx.title}</span>
                    <span className="badge bg-secondary-subtle text-secondary font-monospace">Production Ready</span>
                  </div>
                  <pre className="mb-0 p-3" style={{ background: '#0f172a', color: '#38bdf8', fontFamily: "'JetBrains Mono', monospace", fontSize: '0.85rem', overflowX: 'auto' }}>{codeEx.code}</pre>
                  {codeEx.explanation && (
                    <div className="p-2 bg-light text-muted small border-top">
                      <strong>Analysis:</strong> {codeEx.explanation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Enterprise Use Cases */}
          {lesson.use_cases.length > 0 && (
            <div className="mb-4">
              <h6 className="fw-bold text-uppercase small text-muted mb-2 tracking-wide">
                <i className="bi bi-building-check text-success me-1"></i> Enterprise &amp; Industry Use Cases
              </h6>
              <div className="row g-2">
                {lesson.use_cases.map((uc, i) => (
                  <div className="col-12" key={i}>
                    <div className="p-3 rounded-3" style={{ background: 'rgba(6, 78, 59, 0.04)', borderLeft: '4px solid #064e3b' }}>
                      <div className="fw-bold small text-dark mb-1"><i className="bi bi-gear-wide-connected me-1"></i>{uc.scenario}</div>
                      <p className="small text-muted mb-0">{uc.solution}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Daily Lab Challenge & Diagnostic Quiz */}
          <div className="row g-3 pt-3 border-top" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.25)' })}>
            {/* Assignment */}
            <div className="col-lg-6">
              <div className="p-3 rounded-3 h-100" style={{ background: '#fdfbf7', border: '1.5px solid #d4af37' }}>
                <div className="d-flex align-items-center justify-content-between mb-2">
                  <span className="fw-bold" style={{ color: '#064e3b' }}>
                    <i className="bi bi-pencil-square text-warning me-1"></i> Engineering Lab Challenge
                  </span>
                  <span className="badge bg-warning-subtle text-dark small">Rigorous Task</span>
                </div>
                <p className="small text-dark mb-2" style={{ whiteSpace: 'pre-line', lineHeight: 1.6 }}>
                  {'\n'}{lesson.assignment_prompt || "Implement the day's architectural blueprint and submit your code solution for automated review."}{'\n'}
                </p>
                {lesson.assignment_rubric && (
                  <div className="p-2 rounded-2 mt-2" style={{ background: '#ffffff', border: '1px dashed #d4af37', fontSize: '0.78rem', color: '#475569' }}>
                    <strong>Grading Rubric:</strong>
                    <div style={{ whiteSpace: 'pre-line' }}>{lesson.assignment_rubric}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Diagnostic Quiz */}
            <div className="col-lg-6">
              <div className="p-3 rounded-3 h-100" style={{ background: '#ffffff', border: '1.5px solid #064e3b' }}>
                <div className="d-flex align-items-center justify-content-between mb-2">
                  <span className="fw-bold text-success">
                    <i className="bi bi-patch-question text-success me-1"></i> Diagnostic Assessment (5 MCQs)
                  </span>
                  <span className="badge bg-success-subtle text-success small">Instant AI Grading</span>
                </div>
                {lesson.quiz_data.length > 0 ? (
                  <QuizAccordion lessonId={lesson.id} quiz={lesson.quiz_data} />
                ) : (
                  <p className="text-muted small mb-0">Automated diagnostic quiz synchronized with university benchmark syllabus.</p>
                )}
              </div>
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}

function DailyTopic({ dLes }) {
  return (
    <div className="topic-item-card rounded-3 overflow-hidden" style={{ border: '1px solid rgba(212, 175, 55, 0.35)', background: '#fafaf9' }}>
      <button className="topic-btn-trigger collapsed w-100 p-3 text-start d-flex justify-content-between align-items-center gap-3 border-0" type="button" data-bs-toggle="collapse" data-bs-target={`#topicDetailsDaily_${dLes.id}`} aria-expanded="false" style={{ background: '#ffffff', cursor: 'pointer' }}>
        <div className="d-flex align-items-center gap-3">
          <span className="badge" style={{ background: '#064e3b', color: '#d4af37', borderRadius: '8px', fontSize: '0.82rem', padding: '6px 10px', fontWeight: 800 }}>
            DAY {dLes.day_number}
          </span>
          <div>
            <h6 className="fw-bold mb-0 text-success" style={{ fontSize: '1.02rem' }}>{dLes.title}</h6>
            <span className="small text-muted" style={{ fontSize: '0.82rem' }}>{dLes.content_preview}</span>
          </div>
        </div>
        <div className="d-flex align-items-center gap-2">
          <a href={`/lesson/${dLes.id}/download-ppt/`} className="btn btn-sm btn-outline-warning text-dark py-1 px-2" title="Download PPT" onClick={(e) => e.stopPropagation()}>
            <i className="bi bi-file-earmark-ppt"></i> PPT
          </a>
          <i className="bi bi-chevron-down fs-6 text-muted topic-chevron"></i>
        </div>
      </button>
      <div id={`topicDetailsDaily_${dLes.id}`} className="collapse topic-content-collapse">
        <div className="p-4" style={{ background: '#ffffff', borderTop: '1px dashed rgba(212, 175, 55, 0.3)' }}>
          <div className="mb-4">
            <h6 className="fw-bold text-uppercase small text-muted mb-2"><i className="bi bi-book-fill text-warning me-1"></i> Day {dLes.day_number} Syllabus Content</h6>
            <div className="p-3 rounded-3" style={{ background: '#fbfcfd', border: '1px solid rgba(212, 175, 55, 0.25)', maxHeight: '380px', overflowY: 'auto' }} dangerouslySetInnerHTML={{ __html: dLes.content }} />
          </div>
          {dLes.task && (
            <div className="row g-3">
              <div className="col-md-6">
                <div className="p-3 rounded-3 h-100" style={{ background: '#fdfbf7', border: '1.5px solid #d4af37' }}>
                  <h6 className="fw-bold text-warning-emphasis mb-2"><i className="bi bi-pencil-square text-warning me-1"></i> Assignment Challenge</h6>
                  <p className="small text-dark mb-0" style={{ whiteSpace: 'pre-line' }}>{dLes.task.assignment_question}</p>
                </div>
              </div>
              <div className="col-md-6">
                <div className="p-3 rounded-3 h-100" style={{ background: '#ffffff', border: '1.5px solid #064e3b' }}>
                  <h6 className="fw-bold text-success mb-2"><i className="bi bi-patch-question text-success me-1"></i> Diagnostic Assessment</h6>
                  <p className="small text-muted mb-0">5 Diagnostic Questions pre-generated in database.</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function CourseDetailsPage() {
  usePageAssets({ css });
  const { slug } = useParams();
  const { data, ready, notFound } = usePageData(`/admin-courses/courses/${slug}/`);
  const contentRef = useRef(null);
  const [allExpanded, setAllExpanded] = useState(false);

  // toggleAllCourseDetailTopics() from the template.
  const toggleAllCourseDetailTopics = () => {
    const activePane = contentRef.current?.querySelector('.tab-pane.active') || document;
    const collapses = activePane.querySelectorAll('.topic-content-collapse');
    const triggers = activePane.querySelectorAll('.topic-btn-trigger');
    const anyOpen = Array.from(collapses).some((c) => c.classList.contains('show'));
    collapses.forEach((c) => (anyOpen ? c.classList.remove('show') : c.classList.add('show')));
    triggers.forEach((t) => {
      if (anyOpen) {
        t.classList.add('collapsed');
        t.setAttribute('aria-expanded', 'false');
      } else {
        t.classList.remove('collapsed');
        t.setAttribute('aria-expanded', 'true');
      }
    });
    setAllExpanded(!anyOpen);
  };

  if (notFound) return <NotFoundPage />;
  if (!ready) return <AdminLoader />;
  const { course, course_tiers: courseTiers, enrollments, enrolled_count: enrolledCount, total_modules: totalModules, total_lessons: totalLessons } = data;

  return (
    <div className="container-fluid px-4 py-3" ref={important({ 'max-width': '100%' })}>

      {/* Header with Back Button */}
      <div className="d-flex flex-wrap align-items-center justify-content-between border-bottom pb-3 mb-4" ref={important({ 'border-color': '#D4AF37' })}>
        <div>
          <span className="text-muted small fw-bold text-uppercase" style={{ letterSpacing: '1px' }} ref={important({ color: '#8C7320' })}>Course Management / Details</span>
          <div className="d-flex align-items-center gap-2 flex-wrap mt-1">
            <h2 className="fw-bold mb-0" style={{ color: '#01411C' }}><i className="bi bi-journal-check me-2 text-success"></i>{course.title}</h2>
            {course.course_code && (
              <span className="badge d-inline-flex align-items-center gap-1" style={{ background: 'linear-gradient(135deg, #d4af37, #b8860b)', color: '#064e3b', fontSize: '0.85rem', fontWeight: 800, borderRadius: '20px', padding: '6px 14px', boxShadow: '0 2px 8px rgba(212, 175, 55, 0.35)' }}>
                <i className="bi bi-tag-fill"></i> ID: {course.course_code}
              </span>
            )}
          </div>
        </div>
        <div className="d-flex gap-2">
          <Link to="/courses_info/" className="btn btn-outline-success btn-sm px-4 rounded-pill fw-semibold shadow-sm">
            <i className="bi bi-arrow-left me-1"></i> Back to Course List
          </Link>
        </div>
      </div>

      {/* Main Grid Content */}
      <div className="row g-4">
        {/* Left Side: Course Overview, AI Syllabus & Enrolled Students Table */}
        <div className="col-lg-8">

          {/* Course Overview Card */}
          <div className="dashboard-card p-4 p-md-4 mb-4 shadow-sm" style={{ background: 'white', borderRadius: '20px', border: '1px solid rgba(212, 175, 55, 0.25)' }}>
            {course.image && (
              <div className="mb-4 overflow-hidden rounded-4 shadow-sm" style={{ maxHeight: '280px', border: '1.5px solid #d4af37' }}>
                <img src={course.image} className="w-100 object-fit-cover" alt={course.title} style={{ maxHeight: '280px' }} />
              </div>
            )}

            <div className="d-flex justify-content-between align-items-center mb-3 pb-3 border-bottom">
              <span className="badge px-3 py-2 fs-6 fw-bold" style={{ backgroundColor: 'rgba(1, 65, 28, 0.08)', color: '#01411C', borderRadius: '8px' }}>
                <i className="bi bi-cpu-fill me-1 text-success"></i> AI-Powered Curriculum
              </span>
              <div className="d-flex gap-2">
                <span className="badge bg-warning text-dark px-3 py-2 fw-bold">Level: {course.level || 'All Levels'}</span>
                <span className="badge bg-success px-3 py-2 fw-bold">Status: Active</span>
              </div>
            </div>

            <h4 className="fw-bold text-dark mb-2">Course Description</h4>
            <p className="text-secondary lh-lg mb-4" style={{ fontSize: '1.02rem' }}>
              {course.description}
            </p>

            {/* University-Benchmarked Modules & Syllabus Breakdown */}
            <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3 mt-4 pt-2 border-top" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.25)' })}>
              <div>
                <h4 className="fw-bold text-dark mb-0">
                  <i className="bi bi-mortarboard-fill me-2" style={{ color: '#064e3b' }}></i>University Curriculum, Modules &amp; Syllabus Breakdown
                </h4>
                <p className="text-muted small mb-0 mt-1">
                  Harvard CS50, MIT, and Stanford/CMU tiers. Content details are collapsed by default—click any topic headline to expand full reading, code blueprints, and assessments.
                </p>
              </div>
              <div className="d-flex align-items-center gap-2 flex-wrap">
                <span className="badge" style={{ background: '#064e3b', color: '#d4af37', border: '1px solid #d4af37', fontWeight: 700, padding: '6px 12px', borderRadius: '20px' }}>
                  <i className="bi bi-collection-fill me-1"></i> {totalModules || '9'} Modules
                </span>
                <span className="badge bg-success fw-bold" style={{ padding: '6px 12px', borderRadius: '20px' }}>
                  <i className="bi bi-journal-check me-1"></i> {totalLessons || '30'} Lessons
                </span>
                <button type="button" className="btn btn-sm btn-outline-success rounded-pill fw-semibold shadow-sm" onClick={toggleAllCourseDetailTopics}>
                  <i className={allExpanded ? 'bi bi-arrows-collapse me-1' : 'bi bi-arrows-expand me-1'} id="toggleAllIcon"></i> <span id="toggleAllText">{allExpanded ? 'Collapse All Topics' : 'Expand All Topics'}</span>
                </button>
              </div>
            </div>

            {courseTiers.length > 0 ? (
              <>
                {/* Tier Navigation Tabs */}
                <ul className="nav nav-pills mb-4 gap-2 flex-wrap" id="tierTabs" role="tablist">
                  {courseTiers.map((tier, i) => (
                    <li className="nav-item" role="presentation" key={tier.id}>
                      <button className={`nav-link ${i === 0 ? 'active' : ''} rounded-pill px-4 py-2 fw-bold`} id={`tier-tab-${tier.id}`} data-bs-toggle="pill" data-bs-target={`#tier-pane-${tier.id}`} type="button" role="tab" style={{ fontSize: '0.9rem' }}>
                        {tier.level === 'Beginner' ? (
                          <><i className="bi bi-bank me-1 text-danger"></i> Harvard CS50 (Beginner)</>
                        ) : tier.level === 'Intermediate' ? (
                          <><i className="bi bi-cpu me-1 text-info"></i> MIT Logic (Intermediate)</>
                        ) : (
                          <><i className="bi bi-diagram-3-fill me-1 text-warning"></i> Stanford &amp; CMU (Advanced)</>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>

                {/* Tier Tab Content */}
                <div className="tab-content mb-4" id="tierTabsContent" ref={contentRef}>
                  {courseTiers.map((tier, i) => (
                    <div className={`tab-pane fade ${i === 0 ? 'show active' : ''}`} id={`tier-pane-${tier.id}`} role="tabpanel" key={tier.id}>

                      {/* Tier Header Card */}
                      <div className="p-3 mb-4 rounded-3 d-flex justify-content-between align-items-center flex-wrap gap-2" style={{ background: 'rgba(6, 78, 59, 0.05)', border: '1.5px solid rgba(212, 175, 55, 0.35)' }}>
                        <div>
                          <div className="d-flex align-items-center gap-2">
                            <span className="badge" style={{ background: '#064e3b', color: '#d4af37', fontWeight: 800, fontSize: '0.8rem', borderRadius: '8px' }}>
                              {String(tier.level).toUpperCase()} TIER
                            </span>
                            <h5 className="fw-bold text-dark mb-0">{tier.benchmark}</h5>
                          </div>
                          <p className="text-muted small mb-0 mt-1">{tier.benchmark_description}</p>
                        </div>
                        <div className="d-flex align-items-center gap-2">
                          <Link to={`/admindashboard/level/${tier.slug}/course/`} className="btn btn-sm btn-success fw-semibold rounded-pill px-3 shadow-sm">
                            <i className="bi bi-layers-half me-1"></i> Open Level Studio
                          </Link>
                        </div>
                      </div>

                      {/* Modules List for this Tier */}
                      {tier.modules.map((module) => (
                        <div className="module-group-block mb-4 p-3 rounded-3" style={{ background: '#ffffff', border: '1.5px solid #d4af37', boxShadow: '0 4px 12px rgba(212, 175, 55, 0.1)' }} key={module.id}>
                          {/* Module Title & Stats */}
                          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 pb-2 mb-3 border-bottom" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.25)' })}>
                            <div>
                              <span className="badge" style={{ background: '#064e3b', color: '#d4af37', fontSize: '0.75rem', fontWeight: 800, borderRadius: '6px', padding: '4px 8px' }}>
                                MODULE {module.order}
                              </span>
                              <h5 className="fw-bold mt-1 mb-0" style={{ color: '#064e3b' }}>{module.title}</h5>
                              {module.description && (
                                <p className="text-muted small mb-0 mt-1">{module.description}</p>
                              )}
                            </div>
                            <div className="d-flex align-items-center gap-2">
                              <span className="badge bg-light text-dark border small fw-semibold">
                                <i className="bi bi-clock me-1 text-warning"></i> ~{module.estimated_hours} Hours
                              </span>
                              <span className="badge bg-success-subtle text-success small fw-bold">
                                {module.lessons_count} Lessons
                              </span>
                            </div>
                          </div>

                          {/* Lessons Accordion (Collapsed by Default) */}
                          <div className="d-flex flex-column gap-2">
                            {module.lessons.map((lesson) => <LessonTopic lesson={lesson} key={lesson.id} />)}
                            {module.lessons.length === 0 && (
                              <div className="p-3 text-muted small text-center">No academic lessons registered in this module.</div>
                            )}
                          </div>

                        </div>
                      ))}
                      {tier.modules.length === 0 && (
                        /* Fallback to canonical lessons if modules not explicitly nested */
                        <div className="d-flex flex-column gap-2">
                          {tier.canonical_lessons.map((dLes) => <DailyTopic dLes={dLes} key={dLes.id} />)}
                          {tier.canonical_lessons.length === 0 && (
                            <div className="p-3 text-muted small text-center">No daily lessons registered for this tier.</div>
                          )}
                        </div>
                      )}

                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="alert alert-warning py-3 rounded-3 mb-4" role="alert">
                <i className="bi bi-exclamation-triangle-fill me-2"></i> University curriculum tiers are currently being synchronized.
              </div>
            )}

            {/* Admin Action Buttons */}
            <div className="d-flex flex-wrap gap-3 pt-3 border-top">
              <Link to="/courses_info/" className="btn btn-outline-success px-4 py-2 rounded-pill fw-semibold shadow-sm">
                <i className="bi bi-arrow-left me-2"></i>All Courses
              </Link>
            </div>
          </div>

          {/* Enrolled Students Table Section */}
          <div className="dashboard-card p-4 shadow-sm mb-4" style={{ background: 'white', borderRadius: '20px', border: '1px solid rgba(212, 175, 55, 0.25)' }}>
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="fw-bold text-dark mb-0"><i className="bi bi-people-fill me-2 text-success"></i>Students Enrolled In This Course</h5>
              <span className="badge bg-success rounded-pill px-3 py-2">{enrolledCount} Total</span>
            </div>

            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th scope="col">Student Name</th>
                    <th scope="col">Student ID</th>
                    <th scope="col">Email</th>
                    <th scope="col">Assignments &amp; Quizzes</th>
                    <th scope="col">Progress</th>
                    <th scope="col">Status</th>
                    <th scope="col">Enrolled Date</th>
                  </tr>
                </thead>
                <tbody>
                  {enrollments.map((item) => (
                    <tr key={item.id}>
                      <td className="fw-semibold text-dark">
                        <i className="bi bi-person-circle me-1 text-success"></i> {item.full_name}
                      </td>
                      <td>
                        <span className="badge px-2 py-1 fw-bold" style={{ background: 'linear-gradient(135deg, #d4af37, #b8860b)', color: '#064e3b', fontSize: '0.78rem' }}>
                          {item.student_id}
                        </span>
                      </td>
                      <td className="text-muted small">{item.email}</td>

                      {/* Assignments & Quizzes count */}
                      <td>
                        <span className="small text-dark fw-bold">A:</span> {item.attempted_assignments}/{item.total_assignments}<br />
                        <span className="small text-dark fw-bold">Q:</span> {item.attempted_quizzes}/{item.total_quizzes}
                      </td>

                      {/* Progress Percentage */}
                      <td>
                        <div className="progress mb-1" style={{ height: '6px', width: '90px' }}>
                          <div className="progress-bar bg-success" role="progressbar" style={{ width: `${item.progress}%` }}></div>
                        </div>
                        <small className="text-muted" style={{ fontSize: '11px' }}>{item.progress}% ({item.completed_lessons}/{item.total_lessons})</small>
                      </td>

                      {/* Status: Completed / Active */}
                      <td>
                        {item.status === 'Completed' ? (
                          <span className="badge bg-success px-2 py-1">Completed</span>
                        ) : (
                          <span className="badge px-2 py-1" style={{ background: '#064e3b', color: '#d4af37', border: '1px solid #d4af37' }}>Active</span>
                        )}
                      </td>

                      <td>
                        <small className="text-muted">{item.enrolled_at}</small>
                      </td>
                    </tr>
                  ))}
                  {enrollments.length === 0 && (
                    <tr>
                      <td colSpan="7" className="text-center text-muted py-4">
                        <i className="bi bi-info-circle me-1"></i> No students have generated or enrolled in this specific course yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Right Side: Instructor & Live Stats Sidebar */}
        <div className="col-lg-4">
          <div className="dashboard-card p-4 shadow-sm mb-4 text-center" style={{ background: 'white', borderRadius: '20px', border: '1px solid rgba(212, 175, 55, 0.25)' }}>
            <div className="mb-3 text-success fs-1 p-3 rounded-circle d-inline-flex align-items-center justify-content-center shadow-sm" style={{ backgroundColor: 'rgba(1, 65, 28, 0.08)' }}>
              <i className="bi bi-robot"></i>
            </div>
            <h4 className="fw-bold text-dark mb-1">Instructor Profile</h4>
            <p className="text-success fw-bold mb-3">ALVIX AI Autonomous Engine</p>
            <p className="text-muted small mb-4">This master course template is dynamically utilized and synchronized by student registration profiles.</p>

            <div className="p-3 rounded-3 mb-3 text-start" style={{ backgroundColor: 'rgba(1, 65, 28, 0.03)', border: '1px dashed rgba(212, 175, 55, 0.5)' }}>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted small">Course ID:</span>
                <strong className="text-dark small fw-bold" ref={important({ color: '#064e3b' })}>{course.course_code || course.slug}</strong>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted small">Course Slug:</span>
                <strong className="text-muted small" style={{ wordBreak: 'break-all' }}>{course.slug}</strong>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted small">Enrolled Students:</span>
                <strong className="text-dark">{enrolledCount} Students</strong>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted small">AI Generation Status:</span>
                <span className="badge bg-success">ON (Live)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
