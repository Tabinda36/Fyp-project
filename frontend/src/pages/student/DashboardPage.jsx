import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiFetch } from '../../api/client';
import { announceNotificationsChanged, postNotificationRead, useNotificationsChanged } from '../../hooks/notificationEvents';
import { usePageData } from '../../hooks/usePageData';
import { usePageAssets } from '../../hooks/usePageAssets';
import { useFlash } from '../../hooks/useFlash';
import { djDate } from '../../utils/djangoFormat';
import AdminLoader from '../../layouts/AdminLoader';
import css from './DashboardPage.css?raw';

/*
 * Student dashboard (default `{% block content %}` of `student_dashboard/dashboard.html`),
 * redesigned to match the admin console: hero with progress ring, stat cards, course grid,
 * performance + certificate panels. Same data as before (/api/v1/student/dashboard/).
 */

const DEFAULT_AVATAR =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150' viewBox='0 0 24 24' fill='%231B5E20'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z'/%3E%3C/svg%3E";

/** Inline announcement card (replaces the old blocking Bootstrap modal). */
function AnnouncementCard({ notification }) {
  const id = String(notification.id);
  const [removed, setRemoved] = useState(() => localStorage.getItem(`dismissed_notif_${id}`) === 'true');
  const [leaving, setLeaving] = useState(false);

  // Hide straight away, but only remember the dismissal once the server has saved it: otherwise
  // the same unread item keeps coming back from the API and would hide older announcements for good.
  const acknowledge = async () => {
    setLeaving(true);
    const timer = window.setTimeout(() => setRemoved(true), 260);
    try {
      await postNotificationRead(id);
      localStorage.setItem(`dismissed_notif_${id}`, 'true');
      announceNotificationsChanged('dashboard'); // update the bell badge
    } catch (error) {
      window.clearTimeout(timer);
      setRemoved(false);
      setLeaving(false);
      toast.error(error.message || 'Could not mark the announcement as read.');
    }
  };

  if (removed) return null;

  return (
    <section className={`sd-announce${leaving ? ' is-leaving' : ''}`} role="status" aria-live="polite">
      <span className="sd-announce__icon" aria-hidden="true"><i className="bi bi-megaphone-fill"></i></span>
      <div className="sd-announce__body">
        <div className="sd-announce__meta">
          <span className="sd-announce__tag">New announcement</span>
          {notification.category_type_display ? <span className="sd-announce__cat">{notification.category_type_display}</span> : null}
          <span className="sd-announce__time"><i className="bi bi-clock"></i> {djDate(notification.created_at, 'd M Y, h:i A')}</span>
        </div>
        <strong className="sd-announce__title">{notification.subject_heading}</strong>
        <p className="sd-announce__text">{notification.notification_body}</p>
      </div>
      <div className="sd-announce__actions">
        <button type="button" className="sd-btn sd-btn--primary sd-btn--sm" onClick={acknowledge}>
          <i className="bi bi-check2"></i> Got it
        </button>
        <Link to="/notifications/" className="sd-link">All notifications</Link>
      </div>
    </section>
  );
}

