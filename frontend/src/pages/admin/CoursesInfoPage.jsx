import AdminLoader from '../../layouts/AdminLoader';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { ICONS_1113, googleFont } from '../../cdn';
import css from './CoursesInfoPage.css?raw';
import { important } from './CoursePageUtils';

/* Port of admin_db/courses_info.html (GET ?tier=&search=). */

const FONT = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Poppins:wght@600;700;800');

export default function CoursesInfoPage() {
  usePageAssets({ links: [ICONS_1113, FONT], css });
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { data, ready } = usePageData('/admin-courses/levels/', {
    tier: searchParams.get('tier'),
    search: searchParams.get('search'),
  });
  if (!ready) return <AdminLoader />;

  const { level_cards: levelCards, total_courses: totalCourses, total_cards: totalCards, search_query: searchQuery, tier_filter: tierFilter } = data;

  // <form method="GET"> : submit the form fields as the new query string of this page.
  const onSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    new FormData(e.currentTarget).forEach((value, key) => params.append(key, value));
    navigate(`?${params.toString()}`);
  };

  return (
    <div className="container-fluid py-4">
      <div className="content-wrapper">

        {/* Top Header & Metrics Banner */}
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-start align-items-md-center gap-3 mb-4 border-bottom pb-4" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.3)' })}>
          <div>
            <h2 className="page-title mb-1">🏛️ University-Benchmarked Course Management</h2>
            <p className="text-muted mb-0" ref={important({ 'color': '#047857' })} style={{ fontWeight: 500 }}>
              Harvard CS50 (Beginner), MIT (Intermediate), and Stanford &amp; CMU (Advanced) multi-tier curriculum system.
            </p>
          </div>

          <div className="d-flex flex-wrap gap-2 align-items-center">
            <div className="stats-badge-card">
              <span className="text-muted small fw-bold" ref={important({ 'color': '#047857' })}>Master Courses</span>
              <span className="stats-count">{totalCourses || '0'}</span>
            </div>
            <div className="stats-badge-card">
              <span className="text-muted small fw-bold" ref={important({ 'color': '#047857' })}>Academic Tiers</span>
              <span className="stats-count">{totalCards || '0'}</span>
            </div>
            <Link to="/add_course/" className="btn btn-green-main text-decoration-none">
              <i className="bi bi-plus-circle-fill"></i> Add Course
            </Link>
          </div>
        </div>

        {/* Filter & Search Toolbar */}
        <div className="card p-3 mb-4 shadow-sm" style={{ border: '1.5px solid #d4af37', borderRadius: '14px', background: '#ffffff' }}>
          <div className="d-flex flex-column flex-lg-row align-items-lg-center justify-content-between gap-3">
            {/* University Tier Pills */}
            <div className="d-flex flex-wrap gap-2">
              <Link to={`?search=${encodeURIComponent(searchQuery || "")}`} className={`tier-filter-btn ${!tierFilter ? 'active' : ''}`}>
                <i className="bi bi-grid-fill"></i> All Tiers ({totalCards})
              </Link>
              <Link to={`?tier=Beginner&search=${encodeURIComponent(searchQuery || "")}`} className={`tier-filter-btn ${tierFilter === 'Beginner' ? 'active' : ''}`}>
                <i className="bi bi-mortarboard-fill text-danger"></i> Harvard CS50 (Beginner)
              </Link>
              <Link to={`?tier=Intermediate&search=${encodeURIComponent(searchQuery || "")}`} className={`tier-filter-btn ${tierFilter === 'Intermediate' ? 'active' : ''}`}>
                <i className="bi bi-code-slash text-info"></i> MIT (Intermediate)
              </Link>
              <Link to={`?tier=Advanced&search=${encodeURIComponent(searchQuery || "")}`} className={`tier-filter-btn ${tierFilter === 'Advanced' ? 'active' : ''}`}>
                <i className="bi bi-cpu-fill text-warning"></i> Stanford &amp; CMU (Advanced)
              </Link>
            </div>

            {/* Search Input Form */}
            <form method="GET" className="d-flex gap-2" onSubmit={onSearch} key={`${tierFilter}|${searchQuery}`}>
              {tierFilter && (
                <input type="hidden" name="tier" value={tierFilter} />
              )}
              <input type="text" name="search" defaultValue={searchQuery} className="form-control search-input-box" placeholder="Search by title or benchmark..." style={{ minWidth: '250px' }} />
              <button className="btn btn-green-main px-3" type="submit">
                <i className="bi bi-search"></i>
              </button>
              {(searchQuery || tierFilter) && (
                <Link to="/courses_info/" className="btn btn-outline-secondary d-flex align-items-center" title="Clear Filters">
                  <i className="bi bi-x-circle"></i>
                </Link>
              )}
            </form>
          </div>
        </div>

        {/* Tier Cards Grid (Requirement 1) */}
        <div className="row g-4">
          {levelCards.map((card) => (
            <div className="col-12 col-md-6 col-lg-4" key={card.slug}>
              <div className="level-card h-100">

                {/* Top Media Header */}
                <div className="level-card-img-wrap">
                  {card.image ? (
                    <img src={card.image} className="level-card-img" alt={card.title} />
                  ) : (
                    <div className="d-flex align-items-center justify-content-center h-100 text-white">
                      <i className="bi bi-mortarboard display-5" style={{ color: '#d4af37' }}></i>
                    </div>
                  )}

                  {/* Level Pill Overlay */}
                  <div className="level-badge-overlay">
                    <span className="badge" style={{ background: '#064e3b', color: '#d4af37', border: '1.5px solid #d4af37', fontWeight: 800, fontSize: '0.8rem', borderRadius: '20px', padding: '5px 12px' }}>
                      {card.level} Level
                    </span>
                  </div>

                  {/* Level Code Overlay */}
                  {card.level_code && (
                    <div className="level-code-overlay">
                      <span className="badge" style={{ background: 'rgba(0, 0, 0, 0.75)', color: '#ffffff', border: '1px solid rgba(255,255,255,0.4)', fontWeight: 700, fontSize: '0.72rem', borderRadius: '12px', padding: '4px 8px' }}>
                        {card.level_code}
                      </span>
                    </div>
                  )}
                </div>

                {/* Card Body */}
                <div className="p-3 d-flex flex-column justify-content-between flex-grow-1">
                  <div>
                    {/* Course Title & Level Name */}
                    <div className="mb-2">
                      <span className="text-muted small fw-semibold text-uppercase" style={{ letterSpacing: '0.5px' }} ref={important({ 'color': '#047857' })}>
                        {card.course_title}
                      </span>
                      <h5 className="fw-bold mt-1 mb-2" style={{ color: '#064e3b', fontSize: '1.15rem', lineHeight: 1.35 }}>
                        {card.title}
                      </h5>
                    </div>

                    {/* Specific University Benchmark Display (Requirement 1) */}
                    <div className="mb-3">
                      {card.level_is_beginner ? (
                        <div className="benchmark-badge-harvard d-flex align-items-center gap-2">
                          <i className="bi bi-bank fs-6"></i>
                          <div>
                            <div className="fw-bold">Harvard CS50 Benchmark</div>
                            <div className="small text-white-50" style={{ fontSize: '0.72rem' }}>Algorithmic intuition &amp; clean code hygiene</div>
                          </div>
                        </div>
                      ) : card.level_is_intermediate ? (
                        <div className="benchmark-badge-mit d-flex align-items-center gap-2">
                          <i className="bi bi-cpu fs-6"></i>
                          <div>
                            <div className="fw-bold">MIT Logic Benchmark</div>
                            <div className="small" style={{ fontSize: '0.72rem', color: '#bae6fd' }}>Data structures &amp; asymptotic complexity</div>
                          </div>
                        </div>
                      ) : (
                        <div className="benchmark-badge-stanford d-flex align-items-center gap-2">
                          <i className="bi bi-diagram-3-fill fs-6"></i>
                          <div>
                            <div className="fw-bold">Stanford &amp; CMU Benchmark</div>
                            <div className="small text-white-50" style={{ fontSize: '0.72rem' }}>Distributed systems &amp; production AI workflows</div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Telemetry Quick Stats */}
                    <div className="d-flex align-items-center justify-content-between p-2 rounded-3 mb-3" style={{ background: '#f8fafc', border: '1px solid rgba(212, 175, 55, 0.3)' }}>
                      <div className="d-flex align-items-center gap-1 small fw-bold" style={{ color: '#064e3b' }}>
                        <i className="bi bi-people-fill text-success"></i>
                        <span>{card.enrolled_count} Enrolled</span>
                      </div>
                      <div className="d-flex align-items-center gap-1 small fw-bold" style={{ color: '#064e3b' }}>
                        <i className="bi bi-journal-check text-warning"></i>
                        <span>{card.lessons_count} Lessons</span>
                      </div>
                      <div className="d-flex align-items-center gap-1 small fw-bold" style={{ color: '#064e3b' }}>
                        <i className="bi bi-clock-history text-primary"></i>
                        <span>{card.duration}</span>
                      </div>
                    </div>

                    <p className="text-muted small mb-3" style={{ lineHeight: 1.5 }} ref={important({ 'color': '#475569' })}>
                      {card.description}
                    </p>
                  </div>

                  {/* Two Action Buttons (Requirement 1: 'View Course' and 'View Users') */}
                  <div className="pt-3 border-top mt-2" ref={important({ 'border-color': 'rgba(212, 175, 55, 0.25)' })}>
                    <div className="row g-2">
                      <div className="col-6">
                        <Link to={`/admindashboard/level/${card.slug}/course/`} className="btn-view-course w-100" title="View & Manage Curriculum, Lessons, Tasks">
                          <i className="bi bi-layers-half"></i> View Course
                        </Link>
                      </div>
                      <div className="col-6">
                        <Link to={`/admindashboard/level/${card.slug}/users/`} className="btn-view-users w-100" title="View Students Enrolled in this Level">
                          <i className="bi bi-people"></i> View Users
                        </Link>
                      </div>
                    </div>
                  </div>

                </div>

              </div>
            </div>
          ))}
          {levelCards.length === 0 && (
            <div className="col-12">
              <div className="card p-5 text-center shadow-sm" style={{ border: '2px dashed #d4af37', borderRadius: '18px', background: '#ffffff' }}>
                <i className="bi bi-journal-x mb-3 d-block" style={{ fontSize: '3.5rem', color: '#d4af37' }}></i>
                <h4 className="fw-bold" style={{ color: '#064e3b' }}>No Course Levels Found</h4>
                <p className="mb-3 text-muted">Try clearing your filters or create a new course to generate the 3 university tiers.</p>
                <Link to="/add_course/" className="btn btn-green-main d-inline-block">
                  <i className="bi bi-plus-circle"></i> Create New Course
                </Link>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
