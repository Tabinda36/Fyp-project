import AdminLoader from '../../layouts/AdminLoader';
import { Fragment, useEffect, useState } from 'react';
import { Link, Navigate, useParams, useSearchParams } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { useFlash } from '../../hooks/useFlash';
import { apiFetch } from '../../api/client';
import { ICONS_1113, googleFont } from '../../cdn';
import css from './LevelCourseViewPage.css?raw';
import { important } from './CoursePageUtils';
import { cleanupModals } from './adminModals';
import NotFoundPage from '../NotFoundPage';

/* Port of admin_db/level_course_view.html (?regenerate=1). Tabs, collapses, accordions and the
   per-lesson upload modals are Bootstrap data-API (Bootstrap JS is now loaded globally). */

const FONT = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700');

// `.visual-preview-box` is `white-space: pre`, so the template's whitespace around the value showed.
const VISUAL_LEAD = `\n${' '.repeat(44)}`;
const VISUAL_TRAIL = `\n${' '.repeat(40)}`;

export const REGEN_CONFIRM ='Trigger deep AI regeneration with Gemini? This will synthesize an exhaustive multi-module curriculum and 20+ slide lecture deck.';

/* The template's toggleAllCurriculumLessons() / toggleAllDailyLessons(): flip every collapse in
   the pane based on whether any is open, then return the new "expanded" state for the label. */
function toggleAll(paneId, collapseSelector, triggerSelector) {
  const pane = document.getElementById(paneId);
  if (!pane) return null;
  const collapses = pane.querySelectorAll(collapseSelector);
  const triggers = pane.querySelectorAll(triggerSelector);
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
  return !anyOpen;
}

