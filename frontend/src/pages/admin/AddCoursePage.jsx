import toast from 'react-hot-toast';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { useFlash } from '../../hooks/useFlash';
import { apiFetch } from '../../api/client';
import { ICONS_1113, googleFont } from '../../cdn';
import css from './AddCoursePage.css?raw';

/* Port of admin_db/add_course.html (POST multipart title, image, description). */

const FONT = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Poppins:wght@600;700;800');

export default function AddCoursePage() {
  usePageAssets({ links: [ICONS_1113, FONT], css });
  const navigate = useNavigate();
  const { addMessages } = useFlash();
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (busy) return; // AI tier generation is slow: block double submits (they create duplicate courses)
    const form = e.currentTarget;
    setBusy(true);
    const loading = toast.loading('Publishing course and generating the 3 tiers… this can take a minute.');
    try {
      const res = await apiFetch('/admin-courses/courses/', { method: 'POST', body: new FormData(form) });
      toast.dismiss(loading);
      addMessages(res.messages);
      if (res.redirect) navigate(res.redirect);
    } catch (err) {
      toast.dismiss(loading);
      if (err.status === 401 || err.status === 403) {
        navigate(`/login/?next=${encodeURIComponent('/add_course/')}`);
        return;
      }
      // The template view re-rendered the blank form when no title was given.
      if (err.status === 400) {
        form.reset();
        toast.error(err.data?.error || 'Please enter a course title.');
      } else {
        toast.error(!err.status || err.status >= 500 ? 'Server error while creating the course. Please try again.' : (err.data?.error || 'Could not create the course.'));
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container-fluid py-4">
      <div className="content-wrapper">

        {/* Top Breadcrumb & Heading */}
        <div className="d-flex align-items-center justify-content-between mb-4">
          <div>
            <Link to="/courses_info/" className="text-decoration-none small fw-bold text-success mb-1 d-inline-block">
              <i className="bi bi-arrow-left"></i> Back to Courses
            </Link>
            <h3 className="fw-bold mb-0" style={{ color: '#064e3b' }}>Add Master Course</h3>
          </div>
          <span className="badge" style={{ background: '#064e3b', color: '#d4af37', border: '1.5px solid #d4af37', padding: '6px 14px', borderRadius: '20px', fontWeight: 700 }}>
            ✨ Auto 3-Tier Generation
          </span>
        </div>

        {/* Add Course Form Card */}
        <div className="form-card p-4 p-md-5">
          <form method="POST" encType="multipart/form-data" onSubmit={onSubmit}>

            <div className="row g-4">
              {/* Course Title */}
              <div className="col-md-8">
                <label htmlFor="course_title" className="form-label">Course Title / Master Topic</label>
                <input type="text" className="form-control" id="course_title" name="title" placeholder="e.g., Python Programming & Software Engineering" required />
                <div className="form-text small text-muted">
                  Entering a master title will automatically generate the 3 university benchmark tiers in the database.
                </div>
              </div>

              {/* Course Cover Image / Thumbnail */}
              <div className="col-md-4">
                <label htmlFor="course_image" className="form-label">Course Cover Thumbnail</label>
                <input type="file" className="form-control" id="course_image" name="image" accept="image/*" />
                <div className="form-text small text-muted">Recommended: 16:9 banner image.</div>
              </div>

              {/* Short Description */}
              <div className="col-12">
                <label htmlFor="course_description" className="form-label">Master Course Description &amp; Scope</label>
                <textarea className="form-control" id="course_description" name="description" rows="4" placeholder="Describe the domain scope, foundational objectives, and production application goals of this course." required></textarea>
              </div>

              {/* Automatic University Tiers Preview Box */}
              <div className="col-12">
                <div className="p-3 rounded-3" style={{ background: 'rgba(212, 175, 55, 0.08)', border: '1.5px solid #d4af37' }}>
                  <h6 className="fw-bold mb-2" style={{ color: '#064e3b' }}>
                    <i className="bi bi-mortarboard-fill text-warning me-1"></i>
                    {' '}Automatic University Benchmark Generation:
                  </h6>
                  <p className="small text-muted mb-3">
                    When you click <strong>&quot;Publish Course&quot;</strong>, ALVIX will automatically construct 3 distinct tier cards and pre-generate their complete university canonical curricula, lab challenges, and diagnostic quizzes directly in the database:
                  </p>

                  <div className="row g-2">
                    <div className="col-md-4">
                      <div className="tier-preview-box h-100">
                        <div className="d-flex align-items-center justify-content-between mb-1">
                          <span className="fw-bold" style={{ color: '#A51C30' }}>Beginner Level</span>
                          <span className="badge bg-danger-subtle text-danger small">Tier 1</span>
                        </div>
                        <div className="small fw-semibold text-dark">Harvard University / CS50 Philosophy</div>
                        <div className="text-muted" style={{ fontSize: '0.78rem' }}>Computational thinking, algorithmic intuition &amp; clean architecture.</div>
                      </div>
                    </div>
                    <div className="col-md-4">
                      <div className="tier-preview-box h-100">
                        <div className="d-flex align-items-center justify-content-between mb-1">
                          <span className="fw-bold" style={{ color: '#0284c7' }}>Intermediate Level</span>
                          <span className="badge bg-info-subtle text-info small">Tier 2</span>
                        </div>
                        <div className="small fw-semibold text-dark">MIT / Data Structures &amp; Logic</div>
                        <div className="text-muted" style={{ fontSize: '0.78rem' }}>Abstract data types, asymptotic efficiency &amp; algorithmic design.</div>
                      </div>
                    </div>
                    <div className="col-md-4">
                      <div className="tier-preview-box h-100">
                        <div className="d-flex align-items-center justify-content-between mb-1">
                          <span className="fw-bold" style={{ color: '#8C1515' }}>Advanced Level</span>
                          <span className="badge bg-warning-subtle text-warning small">Tier 3</span>
                        </div>
                        <div className="small fw-semibold text-dark">Stanford &amp; CMU / Systems &amp; AI</div>
                        <div className="text-muted" style={{ fontSize: '0.78rem' }}>Distributed systems, asynchronous concurrency &amp; production AI integration.</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Form Action Buttons */}
              <div className="col-12 d-flex justify-content-end align-items-center gap-3 mt-4">
                <Link to="/courses_info/" className="btn btn-outline-secondary px-4 py-2" style={{ borderRadius: '10px', fontWeight: 600 }}>
                  Cancel
                </Link>
                <button type="submit" className="btn-submit-green" disabled={busy} aria-busy={busy}>
                  {busy ? (
                    <><span className="spinner-border spinner-border-sm me-2" aria-hidden="true"></span> Generating tiers…</>
                  ) : (
                    <><i className="bi bi-cloud-arrow-up-fill me-1"></i> Save &amp; Generate University Tiers</>
                  )}
                </button>
              </div>
            </div>
          </form>
        </div>

      </div>
    </div>
  );
}
