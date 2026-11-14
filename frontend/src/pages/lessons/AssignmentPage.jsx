import AdminLoader from '../../layouts/AdminLoader';
import { useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { usePageData } from '../../hooks/usePageData';
import { usePageAssets } from '../../hooks/usePageAssets';
import { useFlash } from '../../hooks/useFlash';
import { apiFetch, ApiError } from '../../api/client';
import { djDate } from '../../utils/djangoFormat';
import { useNotificationOverlays, useResultPanelReset } from './useLessonOverlays';
import css from './AssignmentPage.css?raw';

/* Port of `student_dashboard/course_data/assignment.html` (rendered inside StudentLayout). */

const DT = 'd M Y, h:i A';
// Django's `|default` treats 0 / '' / None as empty
const dj = (value, fallback) => (value === null || value === undefined || value === '' || value === 0 || value === false ? fallback : value);

/*
 * Owner-approved fix: the hidden telemetry inputs were never filled. Track paste events,
 * pasted characters, keystrokes and typing time (from the first keystroke) on the textarea.
 */
function useSubmissionTelemetry() {
  const stats = useRef({ pasteCount: 0, pastedChars: 0, keystrokes: 0, firstKeyAt: null });

  const onPaste = (e) => {
    const text = (e.clipboardData || window.clipboardData)?.getData('text') || '';
    stats.current.pasteCount += 1;
    stats.current.pastedChars += text.length;
  };
  const onKeyDown = () => {
    const s = stats.current;
    s.keystrokes += 1;
    if (s.firstKeyAt === null) s.firstKeyAt = Date.now();
  };
  const values = () => {
    const s = stats.current;
    return {
      paste_count: s.pasteCount,
      pasted_chars_total: s.pastedChars,
      typing_duration_seconds: s.firstKeyAt === null ? 0 : Math.round((Date.now() - s.firstKeyAt) / 1000),
      keystroke_count: s.keystrokes,
    };
  };
  const reset = () => {
    stats.current = { pasteCount: 0, pastedChars: 0, keystrokes: 0, firstKeyAt: null };
  };
  return { onPaste, onKeyDown, values, reset };
}

function AssignmentForm({ lessonId, expired, onSubmitted }) {
  const telemetry = useSubmissionTelemetry();
  const { addMessages } = useFlash();
  const busy = useRef(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy.current) return;
    const form = e.currentTarget;
    const values = telemetry.values();
    Object.entries(values).forEach(([name, value]) => {
      if (form.elements[name]) form.elements[name].value = String(value);
    });
    const body = new FormData(form);
    busy.current = true;
    try {
      const res = await apiFetch('/lessons/assignment/', { method: 'POST', body, query: { lesson_id: lessonId } });
      addMessages(res.messages);
    } catch (err) {
      if (err instanceof ApiError && err.data?.messages) addMessages(err.data.messages);
      else throw err;
    } finally {
      busy.current = false;
    }
    // The view redirected to itself (?lesson_id=...): a fresh, empty form + reloaded page data.
    form.reset();
    telemetry.reset();
    onSubmitted();
  };

  const telemetryInputs = (
    <>
      {/* Telemetry inputs for copy/paste & typing pattern detection */}
      <input type="hidden" name="paste_count" className="telemetry_paste_count" defaultValue="0" />
      <input type="hidden" name="pasted_chars_total" className="telemetry_pasted_chars" defaultValue="0" />
      <input type="hidden" name="typing_duration_seconds" className="telemetry_typing_duration" defaultValue="0" />
      <input type="hidden" name="keystroke_count" className="telemetry_keystroke_count" defaultValue="0" />
    </>
  );

  const action = `/assignment/?lesson_id=${lessonId}`;

  if (expired) {
    return (
      <form method="POST" encType="multipart/form-data" action={action} className="mt-2" onSubmit={handleSubmit}>
        {telemetryInputs}
        <div className="mb-2">
          <label className="form-label fw-bold small alvix-text-dark-green">Notes / Written Response</label>
          <textarea name="student_submission" className="form-control form-control-sm" rows="2" placeholder="Write key logic explanation..." onPaste={telemetry.onPaste} onKeyDown={telemetry.onKeyDown}></textarea>
        </div>
        <div className="mb-2">
          <label className="form-label fw-bold small alvix-text-dark-green">Upload File (PDF / Image / Code)</label>
          <input type="file" name="file_submission" className="form-control form-control-sm" />
        </div>
        <button type="submit" className="btn alvix-btn-gold w-100 py-2">
          <i className="bi bi-cloud-arrow-up me-2"></i> Submit Assignment
        </button>
      </form>
    );
  }

  return (
    <form method="POST" encType="multipart/form-data" action={action} onSubmit={handleSubmit}>
      {telemetryInputs}
      <div className="mb-2">
        <label className="form-label fw-bold small alvix-text-dark-green">Notes / Written Response (Optional)</label>
        <textarea name="student_submission" className="form-control form-control-sm" rows="2" placeholder="Write key logic explanation..." onPaste={telemetry.onPaste} onKeyDown={telemetry.onKeyDown}></textarea>
      </div>
      <div className="mb-3">
        <label className="form-label fw-bold small alvix-text-dark-green">Upload File (PDF / Image / Code)</label>
        <input type="file" name="file_submission" className="form-control form-control-sm" />
      </div>
      <button type="submit" className="btn alvix-btn-gold w-100 py-2">
        <i className="bi bi-cloud-arrow-up me-2"></i> Submit Assignment
      </button>
    </form>
  );
}

