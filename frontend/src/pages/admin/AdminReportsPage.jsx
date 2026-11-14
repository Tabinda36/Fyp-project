import { announceNotificationsChanged } from '../../hooks/notificationEvents';
import AdminLoader from '../../layouts/AdminLoader';
import { apiFetch } from '../../api/client';
import { ICONS_1113, googleFont } from '../../cdn';
import { useFlash } from '../../hooks/useFlash';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { truncatechars } from '../../utils/djangoFormat';
import { rawStyle } from './adminModals';
import css from './AdminReportsPage.css?raw';

const FONT = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Poppins:wght@600;700;800');

/* Port of `admin_db/admin_reports.html` (rendered inside AdminLayout). */
export default function AdminReportsPage() {
  usePageAssets({ links: [ICONS_1113, FONT], css });
  const { data, ready, reload } = usePageData('/admin/reports/');
  const { addMessages } = useFlash();

  // Both forms posted to a view that redirected back to /admin_reports/.
  const post = async (form, path) => {
    try {
      const res = await apiFetch(path, { method: 'POST', body: new FormData(form) });
      addMessages(res.messages);
      announceNotificationsChanged('page'); // refresh the bell's pending-reports badge
      form.reset();
    } catch (err) {
      // e.g. the report was already deleted in another tab: show the current list
      addMessages([{ tags: 'error', message: err.message }]);
    }
    reload();
  };

  const onRespond = (event, reportId) => {
    event.preventDefault();
    post(event.currentTarget, `/admin/reports/${reportId}/respond/`);
  };

  const onDelete = (event, reportId) => {
    event.preventDefault();
    if (!window.confirm('Are you sure you want to delete this report?')) return;
    post(event.currentTarget, `/admin/reports/${reportId}/delete/`);
  };

  if (!ready) return <AdminLoader />;
  const { reports } = data;

  return (
    <div className="container-fluid py-4">
      <div className="content-wrapper">

        <div className="d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-3 mb-4">
          <div>
            <h2 className="page-title mb-1">📑 Student Reports (Admin Panel)</h2>
            <p className="text-muted mb-0" ref={rawStyle('color: #047857 !important; font-weight: 500;')}>Review student reported issues, send responses, and resolve support tickets.</p>
          </div>
        </div>

        {/* Dynamic Counters */}
        <div className="metrics-row">
          <div className="metric-item">
            <h3>{data.total_submissions || reports.length}</h3>
            <p>📂 Total Submissions</p>
          </div>
          <div className="metric-item">
            <h3>{data.reviewed_reports || 0}</h3>
            <p>👨‍🎓 Reviewed Reports</p>
          </div>
          <div className="metric-item">
            <h3>{data.pending_reports || 0}</h3>
            <p>⏳ Pending Review</p>
          </div>
          <div className="metric-item">
            <h3>{data.active_today || 0}</h3>
            <p>✨ Active Today</p>
          </div>
        </div>

        {/* Reports Table */}
        <div className="section">
          <h4>👨‍🎓 Incoming Student Reports</h4>
          <div className="table-responsive">
            <table className="table align-middle" id="reportsTable">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Course Name</th>
                  <th>Problem Type</th>
                  <th>Problem Title &amp; Description</th>
                  <th>Status Indicator</th>
                  <th style={{ minWidth: '280px' }}>Send Response to Student</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.length ? (
                  reports.map((report) => (
                    <tr id={`row-report-${report.id}`} key={report.id}>
                      <td className="fw-bold">{report.student_name}</td>
                      <td className="fw-semibold">{report.course_name}</td>
                      <td>
                        <span className="badge bg-light text-dark border">{report.problem_type_display}</span>
                      </td>
                      <td>
                        <strong className="d-block" style={{ color: '#064e3b' }}>{report.problem_title}</strong>
                        <small className="text-muted">{truncatechars(report.problem_description, 45)}</small>
                      </td>
                      <td>
                        {report.status === 'resolved' ? (
                          <span className="badge-seen"><i className="bi bi-check2-all"></i> Resolved</span>
                        ) : (
                          <span className="badge-pending"><i className="bi bi-clock"></i> Pending</span>
                        )}
                      </td>
                      <td>
                        <form method="POST" className="d-flex gap-2" onSubmit={(e) => onRespond(e, report.id)}>
                          <input type="text" name="feedback" className="form-control form-control-sm" placeholder="Write response to student..." required />
                          <button className="btn btn-green btn-sm px-3" type="submit">Send</button>
                        </form>
                      </td>
                      <td className="text-end">
                        <form method="POST" style={{ display: 'inline' }} onSubmit={(e) => onDelete(e, report.id)}>
                          <button type="submit" className="btn btn-danger-outline btn-sm">
                            <i className="bi bi-trash"></i> Delete
                          </button>
                        </form>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7" className="text-center py-4 text-muted" ref={rawStyle('color: #047857 !important;')}>
                      <i className="bi bi-inbox fs-3 d-block mb-2" style={{ color: '#d4af37' }}></i>
                      No student reports found yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
