import { Link, useLocation, useParams } from 'react-router-dom';
import StudentLayout from '../../layouts/StudentLayout';
import { ICONS_1113, googleFont } from '../../cdn';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import { dflt, djDate, widthratio } from '../../utils/djangoFormat';
import AdminLoader from '../../layouts/AdminLoader';
import NotFoundPage from '../NotFoundPage';
import certCss from './CertificatePage.css?raw';
import lockedCss from './CertificateLockedPage.css?raw';

/*
 * /certificate/ and /certificate/:courseId/ (query `preview`) — view `certificate`.
 * GET /api/v1/learning/certificate/?course_id=&preview=
 *   locked   -> `student_dashboard/certificate_locked.html` (extends the student base -> <StudentLayout>)
 *   unlocked -> `student_dashboard/course_data/certificate.html` (standalone: only its Google Fonts +
 *               Bootstrap Icons, no Bootstrap CSS; its Bootstrap utility classes stay inert as before)
 */
const CERT_FONTS = googleFont(
  'family=Cinzel:wght@500;700;800;900&family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Montserrat:wght@400;500;600;700',
);
// In the template the action bar and the canvas were direct flex children of <body>; keep that box tree.
const ROOT_AS_BODY = '\n#root { display: contents; }\n';

export default function CertificatePage() {
  const { courseId } = useParams();
  const { search } = useLocation();
  const preview = new URLSearchParams(search).get('preview');
  const { data, ready, notFound, error } = usePageData('/learning/certificate/', { course_id: courseId, preview });

  const locked = ready && data.locked;
  const unlocked = ready && !data.locked;
  // Called here (the parent of <StudentLayout>) so the page CSS lands after the layout's
  // Bootstrap/CSS in <head>, as the template's <style> came after the base's stylesheets.
  usePageAssets({
    links: unlocked ? [CERT_FONTS, ICONS_1113] : [],
    css: locked ? lockedCss : unlocked ? certCss + ROOT_AS_BODY : '',
    title: unlocked ? `Official Certificate of Completion • ${data.certificate?.student_name || ''} • ALVIX` : undefined,
  });

  if (notFound) return <NotFoundPage />;
  // Server/network failure: show the error card with Retry instead of a blank page.
  if (!ready) return error ? <StudentLayout><AdminLoader /></StudentLayout> : null;
  if (data.locked) {
    return (
      <StudentLayout>
        <CertificateLocked data={data} />
      </StudentLayout>
    );
  }
  return <Certificate data={data} />;
}