function CurriculumLesson({ lesson }) {
  return (
    <div className="lesson-card-item">
      {/* Accordion Header */}
      <button className="lesson-btn-trigger collapsed" type="button" data-bs-toggle="collapse" data-bs-target={`#lessonCollapse${lesson.id}`} aria-expanded="false">
        <div className="d-flex align-items-center gap-3">
          <span className="badge" style={{ background: '#064e3b', color: '#d4af37', borderRadius: '8px', fontSize: '0.8rem', padding: '6px 10px' }}>
            L{lesson.order}
          </span>
          <div>
            <h5 className="fw-bold mb-0 text-success" style={{ fontSize: '1.05rem' }}>{lesson.title}</h5>
            <span className="small text-muted">{lesson.summary}</span>
          </div>
        </div>
        <div className="d-flex align-items-center gap-2">
          <span className="badge bg-light text-dark border small fw-semibold">
            {lesson.estimated_minutes} mins
          </span>
          <i className="bi bi-chevron-down fs-6 text-muted"></i>
        </div>
      </button>

      {/* Accordion Body */}
      <div id={`lessonCollapse${lesson.id}`} className="collapse">
        <div className="p-4" style={{ background: '#ffffff' }}>

          {/* Long-form Textbook Reading Material */}
          <div className="mb-4">
            <h6 className="fw-bold text-uppercase small text-muted mb-2 tracking-wide">
              <i className="bi bi-book-fill text-warning me-1"></i> Core Long-form Reading Material
            </h6>
            <div className="p-3 rounded-3" style={{ background: '#fbfcfd', border: '1px solid rgba(212, 175, 55, 0.25)' }} dangerouslySetInnerHTML={{ __html: lesson.reading_content }} />
          </div>

          {/* Code Architecture Blueprints */}
          {lesson.code_examples.length > 0 && (
            <div className="mb-4">
              <h6 className="fw-bold text-uppercase small text-muted mb-2 tracking-wide">
                <i className="bi bi-code-slash text-info me-1"></i> Production Code Blueprints
              </h6>
              {lesson.code_examples.map((codeEx, i) => (
                <div className="mb-3 rounded-3 overflow-hidden" style={{ border: '1.5px solid rgba(212, 175, 55, 0.4)' }} key={i}>
                  <div className="px-3 py-2 bg-dark text-white d-flex justify-content-between align-items-center small">
                    <span className="fw-bold" style={{ color: '#d4af37' }}><i className="bi bi-file-earmark-code me-1"></i>{codeEx.title}</span>
                    <span className="badge bg-secondary-subtle text-secondary font-monospace">Python/Enterprise</span>
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

          {/* Real-World Enterprise Use Cases */}
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

          {/* Assessment: Engineering Lab Challenge & Diagnostic Quiz */}
          <div className="row g-3 pt-3 border-top" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.25)' })}>
            {/* Assignment Box */}
            <div className="col-lg-6">
              <div className="p-3 rounded-3 h-100" style={{ background: '#f8fafc', border: '1.5px solid #d4af37' }}>
                <div className="d-flex align-items-center justify-content-between mb-2">
                  <span className="fw-bold" style={{ color: '#064e3b' }}>
                    <i className="bi bi-pencil-square text-warning me-1"></i> Engineering Lab Challenge
                  </span>
                  <span className="badge bg-warning-subtle text-dark small">Rigorous Task</span>
                </div>
                <p className="small text-muted mb-2" style={{ whiteSpace: 'pre-line', lineHeight: 1.6 }}>
                  {'\n'}{lesson.assignment_prompt}{'\n'}
                </p>
                {lesson.assignment_rubric && (
                  <div className="p-2 rounded-2 mt-2" style={{ background: '#ffffff', border: '1px dashed #d4af37', fontSize: '0.78rem', color: '#475569' }}>
                    <strong>Grading Rubric:</strong>
                    <div style={{ whiteSpace: 'pre-line' }}>{lesson.assignment_rubric}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Diagnostic Quiz Box */}
            <div className="col-lg-6">
              <div className="p-3 rounded-3 h-100" style={{ background: '#f8fafc', border: '1.5px solid #d4af37' }}>
                <div className="d-flex align-items-center justify-content-between mb-2">
                  <span className="fw-bold" style={{ color: '#064e3b' }}>
                    <i className="bi bi-patch-question-fill text-success me-1"></i> Diagnostic Assessment Quiz
                  </span>
                  <span className="badge bg-success-subtle text-success small">5 Questions</span>
                </div>

                {lesson.quiz_data.length > 0 ? (
                  <div className="accordion accordion-flush" id={`quizAcc${lesson.id}`}>
                    {lesson.quiz_data.map((q, i) => (
                      <div className="accordion-item bg-transparent border-0 mb-2" key={i}>
                        <div className="small fw-bold text-dark mb-1">
                          Q{i + 1}: {q.question}
                        </div>
                        <div className="ps-2 small text-muted" style={{ borderLeft: '2px solid #064e3b' }}>
                          {q.options.map((opt, j) => (
                            <div className={opt.is_correct_index ? 'text-success fw-bold' : ''} key={j}>
                              &bull; {opt.text} {opt.is_correct_index ? '✓' : ''}
                            </div>
                          ))}
                        </div>
                        {q.explanation && (
                          <div className="small text-muted mt-1 fst-italic ps-2" style={{ fontSize: '0.75rem' }}>
                            Why: {q.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="small text-muted mb-0">Diagnostic quizzes mapped to this lesson.</p>
                )}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

// Owner-requested: the admin sees the lesson video (the same Inara slide player students get)
// inside the lesson card. Loaded on demand so "Expand All" doesn't start a player per day.
function LessonVideoPreview({ lessonId, dayNumber }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-4">
      <h6 className="fw-bold text-success mb-2"><i className="bi bi-play-btn-fill text-warning me-1"></i> Day {dayNumber} Lesson Video</h6>
      {open ? (
        <div className="rounded-3 overflow-hidden shadow-sm" style={{ border: '2px solid #d4af37', background: '#ffffff' }}>
          <iframe
            src={`/daily-lesson/${lessonId}/?embed=1`}
            title={`Day ${dayNumber} lesson video`}
            style={{ width: '100%', height: '780px', border: 0, display: 'block' }}
            allow="autoplay; fullscreen"
            allowFullScreen
          />
        </div>
      ) : (
        <button
          type="button"
          className="w-100 d-flex flex-column align-items-center justify-content-center gap-2 rounded-3 shadow-sm"
          style={{ minHeight: '180px', border: '2px dashed #d4af37', background: '#064e3b', color: '#d4af37', cursor: 'pointer' }}
          onClick={() => setOpen(true)}
        >
          <i className="bi bi-play-circle-fill" style={{ fontSize: '3rem' }}></i>
          <span className="fw-bold">Play Lesson Video</span>
          <span className="small text-white-50">Same slide player &amp; narration the student sees</span>
        </button>
      )}
    </div>
  );
}

function DailyLessonCard({ dLesson, uploading, onUpload }) {
  const id = dLesson.id;
  return (
    <div className="card p-3 p-md-4 mb-3 shadow-sm daily-lesson-card" style={{ border: '1.8px solid #d4af37', borderRadius: '16px', background: '#fafaf9' }}>
      {/* Lesson Header Bar (Main Topic Always Visible) */}
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div className="d-flex align-items-center gap-3">
          <button className="btn p-0 text-start border-0 bg-transparent daily-topic-btn daily-lesson-trigger collapsed" type="button" data-bs-toggle="collapse" data-bs-target={`#dailyCollapse${id}`} aria-expanded="false" style={{ cursor: 'pointer' }}>
            <div className="d-flex align-items-center gap-2">
              <span className="badge" style={{ background: '#064e3b', color: '#d4af37', border: '1px solid #d4af37', fontWeight: 800, fontSize: '0.8rem', borderRadius: '20px', padding: '5px 12px' }}>
                DAY {dLesson.day_number}
              </span>
              <i className="bi bi-chevron-down text-muted fs-6 daily-chevron"></i>
            </div>
            <h5 className="fw-bold mt-1 mb-0 text-success" style={{ fontSize: '1.1rem' }}>{dLesson.title}</h5>
            <span className="small text-muted">
              <i className="bi bi-diagram-2 me-1"></i>Module: <strong>{dLesson.module_title}</strong>
            </span>
          </button>
        </div>
        <div className="d-flex align-items-center gap-2 flex-wrap">
          {dLesson.ppt_file && (
            <span className="badge bg-success-subtle text-success border border-success px-3 py-2 rounded-pill"><i className="bi bi-file-earmark-check-fill me-1"></i> Custom PPT Loaded</span>
          )}
          <a href={`/lesson/${id}/download-ppt/`} className="btn btn-sm btn-nav-outline" title="Download Presentation"><i className="bi bi-file-earmark-ppt"></i> PPT</a>
          <button type="button" className="btn btn-sm btn-outline-warning rounded-pill fw-semibold text-dark" data-bs-toggle="modal" data-bs-target={`#uploadPptModal${id}`} title="Upload Custom PPT & Generate Audio">
            <i className="bi bi-cloud-arrow-up-fill text-warning me-1"></i>Upload PPT
          </button>
          <button className="btn btn-sm btn-outline-success rounded-pill fw-semibold daily-lesson-trigger collapsed" type="button" data-bs-toggle="collapse" data-bs-target={`#dailyCollapse${id}`} aria-expanded="false">
            <i className="bi bi-eye me-1"></i> <span className="d-none d-md-inline">View Content</span>
          </button>
        </div>
      </div>

      {/* Collapsed Content Details (PPT Deck, Syllabus, Assignment, Quiz) */}
      <div id={`dailyCollapse${id}`} className="collapse daily-lesson-collapse pt-4 mt-3 border-top" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.25)' })}>

        <LessonVideoPreview lessonId={id} dayNumber={dLesson.day_number} />

        {/* PPT Presentation & Audio Hub (Admin Mode) */}
        <div className="row g-4 mb-4">
          <div className="col-lg-6">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <h6 className="fw-bold text-success mb-0"><i className="bi bi-file-earmark-slides me-1"></i> Day {dLesson.day_number} Presentation Lecture &amp; Audio Hub</h6>
              <button type="button" className="btn btn-sm btn-outline-warning text-dark fw-bold rounded-pill px-2 py-0" style={{ fontSize: '0.78rem' }} data-bs-toggle="modal" data-bs-target={`#uploadPptModal${id}`}>
                <i className="bi bi-upload me-1 text-warning"></i> Upload PPT
              </button>
            </div>
            <div className="p-3 rounded-3 shadow-sm bg-white" style={{ border: '2px solid #d4af37' }}>
              <div className="d-flex align-items-center justify-content-between mb-2 border-bottom pb-2">
                <div>
                  <span className="badge" style={{ background: '#064e3b', color: '#d4af37', fontSize: '0.75rem' }}>
                    <i className="bi bi-mortarboard-fill me-1"></i> Lecture Deck
                  </span>
                  {dLesson.ppt_file ? (
                    <span className="badge bg-success text-white ms-1"><i className="bi bi-check2 me-1"></i>Teacher PPT Active</span>
                  ) : (
                    <span className="badge bg-info-subtle text-info border border-info ms-1"><i className="bi bi-stars me-1"></i>AI Generated Deck</span>
                  )}
                </div>
                <div className="d-flex align-items-center gap-2">
                  <Link to={`/daily-lesson/${id}/`} target="_blank" className="btn btn-sm btn-golden fw-bold" style={{ fontSize: '0.78rem' }}>
                    <i className="bi bi-play-circle-fill me-1"></i> Preview Masterclass Screen
                  </Link>
                  <a href={`/lesson/${id}/download-ppt/`} className="btn btn-sm btn-nav-outline fw-bold" style={{ fontSize: '0.78rem' }}>
                    <i className="bi bi-download me-1"></i> Download .pptx
                  </a>
                </div>
              </div>

              <p className="small text-muted mb-2">
                Features synchronized PPT slides with automated <strong>Slide Explanations (with practical examples)</strong> and <strong>Audio Explanations (gTTS)</strong>.
              </p>

              <div className="p-2 rounded bg-light border small mb-2 d-flex justify-content-between align-items-center">
                <span><i className="bi bi-volume-up-fill text-success me-1"></i>Audio Voice Engine: <strong>gTTS Synthesized</strong></span>
                <span className="badge bg-dark text-warning">Per-Slide MP3</span>
              </div>

              <div className="d-flex gap-2 mt-2">
                <button type="button" className="btn btn-sm btn-outline-success w-100 fw-semibold" data-bs-toggle="modal" data-bs-target={`#uploadPptModal${id}`}>
                  <i className="bi bi-cloud-arrow-up-fill me-1"></i> Upload / Replace Lesson PPT (.pptx)
                </button>
              </div>
            </div>
          </div>

          {/* Lesson Overview & Syllabus Text */}
          <div className="col-lg-6">
            <h6 className="fw-bold text-success mb-2"><i className="bi bi-book me-1"></i> Day {dLesson.day_number} Core Syllabus</h6>
            <div className="p-3 rounded-3" style={{ background: '#ffffff', border: '1.5px solid rgba(212, 175, 55, 0.35)', maxHeight: '320px', overflowY: 'auto', fontSize: '0.88rem', lineHeight: 1.6 }} dangerouslySetInnerHTML={{ __html: dLesson.content_html }} />
          </div>
        </div>

        {/* Daily Tasks: Assignment & Quiz */}
        <div className="row g-3">
          {/* Assignment */}
          <div className="col-md-6">
            <div className="p-3 rounded-3 h-100" style={{ background: '#fdfbf7', border: '1.5px solid #d4af37' }}>
              <h6 className="fw-bold text-warning-emphasis mb-2">
                <i className="bi bi-pencil-square text-warning me-1"></i> Day {dLesson.day_number} Assignment Challenge
              </h6>
              <p className="small mb-0 text-dark" style={{ whiteSpace: 'pre-line', lineHeight: 1.6 }}>
                {'\n'}{dLesson.assignment_question}{'\n'}
              </p>
            </div>
          </div>

          {/* Quiz */}
          <div className="col-md-6">
            <div className="p-3 rounded-3 h-100" style={{ background: '#ffffff', border: '1.5px solid #064e3b' }}>
              <h6 className="fw-bold text-success mb-2">
                <i className="bi bi-patch-question text-success me-1"></i> Day {dLesson.day_number} Diagnostic Assessment (5 Questions)
              </h6>
              {dLesson.quiz_data.length > 0 ? (
                <div className="accordion accordion-flush" id={`quizAccAdmin_${id}`}>
                  {dLesson.quiz_data.map((q, i) => {
                    const n = i + 1;
                    return (
                      <div className="accordion-item bg-transparent" key={n}>
                        <h2 className="accordion-header" id={`heading_admin_q_${id}_${n}`}>
                          <button className="accordion-button collapsed py-2 px-0 bg-transparent text-dark small fw-bold" type="button" data-bs-toggle="collapse" data-bs-target={`#collapse_admin_q_${id}_${n}`}>
                            Q{n}: {q.question_short}
                          </button>
                        </h2>
                        <div id={`collapse_admin_q_${id}_${n}`} className="accordion-collapse collapse" data-bs-parent={`#quizAccAdmin_${id}`}>
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
              ) : (
                <p className="small text-muted mb-0">No quiz data loaded for this lesson.</p>
              )}
            </div>
          </div>
        </div>
        {/* End Daily Tasks row */}
      </div>
      {/* End Collapsed Content Details */}

      {/* Modal: Upload PPT Presentation for Day N */}
      <div className="modal fade" id={`uploadPptModal${id}`} tabIndex="-1" aria-labelledby={`uploadPptLabel${id}`} aria-hidden="true">
        <div className="modal-dialog modal-dialog-centered">
          <div className="modal-content border-0 shadow-lg rounded-4" ref={important({ border: '2px solid #d4af37' })}>
            <form method="POST" encType="multipart/form-data" onSubmit={(e) => onUpload(e, id)}>
              <div className="modal-header border-bottom py-3" style={{ background: 'linear-gradient(135deg, #064e3b, #106e53)', color: '#ffffff' }}>
                <h5 className="modal-title fw-bold" id={`uploadPptLabel${id}`}>
                  <i className="bi bi-file-earmark-slides-fill text-warning me-2"></i>Upload PPT &amp; Generate Audio
                </h5>
                <button type="button" className="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div className="modal-body p-4 bg-light">
                <div className="mb-3 text-center">
                  <div className="rounded-circle d-inline-flex align-items-center justify-content-center mb-2 shadow-sm" style={{ width: '58px', height: '58px', background: '#fef9e7', border: '2px solid #d4af37', color: '#064e3b' }}>
                    <i className="bi bi-cloud-arrow-up-fill fs-3"></i>
                  </div>
                  <h6 className="fw-bold text-dark mb-1">Day {dLesson.day_number}: {dLesson.title}</h6>
                  <p className="text-muted small mb-0">Upload a PowerPoint (<code>.pptx</code>) file for this lesson.</p>
                </div>

                <div className="p-3 bg-white rounded-3 border mb-3">
                  <label className="form-label fw-bold small text-success mb-2"><i className="bi bi-gear-wide-connected me-1"></i>Automated 5-Step Pipeline:</label>
                  <ul className="small text-muted mb-0 ps-3" style={{ lineHeight: 1.6 }}>
                    <li><strong>Step 1:</strong> python-pptx extracts titles, bullets &amp; text from all slides.</li>
                    <li><strong>Step 2:</strong> AI generates simple concept breakdowns + real-world practical examples.</li>
                    <li><strong>Step 3:</strong> gTTS synthesizes per-slide voice audio (MP3) files on server.</li>
                    <li><strong>Step 4:</strong> Saves to PresentationSlide database models.</li>
                    <li><strong>Step 5:</strong> Student gets instant &quot;Slide Explanation&quot; &amp; &quot;Audio Explanation&quot; buttons!</li>
                  </ul>
                </div>

                <div className="mb-2">
                  <label htmlFor={`pptFileInput${id}`} className="form-label fw-bold text-dark small">Select PowerPoint Presentation (.pptx):</label>
                  <input type="file" className="form-control rounded-pill" id={`pptFileInput${id}`} name="ppt_file" accept=".pptx" required />
                </div>
              </div>
              <div className="modal-footer border-top bg-white">
                <button type="button" className="btn btn-sm btn-outline-secondary rounded-pill px-3" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" disabled={uploading} className="btn btn-sm rounded-pill px-4 fw-bold shadow-sm" style={{ background: '#D4AF37', color: '#064E3B', border: '1px solid #c49f27' }}>
                  {uploading ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Extracting PPT &amp; Synthesizing Audio...</>
                  ) : (
                    <><i className="bi bi-upload me-1"></i> Upload &amp; Process PPT</>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

    </div>
  );
}

export default function LevelCourseViewPage() {
  usePageAssets({ links: [ICONS_1113, FONT], css });
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const { addMessages } = useFlash();
  // `?regenerate=1` used to regenerate on a plain GET; route it through the confirming regenerate page.
  const wantsRegenerate = searchParams.get('regenerate') === '1';
  const { data, ready, reload, notFound } = usePageData(wantsRegenerate ? null : `/admin-courses/levels/${slug}/`);
  // Leaving the page with an upload modal open must not leave Bootstrap's backdrop/scroll lock behind.
  useEffect(() => () => cleanupModals([...document.querySelectorAll('.modal.show')]), []);
  const [curriculumExpanded, setCurriculumExpanded] = useState(false);
  const [dailyExpanded, setDailyExpanded] = useState(false);
  const [uploadingId, setUploadingId] = useState(null);
  // Bumped after a PPT upload so the page comes back fresh, like the old redirect + full page load.
  const [version, setVersion] = useState(0);

  const toggleAllCurriculumLessons = () => {
    const next = toggleAll('curriculumPane', '.lesson-card-item .collapse', '.lesson-btn-trigger');
    if (next !== null) setCurriculumExpanded(next);
  };
  const toggleAllDailyLessons = () => {
    const next = toggleAll('dailyPane', '.daily-lesson-collapse', '.daily-lesson-trigger');
    if (next !== null) setDailyExpanded(next);
  };

  const onRegenerateClick = (e) => {
    if (!window.confirm(REGEN_CONFIRM)) e.preventDefault();
  };

  const onUpload = async (e, lessonId) => {
    e.preventDefault();
    setUploadingId(lessonId);
    let res;
    try {
      res = await apiFetch(`/admin-courses/lessons/${lessonId}/upload-ppt/`, { method: 'POST', body: new FormData(e.currentTarget) });
    } catch (err) {
      res = err.data || null;
    }
    if (res?.messages) addMessages(res.messages);

    // Close the modal first (so Bootstrap removes its backdrop), then reload the page fresh.
    const finish = async () => {
      await reload();
      setUploadingId(null);
      setCurriculumExpanded(false);
      setDailyExpanded(false);
      setVersion((v) => v + 1);
    };
    const modalEl = document.getElementById(`uploadPptModal${lessonId}`);
    const modal = modalEl && window.bootstrap?.Modal.getInstance(modalEl);
    if (modal && modalEl.classList.contains('show')) {
      modalEl.addEventListener('hidden.bs.modal', finish, { once: true });
      modal.hide();
    } else {
      finish();
    }
  };

  if (wantsRegenerate) return <Navigate to={`/admindashboard/level/${slug}/regenerate/`} replace />;
  if (notFound) return <NotFoundPage />;
  if (!ready) return <AdminLoader />;
  const {
    course_level: courseLevel, parent_course: parentCourse, modules, total_modules: totalModules,
    total_lessons: totalLessons, all_slides: allSlides, total_slides: totalSlides,
    daily_lessons: dailyLessons, daily_lessons_count: dailyLessonsCount, enrolled_count: enrolledCount,
  } = data;
  const regenerateUrl = `/admindashboard/level/${courseLevel.slug}/regenerate/`;
  const usersUrl = `/admindashboard/level/${courseLevel.slug}/users/`;

  return (
    <Fragment key={version}>
      <div className="container-fluid py-4">
        <div className="content-wrapper">

          {/* Top Navigation Bar */}
          <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
            <Link to="/courses_info/" className="btn-nav-outline">
              <i className="bi bi-arrow-left"></i> Back to Courses
            </Link>
            <div className="d-flex gap-2 flex-wrap">
              {/* Regenerate Deep AI Content Action */}
              <Link to={regenerateUrl} state={{ confirmed: true }} className="btn-regen-ai" onClick={onRegenerateClick}>
                <i className="bi bi-stars"></i> Regenerate Deep AI Curriculum
              </Link>
              <Link to={usersUrl} className="btn-nav-green">
                <i className="bi bi-people-fill"></i> View Enrolled Students ({enrolledCount})
              </Link>
            </div>
          </div>

          {/* Master Course & University Benchmark Header */}
          <div className="master-header-card">
            <div className="row align-items-center g-4">
              <div className="col-lg-8">
                <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                  {courseLevel.level === 'Beginner' ? (
                    <span className="benchmark-badge-lg badge-harvard">
                      🏛️ Harvard CS50 Philosophy (Beginner)
                    </span>
                  ) : courseLevel.level === 'Intermediate' ? (
                    <span className="benchmark-badge-lg badge-mit">
                      🏛️ MIT Data Structures &amp; Logic (Intermediate)
                    </span>
                  ) : (
                    <span className="benchmark-badge-lg badge-stanford">
                      🏛️ Stanford &amp; CMU Systems &amp; AI (Advanced)
                    </span>
                  )}
                  <span className="badge" style={{ background: '#064e3b', color: '#d4af37', border: '1.5px solid #d4af37', padding: '6px 14px', borderRadius: '20px', fontWeight: 700, fontSize: '0.8rem' }}>
                    Unrestricted Academic Scale
                  </span>
                  {courseLevel.level_code && (
                    <span className="badge bg-secondary-subtle text-secondary fw-bold" style={{ borderRadius: '10px', padding: '6px 12px', fontSize: '0.78rem' }}>
                      {courseLevel.level_code}
                    </span>
                  )}
                </div>

                <h2 className="fw-bold mb-2" style={{ color: '#064e3b' }}>
                  {courseLevel.title}
                </h2>
                <p className="text-muted mb-3" style={{ lineHeight: 1.6, fontSize: '0.95rem' }}>
                  {courseLevel.benchmark_description}
                </p>

                <div className="d-flex align-items-center gap-3 flex-wrap">
                  <span className="small fw-semibold text-muted">
                    Master Course: <strong>{parentCourse.title}</strong>
                  </span>
                  <span className="text-muted">&bull;</span>
                  <span className="small fw-semibold text-success">
                    <i className="bi bi-check-circle-fill me-1"></i> Pre-generated &amp; Fully Cached in DB
                  </span>
                </div>
              </div>

              <div className="col-lg-4 text-center">
                {parentCourse.image ? (
                  <img src={parentCourse.image} className="img-fluid rounded-3 shadow-sm" style={{ maxHeight: '160px', objectFit: 'cover', border: '2px solid #d4af37' }} alt={courseLevel.title} />
                ) : (
                  <div className="p-4 rounded-3 d-flex flex-column align-items-center justify-content-center" style={{ background: 'linear-gradient(135deg, #064e3b, #047857)', height: '150px', border: '2px solid #d4af37' }}>
                    <i className="bi bi-mortarboard display-5" style={{ color: '#d4af37' }}></i>
                    <span className="text-white small fw-bold mt-2">{courseLevel.level} Master Tier</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Academic Scale KPI Row */}
          <div className="row g-3 mb-4">
            <div className="col-sm-6 col-lg-3">
              <div className="kpi-stat-card">
                <div className="kpi-icon-box">
                  <i className="bi bi-folder-fill"></i>
                </div>
                <div>
                  <div className="text-muted small fw-bold">Academic Modules</div>
                  <h4 className="fw-bold mb-0" style={{ color: '#064e3b' }}>{totalModules} Modules</h4>
                </div>
              </div>
            </div>

            <div className="col-sm-6 col-lg-3">
              <div className="kpi-stat-card">
                <div className="kpi-icon-box">
                  <i className="bi bi-journal-code"></i>
                </div>
                <div>
                  <div className="text-muted small fw-bold">Comprehensive Lessons</div>
                  <h4 className="fw-bold mb-0" style={{ color: '#064e3b' }}>{totalLessons} Deep Lessons</h4>
                </div>
              </div>
            </div>

            <div className="col-sm-6 col-lg-3">
              <div className="kpi-stat-card">
                <div className="kpi-icon-box">
                  <i className="bi bi-file-earmark-slides-fill"></i>
                </div>
                <div>
                  <div className="text-muted small fw-bold">Lecture Presentation Deck</div>
                  <h4 className="fw-bold mb-0" style={{ color: '#064e3b' }}>{totalSlides} Slides</h4>
                </div>
              </div>
            </div>

            <div className="col-sm-6 col-lg-3">
              <div className="kpi-stat-card">
                <div className="kpi-icon-box">
                  <i className="bi bi-people-fill"></i>
                </div>
                <div>
                  <div className="text-muted small fw-bold">Enrolled Students</div>
                  <h4 className="fw-bold mb-0" style={{ color: '#064e3b' }}>{enrolledCount} Students</h4>
                </div>
              </div>
            </div>
          </div>

          {/* Academic Hierarchy Tabs */}
          <ul className="nav nav-tabs nav-tabs-academic mb-4" id="academicTabs" role="tablist">
            <li className="nav-item" role="presentation">
              <button className="nav-link active" id="curriculum-tab" data-bs-toggle="tab" data-bs-target="#curriculumPane" type="button" role="tab">
                <i className="bi bi-layers-half me-1 text-warning"></i> 1. Modular Curriculum &amp; Deep Lessons ({totalModules} Modules &bull; {totalLessons} Lessons)
              </button>
            </li>
            <li className="nav-item" role="presentation">
              <button className="nav-link" id="daily-tab" data-bs-toggle="tab" data-bs-target="#dailyPane" type="button" role="tab">
                <i className="bi bi-play-btn-fill me-1 text-warning"></i> 2. Daily Lessons, Video Player &amp; Assessments ({dailyLessonsCount} Days)
              </button>
            </li>
            <li className="nav-item" role="presentation">
              <button className="nav-link" id="slides-tab" data-bs-toggle="tab" data-bs-target="#slidesPane" type="button" role="tab">
                <i className="bi bi-file-earmark-slides-fill me-1 text-warning"></i> 3. University Lecture Deck ({totalSlides} Slides Outline)
              </button>
            </li>
            <li className="nav-item" role="presentation">
              <button className="nav-link" id="audit-tab" data-bs-toggle="tab" data-bs-target="#auditPane" type="button" role="tab">
                <i className="bi bi-shield-check me-1 text-warning"></i> 4. Pedagogical Audit &amp; Student Sync
              </button>
            </li>
          </ul>

          {/* Tab Content */}
          <div className="tab-content" id="academicTabContent">

            {/* TAB 1: MODULAR CURRICULUM & DEEP LESSONS */}
            <div className="tab-pane fade show active" id="curriculumPane" role="tabpanel">
              {/* Tab 1 Controls Toolbar */}
              <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3 pb-2 border-bottom" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.3)' })}>
                <div className="small text-muted">
                  <i className="bi bi-info-circle me-1 text-success"></i> Topics are collapsed by default. Click any topic headline to expand full reading, code blueprints, and lab tasks.
                </div>
                <div>
                  <button type="button" className="btn btn-sm btn-outline-success rounded-pill fw-semibold shadow-sm" id="btnToggleAllCurriculum" onClick={toggleAllCurriculumLessons}>
                    <i className={curriculumExpanded ? 'bi bi-arrows-collapse me-1' : 'bi bi-arrows-expand me-1'} id="iconToggleAllCurriculum"></i> <span id="textToggleAllCurriculum">{curriculumExpanded ? 'Collapse All Topics' : 'Expand All Topics'}</span>
                  </button>
                </div>
              </div>

              {modules.map((module) => (
                <div className="module-block" key={module.id}>
                  {/* Module Header */}
                  <div className="module-header d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <div>
                      <span className="badge" style={{ background: '#064e3b', color: '#d4af37', border: '1px solid #d4af37', fontSize: '0.75rem', fontWeight: 800, borderRadius: '8px' }}>
                        MODULE {module.order}
                      </span>
                      <h4 className="fw-bold mt-2 mb-1" style={{ color: '#064e3b' }}>{module.title}</h4>
                      <p className="text-muted small mb-0">{module.description}</p>
                    </div>
                    <div className="d-flex align-items-center gap-2">
                      <span className="badge bg-light text-dark border fw-bold">
                        <i className="bi bi-clock me-1 text-warning"></i> ~{module.estimated_hours} Hours
                      </span>
                      <span className="badge bg-success-subtle text-success fw-bold">
                        {module.lessons_count} Deep Lessons
                      </span>
                    </div>
                  </div>

                  {/* Lessons Inside This Module */}
                  <div className="p-3 p-md-4">
                    {module.lessons.map((lesson) => <CurriculumLesson lesson={lesson} key={lesson.id} />)}
                    {module.lessons.length === 0 && (
                      <div className="text-center py-3 text-muted small">No lessons in this module yet.</div>
                    )}
                  </div>
                </div>
              ))}
              {modules.length === 0 && (
                <div className="card p-5 text-center shadow-sm" style={{ border: '2px dashed #d4af37', borderRadius: '16px' }}>
                  <i className="bi bi-layers text-warning display-4 mb-3"></i>
                  <h4 className="fw-bold" style={{ color: '#064e3b' }}>Curriculum Awaiting Deep Generation</h4>
                  <p className="text-muted mb-3">Click the button below to dynamically synthesize the exhaustive multi-module curriculum with Gemini AI.</p>
                  <Link to={regenerateUrl} className="btn-regen-ai d-inline-block">
                    <i className="bi bi-stars"></i> Generate Deep University Curriculum
                  </Link>
                </div>
              )}
            </div>

            {/* TAB 2: DAILY LESSONS, VIDEO PLAYERS & ASSESSMENTS (ADMIN MODE) */}
            <div className="tab-pane fade" id="dailyPane" role="tabpanel">
              <div className="card p-4 shadow-sm mb-4" style={{ border: '2px solid #d4af37', borderRadius: '16px', background: '#ffffff' }}>
                <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4 border-bottom pb-3">
                  <div>
                    <h4 className="fw-bold mb-1" style={{ color: '#064e3b' }}>
                      <i className="bi bi-play-btn-fill text-warning me-2"></i>Daily Lessons, Video Lectures &amp; Diagnostic Assessments
                    </h4>
                    <p className="text-muted small mb-0">
                      Pre-generated canonical university syllabus. Content details are collapsed by default—click any lesson topic to view video preview, full syllabus, assignment, and quiz.
                    </p>
                  </div>
                  <div className="d-flex align-items-center gap-2 flex-wrap">
                    <button type="button" className="btn btn-sm btn-outline-success rounded-pill fw-semibold shadow-sm" id="btnToggleAllDaily" onClick={toggleAllDailyLessons}>
                      <i className={dailyExpanded ? 'bi bi-arrows-collapse me-1' : 'bi bi-arrows-expand me-1'} id="iconToggleAllDaily"></i> <span id="textToggleAllDaily">{dailyExpanded ? 'Collapse All Daily Topics' : 'Expand All Daily Topics'}</span>
                    </button>
                  </div>
                </div>

                {dailyLessons.map((dLesson) => (
                  <DailyLessonCard dLesson={dLesson} uploading={uploadingId === dLesson.id} onUpload={onUpload} key={dLesson.id} />
                ))}
                {dailyLessons.length === 0 && (
                  <div className="text-center py-4 text-muted">
                    No canonical daily lessons initialized. Click &quot;Regenerate Deep AI Curriculum&quot; to synthesize the daily syllabus.
                  </div>
                )}
              </div>
            </div>

            {/* TAB 3: COMPREHENSIVE LECTURE PRESENTATION DECK (15-30+ SLIDES) */}
            <div className="tab-pane fade" id="slidesPane" role="tabpanel">
              <div className="card p-4 shadow-sm mb-4" style={{ border: '2px solid #d4af37', borderRadius: '16px', background: '#ffffff' }}>
                <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4 border-bottom pb-3">
                  <div>
                    <h4 className="fw-bold mb-1" style={{ color: '#064e3b' }}>
                      <i className="bi bi-file-earmark-slides-fill text-warning me-2"></i>Comprehensive Lecture Presentation Deck
                    </h4>
                    <p className="text-muted small mb-0">
                      Exhaustive {totalSlides}-slide university lecture deck outline with detailed speaker lecture notes, code walkthroughs, and ASCII architecture diagrams.
                    </p>
                  </div>
                  <span className="badge" style={{ background: '#064e3b', color: '#d4af37', border: '1.5px solid #d4af37', fontSize: '0.85rem', padding: '7px 16px', borderRadius: '20px' }}>
                    {totalSlides} Professional Slides
                  </span>
                </div>

                {/* Slide Grid (15 to 30+ Slides) */}
                <div className="row g-4">
                  {allSlides.map((slide) => (
                    <div className="col-12 col-lg-6" key={slide.id}>
                      <div className="slide-grid-card">
                        <div>
                          {/* Slide Top Badge & Category */}
                          <div className="d-flex align-items-center justify-content-between mb-3">
                            <div className="d-flex align-items-center gap-2">
                              <span className="slide-num-pill">SLIDE {slide.slide_number}</span>
                              <span className="badge bg-secondary-subtle text-secondary small fw-bold">
                                {slide.slide_category}
                              </span>
                            </div>
                            <span className="small text-muted fw-semibold">
                              Slide {slide.slide_number} of {totalSlides}
                            </span>
                          </div>

                          {/* Slide Title */}
                          <h5 className="fw-bold mb-3" style={{ color: '#064e3b', fontSize: '1.1rem', lineHeight: 1.4 }}>
                            {slide.title}
                          </h5>

                          {/* Slide Bullet Points */}
                          <div className="mb-3">
                            <div className="small fw-bold text-uppercase text-muted mb-1" style={{ fontSize: '0.72rem', letterSpacing: '0.5px' }}>
                              Lecture Slide Content:
                            </div>
                            <ul className="mb-0 ps-3 small text-dark" style={{ lineHeight: 1.7 }}>
                              {slide.bullet_points.map((pt, i) => (
                                <li key={i}>{pt}</li>
                              ))}
                            </ul>
                          </div>

                          {/* Speaker Notes / Professor Speech Script */}
                          {slide.speaker_notes && (
                            <div className="mb-3">
                              <div className="small fw-bold text-uppercase text-muted mb-1" style={{ fontSize: '0.72rem', letterSpacing: '0.5px' }}>
                                <i className="bi bi-mic-fill text-warning me-1"></i> Professor Speaker Notes:
                              </div>
                              <div className="speaker-notes-box">
                                {slide.speaker_notes}
                              </div>
                            </div>
                          )}

                          {/* Code Snippet if present */}
                          {slide.code_snippet && (
                            <div className="mb-3">
                              <div className="small fw-bold text-uppercase text-muted mb-1" style={{ fontSize: '0.72rem', letterSpacing: '0.5px' }}>
                                <i className="bi bi-code-square text-info me-1"></i> Slide Code Blueprint:
                              </div>
                              <div className="code-preview-box">
                                <pre className="mb-0">{slide.code_snippet}</pre>
                              </div>
                            </div>
                          )}

                          {/* Visual / Diagram Placeholder */}
                          {slide.diagram_or_visual && (
                            <div className="mb-2">
                              <div className="small fw-bold text-uppercase text-muted mb-1" style={{ fontSize: '0.72rem', letterSpacing: '0.5px' }}>
                                <i className="bi bi-diagram-3 text-success me-1"></i> Architecture / Mental Model:
                              </div>
                              <div className="visual-preview-box">
                                {/* white-space: pre -> keep the template's surrounding newline + indentation */}
                                {VISUAL_LEAD}{slide.diagram_or_visual}{VISUAL_TRAIL}
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="pt-2 border-top mt-3 text-end" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.2)' })}>
                          <span className="small text-muted" style={{ fontSize: '0.75rem' }}>
                            Academic Standard: {courseLevel.benchmark}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                  {allSlides.length === 0 && (
                    <div className="col-12 text-center py-4 text-muted">
                      No presentation slides generated yet. Click &quot;Regenerate Deep AI Curriculum&quot; to synthesize the 20+ slide deck.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* TAB 3: PEDAGOGICAL AUDIT & STUDENT SYNC */}
            <div className="tab-pane fade" id="auditPane" role="tabpanel">
              <div className="card p-4 shadow-sm mb-4" style={{ border: '2px solid #d4af37', borderRadius: '16px', background: '#ffffff' }}>
                <h4 className="fw-bold mb-3" style={{ color: '#064e3b' }}>
                  <i className="bi bi-shield-check text-success me-2"></i>Pedagogical Compliance &amp; Student Synchronization
                </h4>

                <div className="row g-4">
                  <div className="col-md-6">
                    <div className="p-3 rounded-3 h-100" style={{ background: '#f8fafc', border: '1.5px solid #d4af37' }}>
                      <h6 className="fw-bold text-success mb-2">Curriculum Specification Overview</h6>
                      <table className="table table-sm mb-0">
                        <tbody>
                          <tr>
                            <td className="text-muted fw-bold">Master Domain:</td>
                            <td className="text-dark">{parentCourse.title}</td>
                          </tr>
                          <tr>
                            <td className="text-muted fw-bold">Academic Tier:</td>
                            <td className="text-dark">{courseLevel.level} Level</td>
                          </tr>
                          <tr>
                            <td className="text-muted fw-bold">Mapped Benchmark:</td>
                            <td className="text-dark">{courseLevel.benchmark}</td>
                          </tr>
                          <tr>
                            <td className="text-muted fw-bold">Total Modules:</td>
                            <td className="text-dark">{totalModules} Active Modules</td>
                          </tr>
                          <tr>
                            <td className="text-muted fw-bold">Total Lessons:</td>
                            <td className="text-dark">{totalLessons} Deep Lessons</td>
                          </tr>
                          <tr>
                            <td className="text-muted fw-bold">Slide Deck Count:</td>
                            <td className="text-dark">{totalSlides} Presentation Slides</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="col-md-6">
                    <div className="p-3 rounded-3 h-100" style={{ background: '#f8fafc', border: '1.5px solid #d4af37' }}>
                      <h6 className="fw-bold text-success mb-2">Instant Student Retrieval Cache</h6>
                      <p className="small text-muted" style={{ lineHeight: 1.6 }}>
                        When students select this university tier on the student dashboard, all pre-generated lessons,
                        textbook material, and diagnostic assessments are retrieved directly from the database in &lt;15ms.
                        Zero AI generation latency or background queue waiting.
                      </p>
                      <div className="d-flex align-items-center gap-2 mt-3">
                        <span className="badge bg-success text-white px-3 py-2 rounded-pill">
                          <i className="bi bi-check-circle-fill me-1"></i> Pre-Cached &amp; Verified
                        </span>
                        <Link to={usersUrl} className="btn btn-sm btn-outline-secondary">
                          Inspect Cohort Telemetry
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>

        </div>
      </div>
    </Fragment>
  );
}
