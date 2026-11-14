import AdminLoader from '../../layouts/AdminLoader';
import { useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { ICONS_1113, googleFont } from '../../cdn';
import css from './LevelUsersTelemetryPage.css?raw';
import NotFoundPage from '../NotFoundPage';
import { important } from './CoursePageUtils';

/* Port of admin_db/level_users_telemetry.html. */

const FONT = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Poppins:wght@600;700;800');

export default function LevelUsersTelemetryPage() {
  usePageAssets({ links: [ICONS_1113, FONT], css });
  const { slug } = useParams();
  const { data, ready, notFound } = usePageData(`/admin-courses/levels/${slug}/users/`);
  const inputRef = useRef(null);
  const tableRef = useRef(null);

  // filterTelemetryTable() from the template (client-side row filter on ID / name / email).
  const filterTelemetryTable = () => {
    const filter = inputRef.current.value.toUpperCase();
    const tr = tableRef.current.getElementsByTagName('tr');
    for (let i = 1; i < tr.length; i++) {
      const tdId = tr[i].getElementsByTagName('td')[0];
      const tdName = tr[i].getElementsByTagName('td')[1];
      const tdEmail = tr[i].getElementsByTagName('td')[2];
      if (tdId || tdName || tdEmail) {
        const txtValue = (tdId ? tdId.textContent : '') + ' ' + (tdName ? tdName.textContent : '') + ' ' + (tdEmail ? tdEmail.textContent : '');
        tr[i].style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? '' : 'none';
      }
    }
  };

  if (notFound) return <NotFoundPage />;
  if (!ready) return <AdminLoader />;
  const {
    course_level: courseLevel, parent_course: parentCourse, enrollments, total_enrolled: totalEnrolled,
    completed_count: completedCount, active_count: activeCount, avg_progress: avgProgress,
  } = data;

  return (
    <div className="container-fluid py-4">
      <div className="content-wrapper">

        {/* Top Navigation */}
        <div className="d-flex justify-content-between align-items-center mb-3">
          <Link to="/courses_info/" className="btn-nav-outline">
            <i className="bi bi-arrow-left"></i> Back to All Courses
          </Link>
          <Link to={`/admindashboard/level/${courseLevel.slug}/course/`} className="btn-nav-green">
            <i className="bi bi-layers-half"></i> View Curriculum &amp; Lessons
          </Link>
        </div>

        {/* Master Telemetry Header Card (Requirement 1: View Users) */}
        <div className="telemetry-header-card">
          <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
            <div>
              <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                {courseLevel.level === 'Beginner' ? (
                  <span className="benchmark-badge-lg badge-harvard">
                    🏛️ Harvard CS50 Philosophy
                  </span>
                ) : courseLevel.level === 'Intermediate' ? (
                  <span className="benchmark-badge-lg badge-mit">
                    🏛️ MIT Data Structures &amp; Logic
                  </span>
                ) : (
                  <span className="benchmark-badge-lg badge-stanford">
                    🏛️ Stanford &amp; CMU Systems &amp; AI
                  </span>
                )}
                <span className="badge" style={{ background: '#064e3b', color: '#d4af37', border: '1.5px solid #d4af37', fontSize: '0.82rem', padding: '5px 12px', borderRadius: '20px' }}>
                  {courseLevel.level} Level Telemetry
                </span>
              </div>

              <h2 className="fw-bold mb-1" style={{ color: '#064e3b' }}>
                👥 Student Telemetry: {courseLevel.title}
              </h2>
              <p className="text-muted mb-0 small">
                Real-time student progress tracking, daily laboratory submissions, and diagnostic test analytics.
              </p>
            </div>

            <div className="text-md-end">
              <span className="badge" style={{ background: 'linear-gradient(135deg, #d4af37, #b8860b)', color: '#064e3b', fontWeight: 800, fontSize: '0.85rem', padding: '8px 16px', borderRadius: '12px' }}>
                Master Topic: {parentCourse.title}
              </span>
            </div>
          </div>
        </div>

        {/* KPI Metrics Grid */}
        <div className="row g-3 mb-4">
          <div className="col-sm-6 col-lg-3">
            <div className="kpi-card">
              <div className="kpi-icon kpi-icon-users">
                <i className="bi bi-people-fill"></i>
              </div>
              <div>
                <div className="text-muted small fw-bold">Total Enrolled</div>
                <h3 className="fw-bold mb-0" style={{ color: '#064e3b' }}>{totalEnrolled}</h3>
              </div>
            </div>
          </div>

          <div className="col-sm-6 col-lg-3">
            <div className="kpi-card">
              <div className="kpi-icon kpi-icon-active">
                <i className="bi bi-lightning-charge-fill"></i>
              </div>
              <div>
                <div className="text-muted small fw-bold">In-Progress Learners</div>
                <h3 className="fw-bold mb-0" style={{ color: '#0284c7' }}>{activeCount}</h3>
              </div>
            </div>
          </div>

          <div className="col-sm-6 col-lg-3">
            <div className="kpi-card">
              <div className="kpi-icon kpi-icon-completed">
                <i className="bi bi-check-circle-fill"></i>
              </div>
              <div>
                <div className="text-muted small fw-bold">Mastery Completed</div>
                <h3 className="fw-bold mb-0" style={{ color: '#059669' }}>{completedCount}</h3>
              </div>
            </div>
          </div>

          <div className="col-sm-6 col-lg-3">
            <div className="kpi-card">
              <div className="kpi-icon kpi-icon-progress">
                <i className="bi bi-graph-up-arrow"></i>
              </div>
              <div>
                <div className="text-muted small fw-bold">Avg Cohort Progress</div>
                <h3 className="fw-bold mb-0" style={{ color: '#b8860b' }}>{avgProgress}%</h3>
              </div>
            </div>
          </div>
        </div>

        {/* Student Telemetry Data Table */}
        <div className="telemetry-card mb-5">
          <div className="p-3 bg-light border-bottom d-flex justify-content-between align-items-center flex-wrap gap-2" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.3)' })}>
            <div className="d-flex align-items-center gap-2">
              <i className="bi bi-table text-success"></i>
              <h5 className="fw-bold mb-0" style={{ color: '#064e3b' }}>Active Cohort Students ({totalEnrolled})</h5>
            </div>
            <div>
              <input type="text" id="telemetrySearch" ref={inputRef} className="form-control form-control-sm" placeholder="Filter by student name or ID..." style={{ border: '1px solid #d4af37', borderRadius: '8px', width: '260px' }} onKeyUp={filterTelemetryTable} />
            </div>
          </div>

          <div className="table-responsive">
            <table className="table telemetry-table mb-0 align-middle" id="telemetryTable" ref={tableRef}>
              <thead>
                <tr>
                  <th>Student ID</th>
                  <th>Student Name</th>
                  <th>Email Address</th>
                  <th>Enrollment Date</th>
                  <th>Mastery Progress</th>
                  <th>Assignments</th>
                  <th>Quizzes</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {enrollments.map((student) => (
                  <tr key={student.id}>
                    <td>
                      <span className="badge" style={{ background: 'rgba(6, 78, 59, 0.1)', color: '#064e3b', border: '1px solid rgba(6, 78, 59, 0.3)', fontWeight: 700, fontSize: '0.8rem', borderRadius: '8px' }}>
                        {student.student_id}
                      </span>
                    </td>
                    <td>
                      <div className="fw-bold text-dark">{student.full_name}</div>
                      <span className="small text-muted">@{student.user.username}</span>
                    </td>
                    <td>
                      <span className="text-muted">{student.email}</span>
                    </td>
                    <td>
                      <span className="small text-muted">{student.enrolled_at}</span>
                    </td>
                    <td style={{ minWidth: '170px' }}>
                      <div className="d-flex justify-content-between align-items-center small fw-bold">
                        <span className="text-success">{student.progress}%</span>
                        <span className="text-muted">{student.completed_lessons}/{student.total_lessons} Days</span>
                      </div>
                      <div className="progress-bar-custom">
                        <div className="progress-fill" style={{ width: `${student.progress}%` }}></div>
                      </div>
                    </td>
                    <td className="text-center">
                      <span className="badge bg-light text-dark border fw-bold px-2 py-1">
                        <i className="bi bi-file-earmark-code text-warning me-1"></i>{student.attempted_assignments}
                      </span>
                    </td>
                    <td className="text-center">
                      <span className="badge bg-light text-dark border fw-bold px-2 py-1">
                        <i className="bi bi-patch-check text-success me-1"></i>{student.attempted_quizzes}
                      </span>
                    </td>
                    <td>
                      {student.status === 'Completed' ? (
                        <span className="badge bg-success text-white px-3 py-1 rounded-pill fw-semibold">
                          <i className="bi bi-award-fill me-1"></i> Completed
                        </span>
                      ) : (
                        <span className="badge px-3 py-1 rounded-pill fw-semibold" style={{ background: '#fef3c7', color: '#92400e', border: '1px solid #fde68a' }}>
                          <i className="bi bi-clock-history me-1"></i> Active
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {enrollments.length === 0 && (
                  <tr>
                    <td colSpan="8" className="text-center py-5">
                      <div className="p-4">
                        <i className="bi bi-people mb-2 d-block" style={{ fontSize: '2.5rem', color: '#d4af37' }}></i>
                        <h5 className="fw-bold" style={{ color: '#064e3b' }}>No Students Enrolled in this Level Yet</h5>
                        <p className="text-muted small mb-0">When students select this university tier, their telemetry and learning stats will populate here in real-time.</p>
                      </div>
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