export default function DashboardPage() {
  usePageAssets({ css });
  const { data, ready, reload } = usePageData('/student/dashboard/');
  // Read from the bell ("Mark all read"): reload so the announcement card goes away too.
  useNotificationsChanged('dashboard', reload);
  const navigate = useNavigate();
  const { addMessages } = useFlash();
  const [now] = useState(() => new Date());

  if (!ready) return <AdminLoader label="Loading your dashboard" />;

  const { user, generated_courses: generatedCourses = [], suggested_course: suggestedCourse, grade, ai_remarks: aiRemarks } = data;
  const overallProgress = Math.max(0, Math.min(100, Number(data.overall_progress) || 0));
  const certificateUnlocked = data.certificate_unlocked;
  const profile = user?.profile || {};
  const name = profile.full_name || user?.username || 'Student';
  const firstName = name.split(' ')[0];
  const hour = now.getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const lectureHref = (course) => (course.first_lesson_id ? `/daily-lesson/${course.first_lesson_id}/` : `/daily_lesson/?course_id=${course.id}`);
  const continueCourse = generatedCourses[0];
  const totalLectures = generatedCourses.reduce((sum, c) => sum + (Number(c.daily_lessons_count) || 0), 0);

  // <form method="POST" action="{% url 'suggested_courses' %}"> with no `action` field
  // -> the view's default action (start_suggested).
  const generateWithAi = async (event) => {
    event.preventDefault();
    try {
      const res = await apiFetch('/public/suggested-courses/', { method: 'POST', body: { action: 'start_suggested' } });
      addMessages(res?.messages);
      navigate(res?.redirect || '/suggested_courses/');
    } catch (err) {
      addMessages(err?.data?.messages);
      navigate('/suggested_courses/');
    }
  };

  const stats = [
    { label: 'Enrolled courses', value: generatedCourses.length, icon: 'bi-journal-bookmark-fill', tone: 'emerald', to: '/mycourse/' },
    { label: 'Total lectures', value: totalLectures, icon: 'bi-play-circle-fill', tone: 'teal', to: '/mycourse/' },
    { label: 'Current grade', value: grade || '—', icon: 'bi-award-fill', tone: 'gold', to: '/performance/' },
    {
      label: 'Certificate',
      value: certificateUnlocked ? 'Unlocked' : 'Locked',
      icon: certificateUnlocked ? 'bi-patch-check-fill' : 'bi-lock-fill',
      tone: certificateUnlocked ? 'emerald' : 'amber',
      to: '/performance/',
    },
  ];

  const ring = 2 * Math.PI * 52;

  return (
    <div className="sd">
      {data.popup_notification ? <AnnouncementCard key={data.popup_notification.id} notification={data.popup_notification} /> : null}

      {/* Hero */}
      <section className="sd-hero">
        <div className="sd-hero__orb sd-hero__orb--a" aria-hidden="true" />
        <div className="sd-hero__orb sd-hero__orb--b" aria-hidden="true" />
        <div className="sd-hero__main">
          <img src={profile.profile_picture || DEFAULT_AVATAR} className="sd-hero__avatar" alt="" />
          <div className="sd-hero__text">
            <p className="sd-hero__greet">{greeting},</p>
            <h2 className="sd-hero__name">{firstName} <span aria-hidden="true">👋</span></h2>
            <div className="sd-hero__chips">
              {profile.student_id ? <span className="sd-chip sd-chip--gold"><i className="bi bi-person-badge-fill"></i> ID {profile.student_id}</span> : null}
              <span className="sd-chip"><i className="bi bi-envelope"></i> {user?.email}</span>
              {profile.goal ? <span className="sd-chip"><i className="bi bi-bullseye"></i> {profile.goal}</span> : null}
            </div>
            <div className="sd-hero__actions">
              {continueCourse ? (
                <Link to={lectureHref(continueCourse)} className="sd-btn sd-btn--gold"><i className="bi bi-play-fill"></i> Continue learning</Link>
              ) : null}
              <Link to="/generate_course/" className="sd-btn sd-btn--ghost"><i className="bi bi-mortarboard-fill"></i> Browse university tiers</Link>
            </div>
          </div>
        </div>

        <div className="sd-ring" role="img" aria-label={`Overall completion ${overallProgress}%`}>
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <defs>
              <linearGradient id="sdRingGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#f3d880" />
                <stop offset="100%" stopColor="#34d399" />
              </linearGradient>
            </defs>
            <circle cx="60" cy="60" r="52" className="sd-ring__track" />
            <circle cx="60" cy="60" r="52" className="sd-ring__bar" strokeDasharray={ring} strokeDashoffset={ring * (1 - overallProgress / 100)} />
          </svg>
          <div className="sd-ring__label">
            <strong>{overallProgress}%</strong>
            <small>Completed</small>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="sd-stats" aria-label="Your progress at a glance">
        {stats.map((s, i) => (
          <Link key={s.label} to={s.to} className={`sd-stat sd-stat--${s.tone}`} style={{ '--i': i }}>
            <span className="sd-stat__icon"><i className={`bi ${s.icon}`}></i></span>
            <span className="sd-stat__body">
              <strong>{s.value}</strong>
              <small>{s.label}</small>
            </span>
          </Link>
        ))}
      </section>

      <div className="sd-columns">
        {/* Courses */}
        <section className="sd-panel">
          <header className="sd-panel__head">
            <div>
              <p className="sd-panel__eyebrow">Learning</p>
              <h3 className="sd-panel__title">My courses</h3>
            </div>
            {generatedCourses.length ? <Link to="/mycourse/" className="sd-link">View all <i className="bi bi-arrow-right"></i></Link> : null}
          </header>

          {generatedCourses.length ? (
            <div className="sd-courses">
              {generatedCourses.map((course, i) => {
                const title = course.admin_course?.title || 'Course';
                const img = course.image || course.admin_course?.image;
                return (
                  <article className="sd-course" key={course.id} style={{ '--i': i }}>
                    <div className="sd-course__media">
                      {img ? <img src={img} alt="" /> : <div className="sd-course__placeholder"><i className="bi bi-journal-code"></i></div>}
                      {course.admin_course?.course_code ? <span className="sd-course__code">{course.admin_course.course_code}</span> : null}
                      {course.tier_display ? <span className="sd-course__tier">{course.tier_display}</span> : null}
                    </div>
                    <div className="sd-course__body">
                      <h4 className="sd-course__title" title={title}>{title}</h4>
                      <div className="sd-course__meta">
                        <span><i className="bi bi-speedometer2"></i> {course.pace || 'Standard'}</span>
                        <span><i className="bi bi-play-circle"></i> {course.daily_lessons_count} lectures</span>
                      </div>
                      <div className="sd-course__actions">
                        <Link to={`/course_content/?course_id=${course.id}`} className="sd-btn sd-btn--soft sd-btn--sm"><i className="bi bi-book-half"></i> Content</Link>
                        <Link to={lectureHref(course)} className="sd-btn sd-btn--primary sd-btn--sm"><i className="bi bi-play-circle-fill"></i> Lecture</Link>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : suggestedCourse ? (
            <div className="sd-suggest">
              {suggestedCourse.image ? <img src={suggestedCourse.image} alt="" className="sd-suggest__img" /> : null}
              <div className="sd-suggest__body">
                <div className="sd-suggest__tags">
                  <span className="sd-chip sd-chip--dark"><i className="bi bi-star-fill"></i> Suggested from your assessment</span>
                  {suggestedCourse.course_code ? <span className="sd-chip sd-chip--gold">ID {suggestedCourse.course_code}</span> : null}
                </div>
                <h4>{suggestedCourse.title}</h4>
                <p>{suggestedCourse.description_display}</p>
                <div className="sd-suggest__actions">
                  <form method="POST" action="/suggested_courses/" onSubmit={generateWithAi}>
                    <button type="submit" className="sd-btn sd-btn--primary"><i className="bi bi-stars"></i> Generate course with AI</button>
                  </form>
                  <Link to="/suggested_courses/" className="sd-btn sd-btn--soft">View full details</Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="sd-empty">
              <span className="sd-empty__icon"><i className="bi bi-book-half"></i></span>
              <strong>No courses yet</strong>
              <small>Pick a university tier to generate your first personalised course.</small>
              <Link to="/generate_course/" className="sd-btn sd-btn--primary"><i className="bi bi-mortarboard-fill"></i> Browse university tiers</Link>
            </div>
          )}
        </section>

        {/* Right column */}
        <div className="sd-side">
          <section className="sd-panel">
            <header className="sd-panel__head">
              <div>
                <p className="sd-panel__eyebrow">Progress</p>
                <h3 className="sd-panel__title">Performance</h3>
              </div>
              <span className={`sd-grade${grade ? '' : ' is-empty'}`}>{grade ? `Grade ${grade}` : 'No grade yet'}</span>
            </header>

            <div className="sd-progress">
              <div className="sd-progress__row">
                <span>Overall completion</span>
                <strong>{overallProgress}%</strong>
              </div>
              <div className="sd-progress__track" role="progressbar" aria-label="Overall completion" aria-valuenow={overallProgress} aria-valuemin="0" aria-valuemax="100">
                <span className="sd-progress__fill" style={{ width: `${overallProgress}%` }} />
              </div>
            </div>

            <div className="sd-remarks">
              <span className="sd-remarks__icon"><i className="bi bi-robot"></i></span>
              <div>
                <strong>AI performance remarks</strong>
                <p>{aiRemarks ? `“${aiRemarks}”` : 'No AI remarks yet. Complete daily lessons and quizzes to get your evaluation.'}</p>
              </div>
            </div>

            <Link to="/performance/" className="sd-btn sd-btn--soft sd-btn--block">View detailed analytics <i className="bi bi-arrow-right"></i></Link>
          </section>

          <section className={`sd-panel sd-cert ${certificateUnlocked ? 'is-unlocked' : 'is-locked'}`}>
            <header className="sd-panel__head">
              <div>
                <p className="sd-panel__eyebrow">Achievement</p>
                <h3 className="sd-panel__title">Completion certificate</h3>
              </div>
              <span className="sd-cert__status">
                <i className={`bi ${certificateUnlocked ? 'bi-unlock-fill' : 'bi-lock-fill'}`}></i> {certificateUnlocked ? 'Unlocked' : 'Locked'}
              </span>
            </header>

            {certificateUnlocked ? (
              <>
                <p className="sd-cert__text">Congratulations! You met all course requirements. Your official certificate is ready.</p>
                <a href={`/certificate/${data.active_course?.id ?? ''}/`} target="_blank" rel="noreferrer" className="sd-btn sd-btn--gold sd-btn--block">
                  <i className="bi bi-trophy-fill"></i> View &amp; download certificate
                </a>
              </>
            ) : (
              <>
                <p className="sd-cert__text">Complete these requirements to unlock your certificate:</p>
                <ul className="sd-cert__list">
                  <li><i className="bi bi-camera-video"></i> Minimum 60% watch time</li>
                  <li><i className="bi bi-file-earmark-check"></i> All assignments submitted</li>
                  <li><i className="bi bi-patch-question"></i> All quizzes attempted</li>
                  <li><i className="bi bi-bar-chart"></i> Overall score of at least 35%</li>
                </ul>
                <button type="button" className="sd-btn sd-btn--locked sd-btn--block" disabled>
                  <i className="bi bi-lock-fill"></i> Certificate locked
                </button>
              </>
            )}
          </section>
        </div>
      </div>

    </div>
  );
}