export default function AssignmentPage() {
  const [params] = useSearchParams();
  const lessonIdParam = params.get('lesson_id') || undefined;
  const { data, ready, reload } = usePageData('/lessons/assignment/', { lesson_id: lessonIdParam });
  usePageAssets({ css });
  const overlays = useNotificationOverlays();
  const panelExpired = useResultPanelReset(ready ? data : null, Boolean(data?.latest_submission));

  // Close any open popup when the page data changes (a Django redirect was a fresh page).
  const { reset } = overlays;
  useEffect(() => reset(), [data, reset]);

  if (!ready) return <AdminLoader />;

  const { lesson, latest_submission: latest, is_practical: isPractical } = data;
  const assignmentData = data.assignment_data || {};
  const display = data.assignment_display || {};
  const hasAssignmentData = Object.keys(assignmentData).length > 0;

  return (
    <>
      <div className="container-fluid px-0">

        {/* Header */}
        <div className="d-flex justify-content-between align-items-center mb-4 pb-2 border-bottom border-warning">
          <h3 className="fw-bold alvix-text-dark-green mb-0"><i className="bi bi-journal-code me-2" style={{ color: '#d4af37' }}></i>ALVIX AI Assignment Portal</h3>
          <Link to="/mycourse/" className="btn btn-outline-secondary btn-sm me-2"><i className="bi bi-arrow-left"></i> Back to Tracks</Link>
          <span className="badge alvix-header-gold p-2 fs-6">Lesson: {lesson.title}</span>
        </div>

        {/* TWO EQUAL-HEIGHT CARDS */}
        <div className="row g-4 mb-5 align-items-stretch">

          {/* CARD 1: Assignment Questions & Submission Status */}
          <div className="col-lg-6 d-flex">
            <div className="card shadow-sm alvix-gold-border w-100 flex-fill">
              <div className="card-header alvix-header-gold fw-bold d-flex justify-content-between align-items-center py-3">
                <span><i className="bi bi-file-earmark-text me-2"></i>Assignment Portal</span>
                <div className="d-flex align-items-center gap-2">
                  <small className="badge bg-light text-dark border"><i className="bi bi-calendar-check text-success me-1"></i>Issued: {djDate(lesson.assignment_issued_at, DT) || 'Active upon click'}</small>
                  <small className="badge bg-warning text-dark"><i className="bi bi-clock me-1"></i>Due: {djDate(data.deadline_date, DT)}</small>
                </div>
              </div>
              <div className="card-body alvix-bg-gold p-4 d-flex flex-column justify-content-between">

                {/* Pre-saved Assignment Questions: Always visible immediately */}
                <div className="p-3 bg-white rounded border alvix-gold-border mb-3" style={{ maxHeight: '250px', overflowY: 'auto' }}>
                  <h6 className="fw-bold alvix-text-dark-green mb-2"><i className="bi bi-journal-code text-warning me-1"></i> Assignment Challenge:</h6>
                  <div className="small text-muted" dangerouslySetInnerHTML={{ __html: data.assignment_prompt || '' }}></div>
                </div>

                {/* Structured Track Rubric & Requirements */}
                {hasAssignmentData && (
                  <div className="p-3 bg-light rounded border border-warning mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span className={`badge ${isPractical ? 'bg-success' : 'bg-primary'} text-uppercase`}>
                        <i className={`bi ${isPractical ? 'bi-code-slash' : 'bi-book'} me-1`}></i>
                        {isPractical ? 'Practical Task' : 'Theory Case Study'}
                      </span>
                      {assignmentData.expected_file_type ? (
                        <span className="badge bg-dark text-warning">
                          <i className="bi bi-file-earmark-code me-1"></i>Expected: {String(assignmentData.expected_file_type)}
                        </span>
                      ) : null}
                    </div>

                    {display.requirements_checklist?.length ? (
                      <>
                        <h6 className="small fw-bold text-dark mb-1"><i className="bi bi-check2-square text-success me-1"></i>Requirements Checklist:</h6>
                        <ul className="small text-muted mb-2 ps-3">
                          {display.requirements_checklist.map((req, i) => <li key={i}>{req}</li>)}
                        </ul>
                      </>
                    ) : display.expected_points?.length ? (
                      <>
                        <h6 className="small fw-bold text-dark mb-1"><i className="bi bi-list-check text-primary me-1"></i>Key Points to Address:</h6>
                        <ul className="small text-muted mb-2 ps-3">
                          {display.expected_points.map((pt, i) => <li key={i}>{pt}</li>)}
                        </ul>
                      </>
                    ) : null}

                    {display.rubric?.length ? (
                      <>
                        <h6 className="small fw-bold text-dark mb-1"><i className="bi bi-award text-warning me-1"></i>Marks Rubric (10 Marks Total):</h6>
                        <div className="row g-1 small text-muted">
                          {display.rubric.map(([criterion, pts], i) => (
                            <div className="col-6" key={i}>
                              <span className="badge bg-secondary-subtle text-dark border w-100 text-start text-truncate">
                                {criterion}: <strong>{pts} marks</strong>
                              </span>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : null}
                  </div>
                )}

                {latest ? (
                  <div className="alert alert-success border-0 shadow-sm text-center py-3 mb-0">
                    <i className="bi bi-check-circle-fill text-success fs-3 d-block mb-1"></i>
                    <h5 className="fw-bold alvix-text-dark-green mb-1">Assignment Submitted!</h5>
                    <p className="text-muted small mb-0">Submitted on {djDate(latest.submitted_at, DT)}</p>
                    <small className="text-muted d-block mt-1">Review feedback and marks in the evaluation panel on the right.</small>
                  </div>
                ) : data.is_expired ? (
                  <>
                    <div className="alert alert-warning mb-0 text-center fw-bold py-3">
                      <i className="bi bi-clock-history me-1 fs-5"></i>Standard Deadline Passed. Submission accepted for late review.
                    </div>
                    <AssignmentForm key={`expired-${lesson.id}`} lessonId={lesson.id} expired onSubmitted={reload} />
                  </>
                ) : (
                  <AssignmentForm key={`open-${lesson.id}`} lessonId={lesson.id} expired={false} onSubmitted={reload} />
                )}

              </div>
            </div>
          </div>

          {/* CARD 2: AI Evaluation & Remarks */}
          <div className="col-lg-6 d-flex">
            <div className="card shadow-sm alvix-gold-border w-100 flex-fill">
              <div className="card-header alvix-header-gold fw-bold d-flex justify-content-between align-items-center py-3">
                <span><i className="bi bi-cpu me-2"></i>AI Evaluation &amp; Logic Checker</span>
                <span id="aiScoreBadge">
                  {latest && !panelExpired ? (
                    // Owner-approved fix: show the real total (10), not "/ 5".
                    <span className="badge bg-warning text-dark fs-6">{dj(latest.score, 0)} / {dj(latest.total_marks, 10)} Marks</span>
                  ) : (
                    <span className="badge bg-secondary fs-6">Pending Review</span>
                  )}
                </span>
              </div>
              <div className="card-body alvix-bg-gold p-4 d-flex flex-column justify-content-between" id="aiCardBody">
                {latest ? (
                  <div id="aiEvaluationContent">
                    {panelExpired ? (
                      <div className="text-center py-5 text-muted my-auto">
                        <i className="bi bi-robot fs-1 d-block mb-2 text-warning"></i>
                        <p className="mb-0">Evaluation timer ended. View archived remarks in History Record below.</p>
                      </div>
                    ) : (
                      <>
                        <div className="mb-3">
                          <h6 className="fw-bold alvix-text-dark-green mb-2"><i className="bi bi-patch-check-fill text-warning me-2"></i>AI Assessment Remarks:</h6>
                          <div className="small bg-white p-3 rounded border alvix-gold-border text-dark">
                            {latest.ai_feedback ?? 'None'}
                          </div>
                        </div>

                        <div className="row g-2 mb-3">
                          <div className="col-6">
                            <div className="p-2 border rounded text-center bg-white alvix-gold-border">
                              <small className="d-block text-muted">Integrity &amp; Copy Check</small>
                              {latest.copy_risk_level === 'High' ? (
                                <strong className="text-danger"><i className="bi bi-flag-fill me-1"></i> Copy Risk: High (Flagged for Admin Review)</strong>
                              ) : latest.copy_risk_level === 'Medium' ? (
                                <strong className="text-warning"><i className="bi bi-exclamation-circle me-1"></i> Copy Risk: Medium</strong>
                              ) : (
                                <strong className="text-success"><i className="bi bi-shield-check me-1"></i> Copy Risk: Low (Original)</strong>
                              )}
                            </div>
                          </div>
                          <div className="col-6">
                            <div className="p-2 border rounded text-center bg-white alvix-gold-border">
                              <small className="d-block text-muted">Rubric Marks</small>
                              <strong className="text-success fs-6"><i className="bi bi-star-fill text-warning me-1"></i> {dj(latest.marks, latest.score)} / {dj(latest.total_marks, 10)}</strong>
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-5 text-muted my-auto">
                    <i className="bi bi-robot fs-1 d-block mb-2 text-warning"></i>
                    <p className="mb-0">Submit your notes or file to trigger Gemini AI logic analysis.</p>
                  </div>
                )}

                <small className="text-muted text-center d-block mt-auto"><i className="bi bi-info-circle me-1"></i> Real-time AI Multimodal Evaluation</small>
              </div>
            </div>
          </div>

        </div>

        {/* BOTTOM RECORD TABLE WITH VIEW REMARKS BUTTON */}
        <div className="card shadow-sm alvix-gold-border">
          <div className="card-header alvix-header-gold fw-bold py-3">
            <i className="bi bi-clock-history me-2"></i>Assignment Submissions History &amp; Record
          </div>
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="alvix-bg-gold">
                  <tr>
                    <th className="alvix-text-dark-green">Lesson / Day</th>
                    {/* Owner-approved fix: header order now matches the cells (deadline, then submitted). */}
                    <th className="alvix-text-dark-green">Deadline Date</th>
                    <th className="alvix-text-dark-green">Submitted Date &amp; Time</th>
                    <th className="alvix-text-dark-green">Assignment Question</th>
                    <th className="alvix-text-dark-green">Uploaded File</th>
                    <th className="alvix-text-dark-green">AI Remarks</th>
                    <th className="alvix-text-dark-green">Marks</th>
                  </tr>
                </thead>
                <tbody>
                  {data.all_submissions.length ? data.all_submissions.map((sub) => (
                    <tr key={sub.id}>
                      <td>
                        <span className="badge bg-success">Day {sub.lesson?.day_number}</span>
                        <small className="d-block text-muted fw-bold">{sub.lesson?.title}</small>
                      </td>

                      {/* Unique Deadline for each Lesson */}
                      <td>
                        <small className="fw-semibold text-dark">
                          {sub.lesson?.deadline ? djDate(sub.lesson.deadline, DT) : djDate(sub.lesson?.created_at, DT)}
                        </small>
                      </td>
                      <td>{djDate(sub.submitted_at, DT)}</td>
                      <td>
                        <button type="button" className="btn btn-sm alvix-btn-gold" onClick={() => overlays.showQuestionCard(dj(sub.question_prompt, data.assignment_prompt))}>
                          <i className="bi bi-eye me-1"></i> View Question
                        </button>
                      </td>
                      <td>
                        {sub.file_submission ? (
                          <a href={sub.file_submission} target="_blank" rel="noreferrer" className="btn btn-sm btn-outline-success">
                            <i className="bi bi-file-earmark-image me-1"></i> View Submitted File
                          </a>
                        ) : (
                          <span className="badge bg-light text-muted">Text Only</span>
                        )}
                      </td>
                      <td>
                        <button type="button" className="btn btn-sm alvix-btn-gold" onClick={() => overlays.showRemarksCard(dj(sub.ai_feedback, 'No remarks available.'))}>
                          <i className="bi bi-chat-square-text me-1"></i> View Remarks
                        </button>
                      </td>
                      <td>
                        {/* Owner-approved fix: real total marks instead of "/ 5". */}
                        <span className="badge alvix-header-gold p-2">{sub.score} / {dj(sub.total_marks, 10)} Marks</span>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan="7" className="text-center py-4 text-muted">No submissions record found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>

      {overlays.render('Assignment Question')}
    </>
  );
}
