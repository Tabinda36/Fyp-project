import AdminLoader from '../../layouts/AdminLoader';
import { ICONS_1113, googleFont } from '../../cdn';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { dflt, timesince } from '../../utils/djangoFormat';
import { rawStyle } from './adminModals';
import css from './AnalyticsPage.css?raw';

const FONT = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Poppins:wght@600;700;800');

const csvCell = (value) => {
  const s = value === null || value === undefined ? '' : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

/*
 * Owner-approved fix: "Export Analytics" did nothing. It now downloads a CSV of the
 * numbers shown on the page, generated in the browser.
 */
function exportAnalyticsCsv(data) {
  const rows = [
    ['Metric', 'Value'],
    ['Total Students', dflt(data.total_students, '0')],
    ['Total Courses', dflt(data.total_courses, '0')],
    ['Enrollments', dflt(data.total_enrollments, '0')],
    ['Assignments', dflt(data.total_assignments, '0')],
    ['Quizzes', dflt(data.total_quizzes, '0')],
    ['Completion', `${dflt(data.completion_rate, '0')}%`],
    [],
    ['Overall Performance', 'Value'],
    ['Course Completion Rate', `${dflt(data.completion_rate, '0')}%`],
    ['Quiz Performance', `${dflt(data.quiz_performance, '0')}%`],
    ['Assignment Submissions', dflt(data.assignment_submissions, '0')],
    ['Student Satisfaction', `${dflt(data.student_satisfaction, '0')}%`],
    [],
    ['Top Performing Courses'],
    ...data.top_performing_courses.map((c) => [c.title]),
  ];
  const csv = rows.map((r) => r.map(csvCell).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'alvix_analytics.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/* Port of `admin_db/analytics.html` (rendered inside AdminLayout). */
export default function AnalyticsPage() {
  usePageAssets({ links: [ICONS_1113, FONT], css });
  const { data, ready } = usePageData('/admin/analytics/');
  if (!ready) return <AdminLoader />;

  // `{{ x|default:'0' }}%` exactly as the template prints it (all values are plain numbers).
  const pct = (v) => `${dflt(v, '0')}%`;
  const bar = (v) => ({ style: { width: pct(v) }, 'aria-valuenow': dflt(v, '0') });

  return (
    <div className="analytics-dashboard-page container-fluid py-4">

      <div className="d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-3 mb-4 border-bottom pb-3" ref={rawStyle('border-color: rgba(212, 175, 55, 0.3) !important;')}>
        <div>
          <h2 className="page-title mb-1">📊 Analytics Dashboard</h2>
          <p className="mb-0" style={{ color: '#047857', fontWeight: 500 }}>Track platform metrics, performance, and recent activities.</p>
        </div>
        <button className="btn btn-green" onClick={() => exportAnalyticsCsv(data)}>
          <i className="bi bi-file-earmark-arrow-down"></i> Export Analytics
        </button>
      </div>

      {/* Stats Horizontal Bar */}
      <div className="stats-horizontal-bar">
        <div className="stat-item">
          <h3>{dflt(data.total_students, '0')}</h3>
          <p>👨‍🎓 Total Students</p>
        </div>
        <div className="stat-item">
          <h3>{dflt(data.total_courses, '0')}</h3>
          <p>📖 Total Courses</p>
        </div>
        <div className="stat-item">
          <h3>{dflt(data.total_enrollments, '0')}</h3>
          <p>📝 Enrollments</p>
        </div>
        <div className="stat-item">
          <h3>{dflt(data.total_assignments, '0')}</h3>
          <p>💼 Assignments</p>
        </div>
        <div className="stat-item">
          <h3>{dflt(data.total_quizzes, '0')}</h3>
          <p>❓ Quizzes</p>
        </div>
        <div className="stat-item">
          <h3>{pct(data.completion_rate)}</h3>
          <p>🏆 Completion</p>
        </div>
      </div>

      <div className="row mt-4 g-4">
        {/* Progress Metrics */}
        <div className="col-lg-6">
          <div className="section-card h-100">
            <h4 className="section-title">
              📈 Overall Performance
            </h4>

            <div className="mb-3">
              <p className="mb-1 fw-bold small" style={{ color: '#047857' }}>Course Completion Rate</p>
              <div className="progress">
                <div className="progress-bar" role="progressbar" {...bar(data.completion_rate)} aria-valuemin="0" aria-valuemax="100"></div>
              </div>
            </div>

            <div className="mb-3">
              <p className="mb-1 fw-bold small" style={{ color: '#047857' }}>Quiz Performance</p>
              <div className="progress">
                <div className="progress-bar" role="progressbar" {...bar(data.quiz_performance)} aria-valuemin="0" aria-valuemax="100"></div>
              </div>
            </div>

            <div className="mb-3">
              <p className="mb-1 fw-bold small" style={{ color: '#047857' }}>Assignment Submissions</p>
              <div className="progress">
                <div className="progress-bar" role="progressbar" {...bar(data.assignment_submissions)} aria-valuemin="0" aria-valuemax="100"></div>
              </div>
            </div>

            <div className="mb-2">
              <p className="mb-1 fw-bold small" style={{ color: '#047857' }}>Student Satisfaction</p>
              <div className="progress">
                <div className="progress-bar" role="progressbar" {...bar(data.student_satisfaction)} aria-valuemin="0" aria-valuemax="100"></div>
              </div>
            </div>
          </div>
        </div>

        {/* Top Performing Courses */}
        <div className="col-lg-6">
          <div className="section-card h-100">
            <h4 className="section-title">
              🏆 Top Performing Courses
            </h4>
            <div className="table-responsive">
              <table className="table align-middle mb-0">
                <thead>
                  <tr>
                    <th>Course</th>
                    <th>Students</th>
                    <th>Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {data.top_performing_courses.length ? (
                    data.top_performing_courses.map((topCourse, i) => (
                      <tr key={i}>
                        <td className="fw-bold" style={{ color: '#064e3b' }}>{topCourse.title}</td>
                        <td>{topCourse.student_count}</td>
                        {/* Python prints the float rating with one decimal (e.g. "4.0"); JSON drops the ".0". */}
                        <td style={{ color: '#d4af37', fontWeight: 700 }}>⭐ {Number(topCourse.rating).toFixed(1)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="3" className="text-center py-4" style={{ color: '#047857' }}>No course data available yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="row mt-4">
        <div className="col-lg-12">
          <div className="section-card">
            <h4 className="section-title">
              🔥 Recent Activity
            </h4>

            {data.recent_activities.length ? (
              data.recent_activities.map((activity, i) => (
                <div className="activity-item" key={i}>
                  <h6>👤 {activity.user?.username} {activity.action_description}</h6>
                  <small><i className="bi bi-clock me-1" style={{ color: '#d4af37' }}></i> {timesince(activity.timestamp)} ago</small>
                </div>
              ))
            ) : (
              <div className="text-center py-4" style={{ color: '#047857' }}>
                <i className="bi bi-info-circle fs-4 d-block mb-2" style={{ color: '#d4af37' }}></i>
                No recent activities recorded.
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
