import AdminLoader from '../../layouts/AdminLoader';
import { useEffect, useRef } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { usePageData } from '../../hooks/usePageData';
import { usePageAssets } from '../../hooks/usePageAssets';
import { useFlash } from '../../hooks/useFlash';
import { apiFetch, ApiError } from '../../api/client';
import { djDate } from '../../utils/djangoFormat';
import { useNotificationOverlays, useResultPanelReset } from './useLessonOverlays';
import css from './QuizPage.css?raw';

/* Port of `student_dashboard/course_data/quiz.html` (rendered inside StudentLayout). */

const DT = 'd M Y, h:i A';
// Django's `|default` treats 0 / '' / None as empty
const dj = (value, fallback) => (value === null || value === undefined || value === '' || value === 0 || value === false ? fallback : value);

function QuizForm({ lesson, questions, onSubmitted }) {
  const { addMessages } = useFlash();
  const busy = useRef(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy.current) return;
    const form = e.currentTarget;
    busy.current = true;
    try {
      const res = await apiFetch('/lessons/quiz/', { method: 'POST', body: new FormData(form), query: { lesson_id: lesson.id } });
      addMessages(res.messages);
    } catch (err) {
      if (err instanceof ApiError && err.data?.messages) addMessages(err.data.messages);
      else throw err;
    } finally {
      busy.current = false;
    }
    // The view redirected to itself (?lesson_id=...): reload the page data.
    onSubmitted();
  };

  return (
    <form method="POST" action={`/quiz/?lesson_id=${lesson.id}`} onSubmit={handleSubmit}>
      <div style={{ maxHeight: '400px', overflowY: 'auto' }} className="pe-2">
        {questions.map((question, qIdx) => (
          <div className="p-3 mb-3 bg-white rounded border alvix-gold-border shadow-sm" key={`${question.id}-${qIdx}`}>
            <h6 className="fw-bold alvix-text-dark-green mb-2">Q{qIdx + 1}: {question.text}</h6>
            {question.code ? (
              <div className="mb-3 p-2 bg-dark rounded border border-warning font-monospace text-light small overflow-auto" style={{ maxHeight: '180px' }}>
                <pre className="mb-0"><code>{question.code}</code></pre>
              </div>
            ) : null}
            <div className="quiz-options-list">
              {question.options.map((option, oIdx) => (
                <div className="form-check custom-quiz-option p-2 mb-2 rounded" key={oIdx}>
                  <input className="form-check-input ms-2 me-3" type="radio" name={`q_${question.id}`} id={`opt_${question.id}_${oIdx + 1}`} value={option} required />
                  <label className="form-check-label w-100" htmlFor={`opt_${question.id}_${oIdx + 1}`}>
                    {option}
                  </label>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button type="submit" className="btn alvix-btn-gold w-100 py-3 mt-3 fs-6 shadow">
        <i className="bi bi-check-circle-fill me-1"></i> Submit Quiz Answers
      </button>
    </form>
  );
}

export default function QuizPage() {
  const { lessonId: pathLessonId } = useParams();
  const [params] = useSearchParams();
  const lessonId = pathLessonId || params.get('lesson_id') || undefined;
  const { data, ready, reload } = usePageData('/lessons/quiz/', { lesson_id: lessonId });
  usePageAssets({ css });
  const overlays = useNotificationOverlays();
  const panelExpired = useResultPanelReset(ready ? data : null, Boolean(data?.latest_submission));

  const { reset } = overlays;
  useEffect(() => reset(), [data, reset]);

  if (!ready) return <AdminLoader />;

  const { lesson, latest_submission: latest } = data;
  const questions = data.quiz_questions || [];

  return (
    <>
      <div className="container-fluid px-0">

        {/* Header */}
        <div className="d-flex justify-content-between align-items-center mb-4 pb-2 border-bottom border-warning">
          <div>
            <h3 className="fw-bold alvix-text-dark-green mb-0"><i className="bi bi-patch-question me-2" style={{ color: '#d4af37' }}></i>ALVIX AI Assessment Quiz</h3>
            <small className="text-muted">Test your memory parameters with real-time adaptive marking.</small>
          </div>
          <div>
            <Link to="/mycourse/" className="btn btn-outline-secondary btn-sm me-2"><i className="bi bi-arrow-left"></i> Back to Tracks</Link>
            <span className="badge alvix-header-gold p-2 fs-6">Lesson: {lesson.title}</span>
          </div>
        </div>

        {/* TWO EQUAL-HEIGHT CARDS */}
        <div className="row g-4 mb-5 align-items-stretch">

          {/* CARD 1: Quiz Questions & Submission Form */}
          <div className="col-lg-7 d-flex">
            <div className="card shadow-sm alvix-gold-border w-100 flex-fill">
              <div className="card-header alvix-header-gold fw-bold d-flex justify-content-between align-items-center py-3">
                <span><i className="bi bi-card-checklist me-2"></i>Quiz Questions Portal</span>
                <div className="d-flex align-items-center gap-2">
                  <small className="badge bg-light text-dark border"><i className="bi bi-calendar-check text-success me-1"></i>Issued: {djDate(lesson.quiz_issued_at, DT) || 'Active upon click'}</small>
                  <small className="badge bg-warning text-dark"><i className="bi bi-clock me-1"></i>Real-time Assessment</small>
                </div>
              </div>
              <div className="card-body alvix-bg-gold p-4 d-flex flex-column justify-content-center">

                {latest ? (
                  <div className="alert alert-success border-0 shadow-sm text-center py-5 mb-0 my-auto">
                    <i className="bi bi-check-circle-fill text-success fs-1 d-block mb-3"></i>
                    <h4 className="fw-bold alvix-text-dark-green">Quiz Already Completed!</h4>
                    <p className="text-muted small mb-0">Attempted on {djDate(latest.submitted_at, DT)}</p>
                    <small className="text-muted d-block mt-2">Check archived details and questions in your history record below.</small>
                  </div>
                ) : questions.length ? (
                  <QuizForm key={lesson.id} lesson={lesson} questions={questions} onSubmitted={reload} />
                ) : (
                  <div className="text-center py-5 my-auto">
                    <div className="spinner-border text-warning mb-3" role="status"></div>
                    <h6 className="alvix-text-dark-green fw-bold">Configuring adaptive questionnaire matrices...</h6>
                  </div>
                )}

              </div>
            </div>
          </div>

          {/* CARD 2: AI Evaluation & Quiz Remarks (Resets after 60s) */}
          <div className="col-lg-5 d-flex">
            <div className="card shadow-sm alvix-gold-border w-100 flex-fill">
              <div className="card-header alvix-header-gold fw-bold d-flex justify-content-between align-items-center py-3">
                <span><i className="bi bi-cpu me-2"></i>AI Assessment &amp; Score</span>
                <span id="aiQuizScoreBadge">
                  {latest && !panelExpired ? (
                    <span className="badge bg-warning text-dark fs-6">{dj(latest.score, 0)} / {dj(latest.total_questions, 5)} Marks</span>
                  ) : (
                    <span className="badge bg-secondary fs-6">Pending Quiz</span>
                  )}
                </span>
              </div>
              <div className="card-body alvix-bg-gold p-4 d-flex flex-column justify-content-between" id="aiQuizCardBody">
                {latest ? (
                  <div id="aiQuizEvaluationContent">
                    {panelExpired ? (
                      <div className="text-center py-5 text-muted my-auto">
                        <i className="bi bi-robot fs-1 d-block mb-2 text-warning"></i>
                        <p className="mb-0">Quiz evaluation timer ended. View detailed summary and remarks in History Record below.</p>
                      </div>
                    ) : (
                      <>
                        <div className="mb-3">
                          <h6 className="fw-bold alvix-text-dark-green mb-2"><i className="bi bi-patch-check-fill text-warning me-2"></i>AI Performance Analysis:</h6>
                          <div className="small bg-white p-3 rounded border alvix-gold-border text-dark">
                            {dj(latest.ai_feedback, 'Quiz evaluation processed successfully.')}
                          </div>
                        </div>

                        {latest.wrong_answers_explanation && latest.wrong_answers_explanation.length ? (
                          <div className="mb-3">
                            <h6 className="fw-bold text-danger mb-2"><i className="bi bi-exclamation-triangle-fill me-1"></i>Remarks &amp; Explanations for Wrong Answers:</h6>
                            <div style={{ maxHeight: '220px', overflowY: 'auto' }} className="pe-1">
                              {latest.wrong_answers_explanation.map((wa, i) => (
                                <div className="p-2 mb-2 bg-white rounded border border-danger small shadow-sm" key={i}>
                                  <strong className="text-dark d-block mb-1">Q{wa.question_number}: {wa.question}</strong>
                                  <div className="d-flex justify-content-between small mb-1">
                                    <span className="text-danger"><i className="bi bi-x-circle me-1"></i>Your Answer: <strong>{wa.user_answer}</strong></span>
                                    <span className="text-success"><i className="bi bi-check-circle me-1"></i>Correct: <strong>{wa.correct_answer}</strong></span>
                                  </div>
                                  <div className="mt-1 p-1 bg-light rounded text-muted small">
                                    <i className="bi bi-info-circle me-1 text-primary"></i><strong>Explanation:</strong> {wa.explanation}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : null}

                        <div className="row g-2 mb-3">
                          <div className="col-6">
                            <div className="p-2 border rounded text-center bg-white alvix-gold-border">
                              <small className="d-block text-muted">Accuracy Rate</small>
                              <strong className="alvix-text-dark-green"><i className="bi bi-graph-up-arrow me-1"></i> {dj(latest.percentage, '0')}%</strong>
                            </div>
                          </div>
                          <div className="col-6">
                            <div className="p-2 border rounded text-center bg-white alvix-gold-border">
                              <small className="d-block text-muted">Quiz Status</small>
                              {latest.score > 2 ? (
                                <strong className="text-success"><i className="bi bi-check-circle me-1"></i> Passed</strong>
                              ) : (
                                <strong className="text-danger"><i className="bi bi-x-circle me-1"></i> Needs Review</strong>
                              )}
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-5 text-muted my-auto">
                    <i className="bi bi-robot fs-1 d-block mb-2 text-warning"></i>
                    <p className="mb-0">Select options and submit quiz to view instant AI evaluation.</p>
                  </div>
                )}

                <small className="text-muted text-center d-block mt-auto"><i className="bi bi-info-circle me-1"></i> Real-time AI Adaptive Scoring</small>
              </div>
            </div>
          </div>

        </div>

        {/* BOTTOM RECORD TABLE WITH VIEW BUTTONS */}
        <div className="card shadow-sm alvix-gold-border">
          <div className="card-header alvix-header-gold fw-bold py-3">
            <i className="bi bi-clock-history me-2"></i>Quiz History &amp; Performance Records
          </div>
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="alvix-bg-gold">
                  <tr>
                    <th className="alvix-text-dark-green">Attempted Date &amp; Time</th>
                    <th className="alvix-text-dark-green">Quiz Questions</th>
                    <th className="alvix-text-dark-green">AI Remarks</th>
                    <th className="alvix-text-dark-green">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {data.all_submissions.length ? data.all_submissions.map((sub) => (
                    <tr key={sub.id}>
                      <td>
                        <strong className="d-block alvix-text-dark-green">{djDate(sub.submitted_at, 'd M Y')}</strong>
                        <small className="text-muted">{djDate(sub.submitted_at, 'h:i A')}</small>
                      </td>
                      <td>
                        {/* View Quiz Questions Notification Button */}
                        <button type="button" className="btn btn-sm alvix-btn-gold" onClick={() => overlays.showQuestionCard(dj(sub.question_summary, 'Quiz questions record archived.'))}>
                          <i className="bi bi-eye me-1"></i> View Quiz Summary
                        </button>
                      </td>
                      <td>
                        {/* View Remarks Notification Button */}
                        <button type="button" className="btn btn-sm alvix-btn-gold" onClick={() => overlays.showRemarksCard(dj(sub.ai_feedback, 'No detailed remarks available.'))}>
                          <i className="bi bi-chat-square-text me-1"></i> View Remarks
                        </button>
                      </td>
                      <td>
                        <span className="badge alvix-header-gold p-2">{sub.score} / {dj(sub.total_questions, 5)} Marks</span>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan="4" className="text-center py-4 text-muted">No quiz performance records found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>

      {overlays.render('Quiz Questions Summary')}
    </>
  );
}
