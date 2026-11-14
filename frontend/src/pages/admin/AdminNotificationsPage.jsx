import toast from 'react-hot-toast';
import AdminLoader from '../../layouts/AdminLoader';
import { useRef, useState } from 'react';
import { ApiError, apiFetch } from '../../api/client';
import { ICONS_1113, googleFont } from '../../cdn';
import { useFlash } from '../../hooks/useFlash';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { djDate } from '../../utils/djangoFormat';
import { rawStyle } from './adminModals';
import css from './AdminNotificationsPage.css?raw';

const FONT = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Poppins:wght@600;700;800');

/* Port of `admin_db/admin_notifications.html` (rendered inside AdminLayout). */
export default function AdminNotificationsPage() {
  usePageAssets({ links: [ICONS_1113, FONT], css });
  const { data, ready, reload } = usePageData('/admin/notifications/');
  const { addMessages } = useFlash();
  const [specific, setSpecific] = useState(false);
  const studentSelectRef = useRef(null);

  // toggleSpecificStudentDropdown()
  const toggleSpecificStudentDropdown = (event) => {
    const isSpecific = event.target.value === 'specific_student';
    setSpecific(isSpecific);
    if (!isSpecific && studentSelectRef.current) studentSelectRef.current.value = '';
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    try {
      const res = await apiFetch('/admin/notifications/', { method: 'POST', body: new FormData(form) });
      addMessages(res.messages);
      form.reset();
      setSpecific(false);
      reload();
    } catch (err) {
      // Nothing was sent (empty body): the template view simply re-rendered the page.
      if (err instanceof ApiError && err.status === 400) return;
      toast.error(!err?.status || err.status >= 500 ? 'Server error: the notification was not sent. Please try again.' : (err.data?.error || 'Could not send the notification.'));
    }
  };

  if (!ready) return <AdminLoader />;
  const { students_list: studentsList, dispatch_history: dispatchHistory } = data;

  return (
    <div className="notification-wrapper container-fluid py-4">

      <div className="border-bottom pb-3 mb-4" ref={rawStyle('border-color: rgba(212, 175, 55, 0.3) !important;')}>
        <h2 className="page-title mb-1">🔔 Notifications Control Panel</h2>
        <p className="mb-0" style={{ color: '#047857', fontWeight: 500 }}>Create and dispatch notifications directly to dynamic recipient categories.</p>
      </div>

      {/* Generator Card */}
      <div className="generator-card">
        <div className="d-flex align-items-center gap-2 mb-4">
          <h4 className="section-title mb-0" style={{ fontSize: '1.35rem' }}>✨ Generate &amp; Send Notification</h4>
        </div>

        <form method="POST" onSubmit={onSubmit}>
          <div className="row g-3">
            <div className="col-md-4">
              <label className="form-label fw-bold small" style={{ color: '#047857' }}>Target Recipient</label>
              <select className="form-select" name="target_recipient" id="targetRecipientSelect" required defaultValue="" onChange={toggleSpecificStudentDropdown}>
                <option value="">Select Recipient</option>
                <option value="all_students">All Students</option>
                <option value="enrolled_students">Enrolled Students Only</option>
                <option value="specific_student">Specific Student</option>
              </select>
            </div>

            {/* Specific Student Dropdown (Initially Hidden) */}
            <div className="col-md-4" id="specificStudentWrapper" style={{ display: specific ? 'block' : 'none' }}>
              <label className="form-label fw-bold small" style={{ color: '#047857' }}>Choose Student</label>
              <select className="form-select" name="specific_student_id" id="specificStudentSelect" ref={studentSelectRef} required={specific} defaultValue="">
                <option value="">Select a student...</option>
                {studentsList.map((student) => (
                  <option value={student.id} key={student.id}>
                    {student.username} {student.get_full_name ? `(${student.get_full_name})` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-md-4">
              <label className="form-label fw-bold small" style={{ color: '#047857' }}>Category Type</label>
              <select className="form-select" name="category_type" required defaultValue="">
                <option value="">Notification Type</option>
                <option value="announcement">Announcement</option>
                <option value="course_update">Course Update</option>
                <option value="alert">Urgent Alert</option>
                <option value="reminder">Assignment / Quiz Reminder</option>
              </select>
            </div>

            <div className="col-md-4">
              <label className="form-label fw-bold small" style={{ color: '#047857' }}>Subject Heading</label>
              <input type="text" className="form-control" name="subject_heading" placeholder="Notification Subject" required />
            </div>

            <div className="col-12">
              <label className="form-label fw-bold small" style={{ color: '#047857' }}>Notification Body</label>
              <textarea rows="4" className="form-control" name="notification_body" placeholder="Type your dynamic announcement message here..." required></textarea>
            </div>

            <div className="col-md-3 mt-4">
              <button className="btn btn-green w-100 py-2" type="submit">
                <i className="bi bi-send-fill"></i> Dispatch Notification
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Dispatch History Section */}
      <div className="history-card">
        <h4 className="section-title">📜 Dispatch History</h4>
        <div className="table-responsive">
          <table className="table align-middle">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Target Recipient</th>
                <th>Category</th>
                <th>Date Sent</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {dispatchHistory.length ? (
                dispatchHistory.map((notification) => (
                  <tr key={notification.id}>
                    <td className="fw-bold" style={{ color: '#064e3b' }}>{notification.subject_heading}</td>
                    <td>{notification.get_target_recipient_display}</td>
                    <td><span className="badge bg-light text-dark border">{notification.get_category_type_display}</span></td>
                    <td>{djDate(notification.created_at, 'd M Y, h:i A')}</td>
                    <td>
                      <span className="badge-sent">Dispatched</span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="text-center py-4" style={{ color: '#047857' }}>
                    <i className="bi bi-bell-slash fs-3 d-block mb-2" style={{ color: '#d4af37' }}></i>
                    No notifications have been generated yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
