import AdminLoader from '../../layouts/AdminLoader';
import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import NotFoundPage from '../NotFoundPage';
import { djDate, dflt, truncatechars, truncatewords } from '../../utils/djangoFormat';
import css from './MyCoursePage.css?raw';

/*
 * My Courses (`student_dashboard/mycourse.html`), redesigned in the dashboard style.
 *   /mycourse/            -> view `mycourse`        (GET /api/v1/learning/mycourse/?course_id=&tab=)
 *   /course/:courseId/    -> view `course_detail`   (GET /api/v1/learning/course/<id>/) — same template, less context
 */

const HASH_MAP = {
  'tab-content': '#course-content',
  'tab-lessons': '#lesson-plan',
  'tab-assignment': '#assignments',
  'tab-quiz': '#quizzes',
  'tab-overview': '#overview',
};

// Initial tab: server `active_tab`, then the URL hash overrides it (DOMContentLoaded handler of the template).
function initialTab(activeTab) {
  const hash = window.location.hash;
  if (hash === '#lesson-plan' || hash === '#lessons') return 'tab-lessons';
  if (hash === '#assignments' || hash === '#assignment') return 'tab-assignment';
  if (hash === '#quizzes' || hash === '#quiz') return 'tab-quiz';
  if (hash === '#overview' || hash === '#certificate') return 'tab-overview';
  if (hash === '#course-content' || hash === '#content') return 'tab-content';
  return activeTab ? `tab-${activeTab}` : null;
}

// Django renders None as "None" in `{{ }}`; the course_detail view simply omits the variable (-> '').
const out = (v) => (v === null || v === undefined ? '' : String(v));

const quizTone = (pct) => (pct >= 80 ? 'good' : pct >= 60 ? 'warn' : 'bad');

export function MyCoursePage() {
  const { search } = useLocation();
  const query = Object.fromEntries(new URLSearchParams(search));
  const { data, ready } = usePageData('/learning/mycourse/', { course_id: query.course_id, tab: query.tab });
  usePageAssets({ css });
  if (!ready) return <AdminLoader />;
  return <MyCourseContent key={`${data.active_course?.id}-${data.active_tab}-${search}`} data={data} />;
}

export function CourseDetailPage() {
  const { courseId } = useParams();
  const { data, ready, notFound } = usePageData(`/learning/course/${courseId}/`);
  usePageAssets({ css });
  if (notFound || !/^[0-9]+$/.test(courseId)) return <NotFoundPage />;
  if (!ready) return <AdminLoader />;
  return <MyCourseContent key={courseId} data={data} />;
}

function SectionHead({ icon, title, sub, children }) {
  return (
    <header className="smc-section-head">
      <div>
        <h3 className="smc-section-title"><i className={`bi ${icon}`}></i> {title}</h3>
        <p className="smc-section-sub">{sub}</p>
      </div>
      {children ? <div className="smc-section-actions">{children}</div> : null}
    </header>
  );
}

function Empty({ icon, title, text, children }) {
  return (
    <div className="smc-empty">
      <span className="smc-empty__icon"><i className={`bi ${icon}`}></i></span>
      <strong>{title}</strong>
      {text ? <small>{text}</small> : null}
      {children}
    </div>
  );
}