function CertificateLocked({ data }) {
  const {
    error,
    remaining_lessons: remainingLessons,
    score_gap: scoreGap,
    score_gap_display: scoreGapDisplay,
    pass_mark_display: passMarkDisplay,
    active_course: lockedCourse,
    current_score_display: currentScoreDisplay,
    total_lessons: totalLessons,
    completed_lessons: completedLessons,
  } = data;

  return (
    <div className="container-fluid py-5">
      <div className="row justify-content-center">
        <div className="col-lg-7 col-md-9 text-center">
          <div className="card border-0 shadow-lg rounded-4 p-5 bg-white position-relative overflow-hidden" ref={goldTopBorder}>

            <div className="rounded-circle d-inline-flex align-items-center justify-content-center mx-auto mb-4 shadow-sm" style={{ width: '90px', height: '90px', background: 'rgba(212, 175, 55, 0.15)', border: '2px solid #D4AF37' }}>
              <i className="bi bi-shield-lock-fill fs-1" style={{ color: '#064E3B' }}></i>
            </div>

            <h3 className="fw-bold mb-2" style={{ color: '#064E3B' }}>Certificate of Completion Locked</h3>
            <p className="text-secondary mb-4">
              {dflt(error, 'You have not yet completed all curriculum modules to unlock your official accredited certificate.')}
            </p>

            {(remainingLessons || scoreGap) ? (
              <div className="alert alert-light border border-danger-subtle p-3 mb-4 text-start small">
                <strong className="text-danger"><i className="bi bi-exclamation-circle me-1"></i> Remaining Requirements to Unlock:</strong>
                <ul className="mb-0 ps-3 mt-2 text-muted">
                  {remainingLessons > 0 && (
                    <li><strong>{remainingLessons} lesson(s)</strong> remaining to complete.</li>
                  )}
                  {scoreGap > 0 && (
                    <li><strong>{scoreGapDisplay}%</strong> additional overall score needed to reach the <strong>{passMarkDisplay}%</strong> pass mark (Current: {currentScoreDisplay}%).</li>
                  )}
                </ul>
              </div>
            ) : null}

            {/* `total_lessons` is never passed by the view, so this block does not render (kept for parity). */}
            {totalLessons ? (
              <div className="p-3 rounded-3 mb-4 text-start" style={{ background: '#F8FAFC', border: '1px solid #E2E8F0' }}>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span className="small fw-bold text-dark">Course Curriculum Progress:</span>
                  <span className="badge bg-success">{completedLessons} of {totalLessons} Lessons Complete</span>
                </div>
                <div className="progress" style={{ height: '8px' }}>
                  <div className="progress-bar" role="progressbar" style={{ width: `${widthratio(completedLessons, totalLessons, 100)}%`, background: 'linear-gradient(90deg, #D4AF37, #106E53)' }}></div>
                </div>
              </div>
            ) : null}

            <div className="d-flex flex-wrap justify-content-center gap-2">
              <Link to={lockedCourse?.id ? `/course_content/?course_id=${lockedCourse.id}` : "/course_content/"} className="btn btn-golden px-4 py-2 rounded-pill fw-bold shadow-sm">
                <i className="bi bi-play-circle-fill me-1"></i> Resume Course &amp; Unlock
              </Link>
              <Link to="/performance/" className="btn btn-outline-success px-4 py-2 rounded-pill fw-semibold">
                <i className="bi bi-graph-up me-1"></i> View Performance Page
              </Link>
              <Link to="/dashboard/" className="btn btn-outline-secondary px-4 py-2 rounded-pill fw-semibold">
                <i className="bi bi-house-door me-1"></i> Dashboard
              </Link>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}

function goldTopBorder(el) {
  if (el) el.style.setProperty('border-top', '5px solid #D4AF37', 'important');
}

const FLOURISH_PATHS = (
  <>
    <path d="M5 5 H45 C25 25 25 45 5 45 V5 Z" fill="#D4AF37" fillOpacity="0.2" />
    <path d="M5 5 H55 C30 30 30 55 5 55 Z" stroke="#D4AF37" strokeWidth="2" />
    <path d="M12 12 H40 C22 22 22 40 12 40 Z" stroke="#064E3B" strokeWidth="1.5" />
    <circle cx="8" cy="8" r="3" fill="#D4AF37" />
    <circle cx="28" cy="28" r="2.5" fill="#064E3B" />
  </>
);

// Seal legends keep the template's exact text nodes (whitespace included) so SVG text layout is identical.
const TOP_LEGEND = `
                                        ★ ALVIX ACADEMY ★
                                    `;
const BOTTOM_LEGEND = `
                                        OFFICIAL SEAL • 2026
                                    `;

function Certificate({ data }) {
  const { certificate, active_course: activeCourse } = data;
  const certId = certificate.certificate_id;

  return (
    <>
      {/* Action Bar (Hidden during Print) */}
      <div className="action-bar">
        <Link to={`/course_content/?course_id=${activeCourse.id}`} className="btn-action btn-back">
          <i className="bi bi-arrow-left"></i> Back to Syllabus
        </Link>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <Link to="/performance/" className="btn-action btn-back">
            <i className="bi bi-graph-up"></i> Performance
          </Link>
          <a href={`/certificate/${activeCourse.id}/download-pdf/`} className="btn-action btn-print" style={{ background: 'linear-gradient(135deg, #10B981, #065F46)', color: '#FFF', border: '1px solid #34D399' }}>
            <i className="bi bi-file-earmark-pdf-fill"></i> Download PDF
          </a>
          <Link to={`/verify-certificate/${certId}/`} target="_blank" className="btn-action btn-back">
            <i className="bi bi-qr-code-scan"></i> Verify Online
          </Link>
          <button onClick={() => window.print()} className="btn-action btn-print">
            <i className="bi bi-printer-fill"></i> Print
          </button>
        </div>
      </div>

      {/* Master Certificate Canvas */}
      <div className="certificate-canvas">

        <div className="border-outer">
          <div className="border-middle-gold">
            <div className="border-inner">

              {/* 4 Corner Victorian Flourish Vectors */}
              <svg className="corner-flourish corner-tl" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">{FLOURISH_PATHS}</svg>
              <svg className="corner-flourish corner-tr" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">{FLOURISH_PATHS}</svg>
              <svg className="corner-flourish corner-bl" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">{FLOURISH_PATHS}</svg>
              <svg className="corner-flourish corner-br" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">{FLOURISH_PATHS}</svg>

              {/* Center Background Watermark */}
              <svg className="certificate-watermark" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                <circle cx="100" cy="100" r="90" fill="none" stroke="#064E3B" strokeWidth="6" />
                <circle cx="100" cy="100" r="75" fill="none" stroke="#D4AF37" strokeWidth="3" />
                <path d="M100 25 L115 65 L158 68 L125 96 L135 138 L100 115 L65 138 L75 96 L42 68 L85 65 Z" fill="#064E3B" />
                <text x="100" y="172" fontFamily="'Cinzel', serif" fontSize="14" fontWeight="900" fill="#064E3B" textAnchor="middle">ALVIX ACADEMY</text>
              </svg>

              {/* Top Header Section */}
              <div className="cert-header">
                {/* ALVIX Academy Crest Emblem */}
                <svg className="emblem-icon" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#F9E076" />
                      <stop offset="50%" stopColor="#D4AF37" />
                      <stop offset="100%" stopColor="#AA771C" />
                    </linearGradient>
                    <linearGradient id="greenGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#106E53" />
                      <stop offset="100%" stopColor="#064E3B" />
                    </linearGradient>
                  </defs>
                  <circle cx="50" cy="50" r="46" fill="url(#greenGrad)" stroke="url(#goldGrad)" strokeWidth="3" />
                  <circle cx="50" cy="50" r="39" fill="none" stroke="url(#goldGrad)" strokeWidth="1.2" strokeDasharray="3,2" />
                  {/* Laurel Branch Left */}
                  <path d="M30 65 C25 50, 26 35, 38 24" fill="none" stroke="url(#goldGrad)" strokeWidth="2" strokeLinecap="round" />
                  <path d="M28 50 Q22 45 28 42" fill="url(#goldGrad)" />
                  <path d="M31 38 Q25 33 32 30" fill="url(#goldGrad)" />
                  {/* Laurel Branch Right */}
                  <path d="M70 65 C75 50, 74 35, 62 24" fill="none" stroke="url(#goldGrad)" strokeWidth="2" strokeLinecap="round" />
                  <path d="M72 50 Q78 45 72 42" fill="url(#goldGrad)" />
                  <path d="M69 38 Q75 33 68 30" fill="url(#goldGrad)" />
                  {/* Central Star */}
                  <path d="M50 28 L54 40 L66 40 L56 48 L60 60 L50 52 L40 60 L44 48 L34 40 L46 40 Z" fill="url(#goldGrad)" />
                  {/* Letter A */}
                  <text x="50" y="78" fontFamily="'Cinzel', serif" fontSize="16" fontWeight="900" fill="url(#goldGrad)" textAnchor="middle" letterSpacing="1">ALVIX</text>
                </svg>

                <h1 className="academy-name">ALVIX ADAPTIVE LEARNING ACADEMY</h1>
                <div className="academy-sub">ACCREDITED ADVANCED PROFESSIONAL CERTIFICATION AUTHORITY</div>

                <div className="gold-divider">
                  <div className="gold-line"></div>
                  <span className="gold-star">&#9733; &#9733; &#9733;</span>
                  <div className="gold-line"></div>
                </div>
              </div>

              {/* Certificate Title Area */}
              <div className="cert-title-area">
                <div className="cert-main-heading">CERTIFICATE OF EXCELLENCE</div>
                <div className="cert-subheading">This official honors credential is systematically conferred upon</div>
              </div>

              {/* Student Name */}
              <div className="recipient-area">
                <div className="student-name-text">{certificate.student_name}</div>
                <div className="student-id-meta">
                  {/* Owner-approved fix: shows profile.student_id (the template printed the email here). */}
                  {'STUDENT ID: '}{certificate.student_id || certificate.student_email}{'  •  CERTIFICATE ID: '}{certId}
                </div>
              </div>

              {/* Award Description */}
              <div className="award-statement">
                for successfully fulfilling all rigorous academic requirements, mastering daily theory lessons, hands-on lab projects, and automated AI assessments to achieve verified excellence in:
                <br />
                <div className="course-title-banner">
                  {certificate.course_name}
                </div>
              </div>

              {/* Performance Badge, Duration & AI Commendation Remarks */}
              <div className="honors-section">
                <span className="honor-pill">Overall Score: <strong>{certificate.overall_percentage_display}%</strong></span>
                <span className="honor-pill">Honors Standing: <strong>Grade {certificate.performance_grade}</strong></span>
                <span className="honor-pill">Benchmark Level: <strong>{dflt(dflt(certificate.level, activeCourse.level), 'Standard')}</strong></span>
                <span className="honor-pill">Duration: <strong>{djDate(certificate.start_date, 'M d, Y')} &ndash; {djDate(certificate.current_date, 'M d, Y')} ({certificate.duration_days} Days)</strong></span>
              </div>

              <div className="commendation-quote">
                &ldquo;{certificate.ai_review}&rdquo;
              </div>

              {/* SIGNATURES AND OFFICIAL ALVIX STAMP (User Specific Request) */}
              <div className="validation-footer">

                {/* 1. LEFT SIGNATURE: SUPERVISED BY DR. SALEEM */}
                <div className="signature-col-left">
                  {/* Dr. Saleem Authentic Academic Vector Signature */}
                  <svg className="signature-vector" viewBox="0 0 280 80" xmlns="http://www.w3.org/2000/svg">
                    {/* Calligraphic Dr. Saleem signature */}
                    <path d="M25 45 C20 30, 30 15, 42 16 C55 17, 45 42, 38 52 C32 60, 48 58, 58 46" fill="none" stroke="#064E3B" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
                    <circle cx="63" cy="50" r="2" fill="#064E3B" />
                    {/* 'S' flourish */}
                    <path d="M85 30 C75 18, 92 12, 105 20 C120 30, 85 40, 92 56 C98 70, 125 65, 140 45" fill="none" stroke="#064E3B" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    {/* 'aleem' cursive loops */}
                    <path d="M135 48 C145 35, 155 42, 160 52 C165 40, 172 40, 176 50 C182 38, 190 38, 194 48 C200 38, 208 40, 212 50 C216 45, 230 46, 235 52" fill="none" stroke="#064E3B" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
                    {/* Academic sweeping underline */}
                    <path d="M75 62 Q160 54 245 58" fill="none" stroke="#D4AF37" strokeWidth="2" strokeLinecap="round" />
                    <circle cx="248" cy="58" r="2" fill="#D4AF37" />
                  </svg>
                  <div className="signature-rule"></div>
                  <p className="signatory-name">Dr. Saleem, Ph.D.</p>
                  <p className="signatory-role">Academic Director &amp; Supervisor</p>
                  <span className="signatory-badge badge-supervisor">
                    <i className="bi bi-patch-check-fill me-1"></i> Supervised by Dr. Saleem
                  </span>
                </div>

                {/* 2. CENTER: OFFICIAL ALVIX EMBOSSED GOLDEN STAMP / SEAL */}
                <div className="seal-col-center">
                  <svg className="official-seal-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      {/* Metallic 3D Gold Gradients */}
                      <linearGradient id="sealGoldOuter" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#FFF4D0" />
                        <stop offset="25%" stopColor="#E8C360" />
                        <stop offset="50%" stopColor="#D4AF37" />
                        <stop offset="75%" stopColor="#996515" />
                        <stop offset="100%" stopColor="#5B3C06" />
                      </linearGradient>
                      <linearGradient id="sealGoldInner" x1="100%" y1="100%" x2="0%" y2="0%">
                        <stop offset="0%" stopColor="#FFF9E6" />
                        <stop offset="50%" stopColor="#D4AF37" />
                        <stop offset="100%" stopColor="#8A5A12" />
                      </linearGradient>
                      <linearGradient id="ribbonRed" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#DC2626" />
                        <stop offset="100%" stopColor="#991B1B" />
                      </linearGradient>
                      <linearGradient id="ribbonGold" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#FDE047" />
                        <stop offset="100%" stopColor="#CA8A04" />
                      </linearGradient>
                    </defs>

                    {/* Draped Silk Ribbon Tails Underneath Seal */}
                    <g id="ribbons">
                      {/* Left Ribbon */}
                      <path d="M78 140 L65 195 L85 185 L98 195 L90 140 Z" fill="url(#ribbonRed)" stroke="#7F1D1D" strokeWidth="1" />
                      {/* Right Ribbon */}
                      <path d="M122 140 L110 195 L125 185 L145 195 L132 140 Z" fill="url(#ribbonGold)" stroke="#854D0E" strokeWidth="1" />
                    </g>

                    {/* 32-Point Starburst Rosette / Scalloped Seal Edge */}
                    <circle cx="100" cy="100" r="88" fill="url(#sealGoldOuter)" stroke="#5B3C06" strokeWidth="1.5" />

                    {/* Decorative Serrated Teeth */}
                    <circle cx="100" cy="100" r="83" fill="none" stroke="#FFF9E6" strokeWidth="2" strokeDasharray="4,3" />

                    {/* Inner Sunken Gold Ring */}
                    <circle cx="100" cy="100" r="76" fill="url(#sealGoldInner)" stroke="#8A5A12" strokeWidth="2" />
                    <circle cx="100" cy="100" r="64" fill="#064E3B" stroke="url(#sealGoldOuter)" strokeWidth="2" />

                    {/* Circular Seal Legend Text */}
                    <path id="sealTextPathTop" d="M38 100 A62 62 0 0 1 162 100" fill="none" />
                    <path id="sealTextPathBottom" d="M162 100 A62 62 0 0 1 38 100" fill="none" />

                    <text fontFamily="'Cinzel', serif" fontSize="8.5" fontWeight="900" fill="#FFF9E6" letterSpacing="1.8">
                      <textPath href="#sealTextPathTop" startOffset="50%" textAnchor="middle">{TOP_LEGEND}</textPath>
                    </text>
                    <text fontFamily="'Montserrat', sans-serif" fontSize="7.5" fontWeight="800" fill="#FDE047" letterSpacing="1.2">
                      <textPath href="#sealTextPathBottom" startOffset="50%" textAnchor="middle">{BOTTOM_LEGEND}</textPath>
                    </text>

                    {/* Center Star & Laurels */}
                    <circle cx="100" cy="100" r="28" fill="url(#sealGoldInner)" stroke="#5B3C06" strokeWidth="1" />
                    <path d="M100 82 L104 94 L116 94 L106 101 L110 113 L100 106 L90 113 L94 101 L84 94 L96 94 Z" fill="#064E3B" />
                    <text x="100" y="122" fontFamily="'Cinzel', serif" fontSize="7" fontWeight="900" fill="#064E3B" textAnchor="middle">VERIFIED</text>
                  </svg>
                  <span className="seal-subtext mb-2">Official ALVIX Seal</span>
                  {certificate.qr_code_data_uri && (
                    <div className="text-center mt-2">
                      <Link to={`/verify-certificate/${certId}/`} target="_blank">
                        <img src={certificate.qr_code_data_uri} alt="QR Verification" style={{ width: '72px', height: '72px', border: '2px solid #D4AF37', borderRadius: '6px', padding: '2px', background: '#FFF' }} />
                      </Link>
                      <small className="d-block text-muted" style={{ fontSize: '8px', fontWeight: 700, color: '#064E3B', marginTop: '2px' }}>SCAN TO VERIFY</small>
                    </div>
                  )}
                </div>

                {/* 3. RIGHT SIGNATURE: FOUNDER TABINDA RUKHSAR */}
                <div className="signature-col-right">
                  {/* Tabinda Rukhsar Authentic Vector Signature Matching Physical Design */}
                  <svg className="signature-vector" viewBox="0 0 280 80" xmlns="http://www.w3.org/2000/svg">
                    {/* Crown Crest Element Above Initial 'T' */}
                    <path d="M42 28 L30 14 L40 22 L50 8 L60 22 L70 14 L58 28 Z" fill="#D4AF37" stroke="#AA771C" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
                    <circle cx="30" cy="14" r="2" fill="#D4AF37" />
                    <circle cx="50" cy="8" r="2" fill="#D4AF37" />
                    <circle cx="70" cy="14" r="2" fill="#D4AF37" />

                    {/* Signature Vector representation for "Tabinda" */}
                    <path d="M50 30 C 44 48, 46 62, 54 70 C 58 74, 64 68, 62 64 C 58 56, 68 38, 80 38 C 98 38, 135 40, 148 46 C 154 48, 150 62, 142 65 C 135 68, 130 62, 133 58 C 140 52, 148 52, 156 56 C 162 60, 166 66, 172 68 C 178 70, 184 65, 188 62 C 190 58, 186 54, 182 58 C 180 62, 186 68, 192 68 C 198 68, 204 60, 208 56 C 215 50, 220 62, 214 68 C 210 72, 220 72, 228 65"
                      fill="none" stroke="#064E3B" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />

                    {/* Star Element above the Trailing Name */}
                    <path d="M228 36 L232 44 L240 45 L234 51 L236 59 L228 54 L220 59 L222 51 L216 45 L224 44 Z" fill="#D4AF37" stroke="#AA771C" strokeWidth="1" />

                    {/* Flowing Underline */}
                    <line x1="68" y1="71" x2="225" y2="71" stroke="#064E3B" strokeWidth="2.2" strokeLinecap="round" />
                  </svg>
                  <div className="signature-rule"></div>
                  <p className="signatory-name">Tabinda Rukhsar</p>
                  <p className="signatory-role">Founder &amp; Chief Executive Officer</p>
                  <span className="signatory-badge badge-founder">
                    <i className="bi bi-award-fill me-1"></i> Founder: Tabinda Rukhsar
                  </span>
                </div>

              </div>

              {/* Bottom Authentication Metadata */}
              <div className="bottom-metadata">
                <span>SECURITY CODE: {certificate.certificate_id} &bull; DIGITAL SIGNATURE VERIFIED</span>
                <span>ALVIX ADVANCED AI ACADEMY &bull; ACCREDITED WORLDWIDE</span>
                <span>VERIFY AT ALVIX.ORG/CERTIFICATE</span>
              </div>

            </div>
          </div>
        </div>

      </div>
    </>
  );
}
