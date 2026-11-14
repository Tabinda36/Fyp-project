import AdminLoader from '../../layouts/AdminLoader';
import { Link } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import css from './PerformancePage.css?raw';

/*
 * Student performance (/performance/), redesigned in the dashboard style.
 * Numbers printed with `{{ x }}` / `|floatformat` arrive pre-rendered from the API
 * (`*_text`, `day.fmt`) so they read exactly as Django printed them. When the student has
 * no course, `performance` is null and the template's lookups printed empty strings.
 */

const out = (v) => (v === null || v === undefined ? '' : v);

// Same thresholds as the original badges: >= high -> good, > 0 -> partial, else none.
const pctTone = (value, high) => (value >= high ? 'good' : value > 0 ? 'warn' : 'none');
const dayTone = (value) => (value >= 70 ? 'good' : value >= 35 ? 'warn' : 'none');

function Pill({ tone, children }) {
  return <span className={`spf-pill spf-pill--${tone}`}>{children}</span>;
}

function PerformanceContent({ data }) {
  // Injected once the data is loaded, i.e. after StudentLayout's CSS (same cascade order as the template).
  usePageAssets({ css });

  const perf = data.performance || {};
  const hasPerf = Boolean(data.performance);
  const activeCourse = data.active_course || {};
  const days = perf.days || [];
  const remainingLessons = data.remaining_lessons;
  const scoreGap = data.score_gap;
  const firstDayMax = out(perf.first_day_max_score_text);
  const overall = Math.max(0, Math.min(100, parseFloat(perf.overall_percentage_text) || 0));
  const ring = 2 * Math.PI * 52;

  const stats = [
    { label: 'Overall score', value: `${out(perf.overall_percentage_text) || 0}%`, icon: 'bi-speedometer2', tone: 'emerald' },
    { label: 'Grade', value: out(perf.grade) || '—', icon: 'bi-award-fill', tone: 'gold' },
    { label: 'Days completed', value: `${out(perf.completed_days_count) || 0} / ${out(perf.total_days) || 0}`, icon: 'bi-calendar-check-fill', tone: 'teal' },
    {
      label: perf.is_passed ? 'Status' : 'To pass',
      value: perf.is_passed ? 'Passed' : `+${out(data.score_gap_text) || 0}%`,
      icon: perf.is_passed ? 'bi-patch-check-fill' : 'bi-flag-fill',
      tone: perf.is_passed ? 'emerald' : 'amber',
    },
  ];

  return (
    <div className="spf">
      {/* Hero */}
      <section className="spf-hero">
        <div className="spf-hero__orb" aria-hidden="true" />
        <div className="spf-hero__text">
          <p className="spf-hero__eyebrow">Course performance &amp; scoring</p>
          <h2 className="spf-hero__title">{out(activeCourse.display_title) || 'Your learning track'}</h2>
          <div className="spf-chips">
            <span className="spf-chip"><i className="bi bi-layers"></i> Level: {activeCourse.level || 'Standard'}</span>
            <span className="spf-chip"><i className="bi bi-calendar3"></i> {perf.total_days || 7}-day plan</span>
            {perf.pass_mark_text ? <span className="spf-chip"><i className="bi bi-flag"></i> Pass mark {perf.pass_mark_text}%</span> : null}
          </div>
          <div className="spf-hero__actions">
            <Link to="/daily_lesson/" className="spf-btn spf-btn--gold"><i className="bi bi-play-circle-fill"></i> Continue lesson</Link>
            <Link to="/course-content/" className="spf-btn spf-btn--ghost"><i className="bi bi-journal-text"></i> Syllabus</Link>
          </div>
        </div>
        <div className="spf-ring" role="img" aria-label={`Overall course score ${overall}%`}>
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <defs>
              <linearGradient id="spfRingGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#f3d880" />
                <stop offset="100%" stopColor="#34d399" />
              </linearGradient>
            </defs>
            <circle cx="60" cy="60" r="52" className="spf-ring__track" />
            <circle cx="60" cy="60" r="52" className="spf-ring__bar" strokeDasharray={ring} strokeDashoffset={ring * (1 - overall / 100)} />
          </svg>
          <div className="spf-ring__label">
            <strong>{out(perf.overall_percentage_text) || 0}%</strong>
            <small>Overall</small>
          </div>
        </div>
      </section>

      {!hasPerf ? (
        <div className="spf-notice">
          <i className="bi bi-info-circle-fill"></i>
          <span>No performance data yet. Choose a course and complete your first lesson to start scoring.</span>
          <Link to="/generate_course/" className="spf-btn spf-btn--primary spf-btn--sm">Browse courses</Link>
        </div>
      ) : null}

      {/* Stats */}
      <section className="spf-stats" aria-label="Score summary">
        {stats.map((s, i) => (
          <div key={s.label} className={`spf-stat spf-stat--${s.tone}`} style={{ '--i': i }}>
            <span className="spf-stat__icon"><i className={`bi ${s.icon}`}></i></span>
            <span className="spf-stat__body">
              <strong>{s.value}</strong>
              <small>{s.label}</small>
            </span>
          </div>
        ))}
      </section>

      {/* Certificate */}
      <section className={`spf-panel spf-cert ${perf.is_unlocked ? 'is-unlocked' : 'is-locked'}`}>
        <span className="spf-cert__icon"><i className={`bi ${perf.is_unlocked ? 'bi-patch-check-fill' : 'bi-lock-fill'}`}></i></span>
        <div className="spf-cert__body">
          <p className="spf-eyebrow">Certificate</p>
          <h3 className="spf-title">{perf.is_unlocked ? 'Certificate of completion unlocked!' : 'Certificate locked'}</h3>
          {perf.is_unlocked ? (
            <>
              <p className="spf-text">
                Congratulations! You completed all {perf.total_days} days with an overall score of <strong>{perf.overall_percentage_text}%</strong>, above the {perf.pass_mark_text}% pass mark.
              </p>
              <div className="spf-row">
                <Link to={`/certificate/${activeCourse.id}/`} className="spf-btn spf-btn--primary"><i className="bi bi-eye-fill"></i> View certificate</Link>
                <a href={`/certificate/${activeCourse.id}/download-pdf/`} className="spf-btn spf-btn--soft"><i className="bi bi-download"></i> Download PDF</a>
              </div>
            </>
          ) : (
            <>
              <p className="spf-text">
                Your official ALVIX certificate unlocks once you complete all course days and reach the <strong>{out(perf.pass_mark_text)}%</strong> pass mark.
              </p>
              {(remainingLessons > 0 || scoreGap > 0) ? (
                <ul className="spf-reqs">
                  {remainingLessons > 0 && (
                    <li><i className="bi bi-journal-check"></i> <span><strong>{remainingLessons} lesson(s)</strong> remaining to complete</span></li>
                  )}
                  {scoreGap > 0 && (
                    <li><i className="bi bi-graph-up-arrow"></i> <span><strong>{data.score_gap_text}%</strong> more overall score needed to reach {perf.pass_mark_text}%</span></li>
                  )}
                </ul>
              ) : null}
              <button type="button" className="spf-btn spf-btn--locked" disabled><i className="bi bi-lock-fill"></i> Certificate locked</button>
            </>
          )}
        </div>
      </section>

      {/* Day-by-day breakdown */}
      <section className="spf-panel">
        <header className="spf-panel__head">
          <div>
            <p className="spf-eyebrow">Breakdown</p>
            <h3 className="spf-title">Day-by-day scoring</h3>
            <p className="spf-sub">
              100% split across {out(perf.total_days)} days (~{firstDayMax}% each). Each day: 20% watch time, 40% assignment, 40% quiz.
            </p>
          </div>
          <div className="spf-legend">
            <span><i className="bi bi-stopwatch"></i> Watch 20%</span>
            <span><i className="bi bi-pencil-square"></i> Assignment 40%</span>
            <span><i className="bi bi-patch-question"></i> Quiz 40%</span>
          </div>
        </header>

        {days.length ? (
          <>
            <div className="spf-table-wrap">
              <table className="spf-table">
                <thead>
                  <tr>
                    <th>Day &amp; lesson</th>
                    <th>Watch time</th>
                    <th>Assignment</th>
                    <th>Quiz</th>
                    <th>Day score <small>(max {firstDayMax}%)</small></th>
                    <th>Daily total</th>
                    <th>Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {days.map((day, i) => (
                    <tr key={`${day.lesson_id}-${i}`}>
                      <td>
                        <div className="spf-day">
                          <span className="spf-day__num">{day.day_number}</span>
                          <strong>{day.lesson_title}</strong>
                        </div>
                      </td>
                      <td><Pill tone={pctTone(day.watch_time_pct, 100)}>{day.fmt.watch_time_pct}%</Pill><small className="spf-pts">{day.fmt.watch_time_score} pts</small></td>
                      <td><Pill tone={pctTone(day.assignment_pct, 80)}>{day.fmt.assignment_pct}%</Pill><small className="spf-pts">{day.fmt.assignment_score} pts</small></td>
                      <td><Pill tone={pctTone(day.quiz_pct, 80)}>{day.fmt.quiz_pct}%</Pill><small className="spf-pts">{day.fmt.quiz_score} pts</small></td>
                      <td><strong className="spf-strong">{day.fmt.day_score}</strong> / {day.fmt.day_max_score}%</td>
                      <td>
                        <div className="spf-mini">
                          <span className="spf-mini__bar"><span style={{ width: `${Math.min(100, Number(day.day_percentage) || 0)}%` }} /></span>
                          <Pill tone={dayTone(day.day_percentage)}>{day.fmt.day_percentage}%</Pill>
                        </div>
                      </td>
                      <td className="spf-remarks-cell">{day.remarks}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <ul className="spf-daycards">
              {days.map((day, i) => (
                <li key={`${day.lesson_id}-${i}-m`} className="spf-daycard">
                  <div className="spf-daycard__head">
                    <div className="spf-day">
                      <span className="spf-day__num">{day.day_number}</span>
                      <strong>{day.lesson_title}</strong>
                    </div>
                    <Pill tone={dayTone(day.day_percentage)}>{day.fmt.day_percentage}%</Pill>
                  </div>
                  <div className="spf-daycard__grid">
                    <div><small>Watch</small><Pill tone={pctTone(day.watch_time_pct, 100)}>{day.fmt.watch_time_pct}%</Pill></div>
                    <div><small>Assignment</small><Pill tone={pctTone(day.assignment_pct, 80)}>{day.fmt.assignment_pct}%</Pill></div>
                    <div><small>Quiz</small><Pill tone={pctTone(day.quiz_pct, 80)}>{day.fmt.quiz_pct}%</Pill></div>
                  </div>
                  <p className="spf-daycard__score">Day score <strong>{day.fmt.day_score}</strong> / {day.fmt.day_max_score}%</p>
                  {day.remarks ? <p className="spf-daycard__remarks">{day.remarks}</p> : null}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <div className="spf-empty">
            <span className="spf-empty__icon"><i className="bi bi-table"></i></span>
            <strong>No daily lessons recorded yet</strong>
            <small>Your scores appear here as you complete lessons, assignments and quizzes.</small>
          </div>
        )}
      </section>

      {/* AI review */}
      {perf.ai_review && (
        <section className="spf-panel">
          <header className="spf-panel__head">
            <div>
              <p className="spf-eyebrow">AI advisor</p>
              <h3 className="spf-title">Performance review &amp; advice</h3>
            </div>
          </header>
          <div className="spf-ai">
            <span className="spf-ai__icon"><i className="bi bi-robot"></i></span>
            <p>{perf.ai_review}</p>
          </div>
          <div className="spf-split">
            <div className="spf-box spf-box--good">
              <h4 className="spf-box__title"><i className="bi bi-check-circle-fill"></i> Core strengths</h4>
              <ul>
                {perf.strengths?.length
                  ? perf.strengths.map((s, i) => <li key={i}>{s}</li>)
                  : <li>Active consistency in daily lesson participation.</li>}
              </ul>
            </div>
            <div className="spf-box spf-box--warn">
              <h4 className="spf-box__title"><i className="bi bi-lightbulb-fill"></i> Topics to review</h4>
              <ul>
                {perf.weak_topics?.length
                  ? perf.weak_topics.map((w, i) => <li key={i}>{w}</li>)
                  : <li>Maintain deep focus on practical assignments and test case validations.</li>}
              </ul>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default function PerformancePage() {
  const { data, ready } = usePageData('/student/performance/');
  if (!ready) return <AdminLoader />;
  return <PerformanceContent data={data} />;
}
