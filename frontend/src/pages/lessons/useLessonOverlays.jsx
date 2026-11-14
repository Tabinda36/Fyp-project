import { useCallback, useEffect, useRef, useState } from 'react';

/*
 * The mid-screen "question" and "remarks" notification cards shared by assignment.html and
 * quiz.html (showQuestionCard / closeQuestionCard / showRemarksCard / closeRemarksCard).
 * Bodies are set as HTML, like the template's `body.innerHTML = text`.
 * The remarks card auto-closes after 60 seconds.
 */
export function useNotificationOverlays() {
  const [question, setQuestion] = useState({ open: false, html: '' });
  const [remarks, setRemarks] = useState({ open: false, html: '' });
  const remarksTimer = useRef(null);

  const closeRemarksCard = useCallback(() => {
    setRemarks({ open: false, html: '' });
    if (remarksTimer.current) clearTimeout(remarksTimer.current);
  }, []);

  const showRemarksCard = useCallback((text) => {
    setRemarks({ open: true, html: text ?? '' });
    if (remarksTimer.current) clearTimeout(remarksTimer.current);
    remarksTimer.current = setTimeout(() => {
      closeRemarksCard();
    }, 60000); // 60 Seconds
  }, [closeRemarksCard]);

  const showQuestionCard = useCallback((text) => setQuestion({ open: true, html: text ?? '' }), []);
  const closeQuestionCard = useCallback(() => setQuestion((q) => ({ ...q, open: false })), []);

  const reset = useCallback(() => {
    setQuestion({ open: false, html: '' });
    setRemarks({ open: false, html: '' });
    if (remarksTimer.current) clearTimeout(remarksTimer.current);
  }, []);

  useEffect(() => () => {
    if (remarksTimer.current) clearTimeout(remarksTimer.current);
  }, []);

  const render = (questionTitle) => (
    <>
      {/* MID-SCREEN FLOATING QUESTION NOTIFICATION CARD OVERLAY */}
      <div id="questionNotificationOverlay" style={question.open ? { display: 'flex' } : undefined}>
        <div id="questionNotificationCard" className="card alvix-gold-border rounded-3 overflow-hidden">
          <div className="card-header alvix-header-gold d-flex justify-content-between align-items-center py-3">
            <span className="fw-bold fs-6"><i className="bi bi-patch-question-fill me-2" style={{ color: '#d4af37' }}></i>{questionTitle}</span>
            <button type="button" className="btn-close btn-close-white btn-sm" onClick={closeQuestionCard}></button>
          </div>
          <div className="card-body bg-white p-4">
            <div id="notificationQuestionBody" className="small text-dark mb-4" style={{ maxHeight: '250px', overflowY: 'auto' }} dangerouslySetInnerHTML={{ __html: question.html }}></div>
            <button type="button" className="btn alvix-btn-gold w-100 py-2 fw-bold" onClick={closeQuestionCard}>OK</button>
          </div>
        </div>
      </div>

      {/* MID-SCREEN FLOATING REMARKS NOTIFICATION CARD OVERLAY */}
      <div id="remarksNotificationOverlay" style={remarks.open ? { display: 'flex' } : undefined}>
        <div id="remarksNotificationCard" className="card alvix-gold-border rounded-3 overflow-hidden">
          <div className="card-header alvix-header-gold d-flex justify-content-between align-items-center py-3">
            <span className="fw-bold fs-6"><i className="bi bi-chat-square-text-fill me-2" style={{ color: '#d4af37' }}></i>AI Assessment Remarks</span>
            <button type="button" className="btn-close btn-close-white btn-sm" onClick={closeRemarksCard}></button>
          </div>
          <div className="card-body bg-white p-4">
            <div id="notificationRemarksBody" className="small text-dark mb-4" style={{ maxHeight: '250px', overflowY: 'auto' }} dangerouslySetInnerHTML={{ __html: remarks.html }}></div>
            <button type="button" className="btn alvix-btn-gold w-100 py-2 fw-bold" onClick={closeRemarksCard}>OK</button>
          </div>
        </div>
      </div>
    </>
  );

  return { showQuestionCard, closeQuestionCard, showRemarksCard, closeRemarksCard, reset, render };
}

/*
 * "TOP CARD COMPLETE CLEAR / RESET AFTER 60 SECONDS ON PAGE LOAD": when the page shows a
 * latest submission, the evaluation panel switches to its placeholder 60 s after each load.
 * Returns true once the timer has fired for the current `data`.
 */
export function useResultPanelReset(data, hasResult) {
  const [expiredFor, setExpiredFor] = useState(null);

  useEffect(() => {
    if (!data || !hasResult) return undefined;
    const timer = setTimeout(() => setExpiredFor(data), 60000); // 60000 ms = 60 Seconds
    return () => clearTimeout(timer);
  }, [data, hasResult]);

  return Boolean(data) && expiredFor === data;
}