function MyCourseContent({ data }) {
  const {
    active_course: activeCourse,
    user_courses: userCourses = [],
    lessons = [],
    content_topics: contentTopics = [],
    today_lesson: todayLesson,
    assignment_submissions: assignmentSubmissions = [],
    quiz_submissions: quizSubmissions = [],
    progress_percentage: progressPercentage,
    certificate,
    active_tab: activeTab,
  } = data;

  const [tab, setTab] = useState(() => initialTab(activeTab));

  // Arriving with a section hash (e.g. the dashboard's "Content" button -> #course-content):
  // bring the tabs + that section into view instead of leaving the page at the hero.
  useEffect(() => {
    if (!Object.values(HASH_MAP).includes(window.location.hash)) return;
    document.getElementById('courseHorizontalNavbar')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const switchToTab = (tabId) => {
    setTab(tabId);
    if (HASH_MAP[tabId] && window.history.replaceState) {
      // keep React Router's history state; only the hash changes (as in the template)
      window.history.replaceState(window.history.state, '', HASH_MAP[tabId]);
    }
  };

  const onNavClick = (tabId) => (e) => {
    e.preventDefault();
    switchToTab(tabId);
  };

  const progressNum = Math.max(0, Math.min(100, Number(progressPercentage) || 0));
  // Never show more than 100% (the server's weighted sum can overshoot with quiz retakes).
  const progress = Number(progressPercentage) > 100 ? '100' : out(progressPercentage);
  const ac = activeCourse?.admin_course || {};
  const certUnlocked = Boolean(certificate && certificate.is_unlocked);
  const completedCount = lessons.filter((l) => l.is_completed).length;

  if (!activeCourse) {
    /* Fallback if student has not enrolled in any course yet */
    return (
      <div className="smc">
        <section className="smc-panel">
          <Empty
            icon="bi-mortarboard"
            title="No course enrolled yet"
            text="Pick from our curated Harvard, MIT and Stanford benchmarked courses to begin your personalized learning path."
          >
            <div className="smc-row smc-row--center">
              <Link to="/suggested_courses/" className="smc-btn smc-btn--primary"><i className="bi bi-stars"></i> Choose your course</Link>
              <Link to="/generate_course/" className="smc-btn smc-btn--soft"><i className="bi bi-plus-circle"></i> Browse catalog</Link>
            </div>
          </Empty>
        </section>
      </div>
    );
  }

  const tabs = [
    { id: 'tab-content', href: '#course-content', icon: 'bi-book-half', label: 'Course content', count: contentTopics.length },
    { id: 'tab-lessons', href: '#lesson-plan', icon: 'bi-calendar3', label: 'Lesson plan', count: lessons.length },
    { id: 'tab-assignment', href: '#assignments', icon: 'bi-file-earmark-code', label: 'Assignments', count: assignmentSubmissions.length },
    { id: 'tab-quiz', href: '#quizzes', icon: 'bi-patch-question', label: 'Quizzes', count: quizSubmissions.length },
    { id: 'tab-overview', href: '#overview', icon: 'bi-award', label: 'Overview & certificate' },
  ];

  return (
    <div className="smc">
      {/* 1. COURSE HERO */}
      <section className="smc-hero">
        <div className="smc-hero__orb" aria-hidden="true" />
        <div className="smc-hero__media">
          {ac.image ? <img src={ac.image} alt="" /> : <i className="bi bi-mortarboard-fill"></i>}
        </div>
        <div className="smc-hero__text">
          <div className="smc-chips">
            {ac.course_code ? <span className="smc-chip smc-chip--gold"><i className="bi bi-tag-fill"></i> {ac.course_code}</span> : null}
            <span className="smc-chip"><i className="bi bi-mortarboard-fill"></i> {dflt(activeCourse.course_level?.benchmark, 'Harvard / MIT / Stanford Standard')}</span>
            <span className="smc-chip"><i className="bi bi-clock-history"></i> {dflt(activeCourse.pace, 'Standard Pace')}</span>
          </div>
          <h2 className="smc-hero__title">{ac.title}</h2>
          <p className="smc-hero__desc">
            {truncatewords(dflt(dflt(activeCourse.objective, ac.description), 'Personalized AI-powered curriculum tailored to your learning goals.'), 30)}
          </p>
        </div>
        <div className="smc-hero__progress">
          <div className="smc-progress-row"><span>Overall progress</span><strong>{progress}%</strong></div>
          <div className="smc-progress smc-progress--hero" role="progressbar" aria-label="Overall progress" aria-valuenow={progressNum} aria-valuemin="0" aria-valuemax="100">
            <span style={{ width: `${progressNum}%` }} />
          </div>
          <small>{completedCount} of {lessons.length} lessons completed</small>
        </div>
      </section>

      {/* Course switcher (when the student chose more than one course) */}
      {userCourses.length > 1 ? (
        <section className="smc-switcher" aria-label="My enrolled courses">
          <p className="smc-eyebrow">My enrolled courses ({userCourses.length})</p>
          <div className="smc-switcher__list">
            {userCourses.map((uc) => {
              const active = uc.id === activeCourse.id;
              const img = uc.image || uc.admin_course?.image;
              return (
                <Link
                  key={uc.id}
                  to={`?course_id=${uc.id}&tab=${out(activeTab)}`}
                  className={`smc-switch${active ? ' is-active' : ''}`}
                  aria-current={active ? 'true' : undefined}
                >
                  <span className="smc-switch__thumb">{img ? <img src={img} alt="" /> : <i className="bi bi-journal-code"></i>}</span>
                  <span className="smc-switch__text">
                    <strong>{uc.admin_course?.title}</strong>
                    <small>{uc.admin_course?.course_code || uc.tier_display || 'Course'}</small>
                  </span>
                  {active ? <i className="bi bi-check-circle-fill smc-switch__check"></i> : null}
                </Link>
              );
            })}
          </div>
        </section>
      ) : null}

      {/* 2. PILL TABS */}
      <nav className="smc-tabs" id="courseHorizontalNavbar" role="tablist" aria-label="Course sections">
        {tabs.map((t) => (
          <a
            key={t.id}
            className={`smc-tab${tab === t.id ? ' is-active' : ''}`}
            href={t.href}
            role="tab"
            aria-selected={tab === t.id}
            data-tab-target={t.id}
            onClick={onNavClick(t.id)}
          >
            <i className={`bi ${t.icon}`}></i>
            <span>{t.label}</span>
            {t.count ? <span className="smc-tab__count">{t.count}</span> : null}
          </a>
        ))}
      </nav>

      {/* 3. TAB PANES */}
      <section className="smc-panel" id="courseTabContentArea">

        {/* ================= COURSE CONTENT ================= */}
        <div className={tab === 'tab-content' ? 'smc-pane' : 'd-none'} id="pane-tab-content">
          <SectionHead icon="bi-book-half" title="Course syllabus & learning modules" sub="Chapter outlines, foundational topics and learning objectives.">
            <span className="smc-tag smc-tag--gold"><i className="bi bi-layers"></i> {contentTopics.length} topics</span>
            <span className="smc-tag"><i className="bi bi-play-circle"></i> {lessons.length} lectures</span>
          </SectionHead>

          {contentTopics.length ? (
            // Owner-requested: topics in series (one row each, divided by a horizontal line)
            // with all of their bullet points, instead of a grid of cards.
            <ol className="smc-topic-series">
              {contentTopics.map((topic, i) => (
                <li className="smc-topic-row" key={i} style={{ '--i': i }}>
                  <span className="smc-topic__num">{i + 1}</span>
                  <div className="smc-topic-row__body">
                    <div className="smc-topic-row__head">
                      <h4 className="smc-topic__title">{topic.label}</h4>
                      <span className="smc-tag">Unit {i + 1}</span>
                    </div>
                    {topic.study_bullets.length ? (
                      <ul className="smc-bullets smc-bullets--series">
                        {topic.study_bullets.map((bullet, j) => (
                          <li key={j}><i className="bi bi-check2"></i><span>{bullet}</span></li>
                        ))}
                      </ul>
                    ) : topic.summary ? (
                      <p className="smc-muted mb-0">{topic.summary}</p>
                    ) : (
                      <p className="smc-muted mb-0">Comprehensive study plan and hands-on exercises tailored to university standards.</p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <Empty icon="bi-journal-x" title="Syllabus modules are being prepared" text="You can begin directly with your daily lectures in the Lesson plan tab.">
              <button type="button" className="smc-btn smc-btn--primary" onClick={() => switchToTab('tab-lessons')}>
                <i className="bi bi-calendar3"></i> Open lesson plan
              </button>
            </Empty>
          )}
        </div>

        {/* ================= LESSON PLAN ================= */}
        <div className={tab === 'tab-lessons' ? 'smc-pane' : 'd-none'} id="pane-tab-lessons">
          <SectionHead icon="bi-calendar3" title="Daily lesson roadmap" sub="Follow your day-by-day schedule with Inara, your AI teacher.">
            {todayLesson && (
              <Link to={`/daily-lesson/${todayLesson.id}/`} className="smc-btn smc-btn--primary">
                <i className="bi bi-play-circle-fill"></i> Resume day {todayLesson.day_number}
              </Link>
            )}
          </SectionHead>

          {lessons.length ? (
            <ol className="smc-lessons">
              {lessons.map((l) => {
                const state = l.is_completed ? 'done' : l.is_unlocked ? 'open' : 'locked';
                const current = todayLesson && todayLesson.id === l.id;
                return (
                  <li className={`smc-lesson is-${state}${current ? ' is-current' : ''}`} key={l.id}>
                    <span className="smc-lesson__status" aria-hidden="true">
                      <i className={`bi ${state === 'done' ? 'bi-check-lg' : state === 'open' ? 'bi-play-fill' : 'bi-lock-fill'}`}></i>
                    </span>
                    <div className="smc-lesson__main">
                      <div className="smc-lesson__top">
                        <span className="smc-lesson__day">Day {l.day_number}</span>
                        <span className={`smc-state smc-state--${state}`}>
                          {state === 'done' ? 'Completed' : state === 'open' ? (current ? 'Current' : 'In progress') : 'Locked'}
                        </span>
                      </div>
                      <h4 className="smc-lesson__title">{l.title}</h4>
                      <p className="smc-lesson__meta">
                        <i className="bi bi-stopwatch"></i> Watch time <strong>{dflt(l.watch_time_seconds, 0)}s / {dflt(l.required_watch_seconds, 180)}s</strong>
                      </p>
                    </div>
                    <div className="smc-lesson__actions">
                      <Link to={`/daily-lesson/${l.id}/`} className="smc-btn smc-btn--primary smc-btn--sm"><i className="bi bi-play-circle-fill"></i> Lecture</Link>
                      <Link to={`/assignment/?lesson_id=${l.id}`} className="smc-btn smc-btn--soft smc-btn--sm" title="Go to assignment"><i className="bi bi-pencil-square"></i> Assignment</Link>
                      <Link to={`/quiz/?lesson_id=${l.id}`} className="smc-btn smc-btn--soft smc-btn--sm" title="Go to quiz"><i className="bi bi-patch-question"></i> Quiz</Link>
                      <a href={`/lesson/${l.id}/download-ppt/`} className="smc-btn smc-btn--outline smc-btn--sm" title="Download lecture slides (PPT)"><i className="bi bi-file-earmark-ppt-fill"></i> PPT</a>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : (
            <Empty icon="bi-calendar-x" title="No daily lectures found for this course" />
          )}
        </div>

        {/* ================= ASSIGNMENTS ================= */}
        <div className={tab === 'tab-assignment' ? 'smc-pane' : 'd-none'} id="pane-tab-assignment">
          <SectionHead icon="bi-file-earmark-code" title="Hands-on assignments" sub="Practical tasks, coding challenges and AI evaluations.">
            {todayLesson && (
              <Link to={`/assignment/?lesson_id=${todayLesson.id}`} className="smc-btn smc-btn--primary">
                <i className="bi bi-pencil-square"></i> Open workspace (day {todayLesson.day_number})
              </Link>
            )}
          </SectionHead>

          {todayLesson && (
            <article className="smc-challenge">
              <div className="smc-challenge__head">
                <span className="smc-chip smc-chip--dark">Active challenge · Day {todayLesson.day_number} · {todayLesson.title}</span>
                <span className="smc-muted"><i className="bi bi-clock"></i> Deadline: <strong>{dflt(djDate(todayLesson.deadline, 'd M Y, h:i A'), '2 Days from start')}</strong></span>
              </div>
              <h4 className="smc-sub-title">Assignment prompt</h4>
              <div className="smc-prompt" dangerouslySetInnerHTML={{ __html: todayLesson.assignment_question_html }} />
              <div className="smc-row smc-row--end">
                <Link to={`/assignment/?lesson_id=${todayLesson.id}`} className="smc-btn smc-btn--primary">
                  <i className="bi bi-upload"></i> Submit solution &amp; run AI rubric
                </Link>
              </div>
            </article>
          )}

          <h4 className="smc-sub-title"><i className="bi bi-clock-history"></i> Submission history</h4>
          {assignmentSubmissions.length ? (
            <div className="smc-table-wrap">
              <table className="smc-table">
                <thead>
                  <tr>
                    <th>Lesson / day</th>
                    <th>Submission preview</th>
                    <th>Marks</th>
                    <th>AI evaluation</th>
                    <th>Date</th>
                    <th className="smc-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {assignmentSubmissions.map((sub) => (
                    <tr key={sub.id}>
                      <td data-label="Lesson"><strong className="smc-strong">Day {dflt(sub.lesson?.day_number, '-')}: {dflt(sub.lesson?.title, 'Assignment')}</strong></td>
                      <td data-label="Preview"><span className="smc-trunc">{truncatechars(dflt(sub.submitted_answer, 'File Submission'), 60)}</span></td>
                      <td data-label="Marks"><span className="smc-pill smc-pill--good">{sub.marks || dflt(sub.score, '')}/{dflt(sub.total_marks, 10)}</span></td>
                      <td data-label="AI evaluation"><span className="smc-muted">{truncatechars(dflt(sub.ai_feedback, 'Evaluated against rubric'), 45)}</span></td>
                      <td data-label="Date"><span className="smc-muted">{djDate(sub.submitted_at, 'd M Y, h:i A')}</span></td>
                      <td className="smc-right" data-label="">
                        <a href={`/download-assignment-pdf/${sub.id}/`} className="smc-btn smc-btn--soft smc-btn--sm"><i className="bi bi-file-earmark-pdf"></i> PDF</a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty icon="bi-inbox" title="No assignment submissions yet" text="Open the assignment workspace above to complete your first task." />
          )}
        </div>

        {/* ================= QUIZZES ================= */}
        <div className={tab === 'tab-quiz' ? 'smc-pane' : 'd-none'} id="pane-tab-quiz">
          <SectionHead icon="bi-patch-question" title="Diagnostic concept quizzes" sub="Test your mastery with instant scoring and detailed AI explanations.">
            {todayLesson && (
              <Link to={`/quiz/?lesson_id=${todayLesson.id}`} className="smc-btn smc-btn--primary">
                <i className="bi bi-patch-check-fill"></i> Take today&apos;s quiz (day {todayLesson.day_number})
              </Link>
            )}
          </SectionHead>

          {quizSubmissions.length ? (
            <div className="smc-table-wrap">
              <table className="smc-table">
                <thead>
                  <tr>
                    <th>Lesson / day</th>
                    <th>Score</th>
                    <th>Percentage</th>
                    <th>Date completed</th>
                    <th className="smc-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {quizSubmissions.map((q) => (
                    <tr key={q.id}>
                      <td data-label="Lesson"><strong className="smc-strong">Day {dflt(q.lesson?.day_number, '-')}: {dflt(q.lesson?.title, 'Quiz')}</strong></td>
                      <td data-label="Score"><span className="smc-pill smc-pill--none">{q.score} / {q.total_questions}</span></td>
                      <td data-label="Percentage"><span className={`smc-pill smc-pill--${quizTone(q.percentage)}`}>{q.percentage}%</span></td>
                      <td data-label="Date"><span className="smc-muted">{djDate(q.submitted_at, 'd M Y, h:i A')}</span></td>
                      <td className="smc-right" data-label="">
                        <Link to={`/quiz/?lesson_id=${out(q.lesson?.id)}`} className="smc-btn smc-btn--soft smc-btn--sm"><i className="bi bi-eye"></i> Review</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty icon="bi-question-circle" title="No quiz attempts recorded yet" text="Take today's quiz to assess your learning." />
          )}
        </div>

        {/* ================= OVERVIEW & CERTIFICATE ================= */}
        <div className={tab === 'tab-overview' ? 'smc-pane' : 'd-none'} id="pane-tab-overview">
          <SectionHead icon="bi-award" title="Course overview & official certificate" sub="Your overall standing and verified completion credentials." />

          <div className="smc-overview">
            <article className="smc-card">
              <div className="smc-card__head">
                <span className="smc-card__thumb">{ac.image ? <img src={ac.image} alt="" /> : <i className="bi bi-mortarboard-fill"></i>}</span>
                <div>
                  <h4 className="smc-card__title">{ac.title}</h4>
                  <span className="smc-tag smc-tag--dark">{dflt(activeCourse.course_level?.benchmark, 'Harvard Standard')}</span>
                </div>
              </div>
              <p className="smc-muted">{dflt(activeCourse.objective, ac.description)}</p>
              <div className="smc-box">
                <div className="smc-progress-row"><span>Weighted course completion</span><strong>{progress}%</strong></div>
                <div className="smc-progress" role="progressbar" aria-label="Weighted course completion" aria-valuenow={progressNum} aria-valuemin="0" aria-valuemax="100">
                  <span style={{ width: `${progressNum}%` }} />
                </div>
                <div className="smc-weights">
                  <span>Watch time 20%</span>
                  <span>Assignments 40%</span>
                  <span>Quizzes 40%</span>
                </div>
              </div>
              <div className="smc-row">
                <Link to={`/course_content/?course_id=${activeCourse.id}`} className="smc-btn smc-btn--soft smc-btn--grow"><i className="bi bi-book"></i> Full syllabus</Link>
                <Link to={`/daily_lesson/?course_id=${activeCourse.id}`} className="smc-btn smc-btn--primary smc-btn--grow"><i className="bi bi-play-circle"></i> Continue learning</Link>
              </div>
            </article>

            <article className={`smc-card smc-cert ${certUnlocked ? 'is-unlocked' : 'is-locked'}`}>
              <span className="smc-cert__icon"><i className="bi bi-patch-check-fill"></i></span>
              <h4 className="smc-card__title">Course completion certificate</h4>
              <p className="smc-muted">Official ALVIX adaptive learning certification, verified with QR credentials.</p>

              {certUnlocked ? (
                <div className="smc-cert__msg is-good"><strong>🎉 Congratulations!</strong> You fulfilled all course requirements and earned your verified credential.</div>
              ) : (
                <ul className="smc-cert__reqs">
                  <li><i className="bi bi-camera-video"></i> Complete all daily video lectures (180s minimum watch time each)</li>
                  <li><i className="bi bi-file-earmark-check"></i> Submit all course assignments with a passing evaluation</li>
                  <li><i className="bi bi-patch-question"></i> Pass all diagnostic quizzes with at least 70%</li>
                </ul>
              )}

              {certUnlocked ? (
                <Link to={`/certificate/${activeCourse.id}/`} target="_blank" className="smc-btn smc-btn--gold smc-btn--block">
                  <i className="bi bi-award-fill"></i> View &amp; download certificate
                </Link>
              ) : (
                <Link to={`/certificate/${activeCourse.id}/`} className="smc-btn smc-btn--soft smc-btn--block">
                  <i className="bi bi-lock-fill"></i> Check certificate status
                </Link>
              )}
            </article>
          </div>
        </div>
      </section>
    </div>
  );
}
