import AdminLoader from '../../layouts/AdminLoader';
import { memo, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { usePageData } from '../../hooks/usePageData';
import { usePageAssets } from '../../hooks/usePageAssets';
import { getCookie } from '../../api/client';
import NotFoundPage from '../NotFoundPage';
import { rawStyle } from './rawStyle';
// Side effect: defines window.AvatarPlayer / window.IntroSequence / window.LecturePlayer
import '../../player/inara_player.js';
import css from './DailyLessonPage.css?raw';

/*
 * Port of `student_dashboard/course_data/daily_lesson.html` (rendered inside StudentLayout).
 * The DOM below is the template's markup; the player classes from inara_player.js drive it
 * imperatively, exactly like the template's inline script did.
 */

// `{{ value|escapejs }}` inside a JSON string: None printed as "None".
const djStr = (v) => (v === null || v === undefined ? 'None' : String(v));

// The player session that currently owns the page DOM (guards against double instantiation).
let activeSession = null;

const PLAYER_GLOBALS = [
  'lecturePlayer',
  'introSequence',
  'toggleSlideExplanation',
  'focusSlideExplanation',
  'playCurrentSlideVoice',
  'updateExplanationContent',
];

function createPlayerSession(data) {
  const { lesson } = data;
  const assets = data.avatar_assets || {};
  const urls = assets.resolved_urls || {};

  // 2. Presentation data (all dynamic slides)
  const presentationPayload = data.presentation_data || {};
  const slidesList = presentationPayload.slides_list || [];
  const lessonTitle = lesson.title || 'Masterclass Lecture';
  const courseTitle = data.course_title || 'Academic Course';
  const dayNum = lesson.day_number || 1;

  // 3. Avatar configuration (same object the template's #avatarConfigData JSON produced)
  const avatarConfig = {
    avatar_name: djStr(data.avatar_name_display),
    avatar_name_spoken: djStr(data.avatar_name_spoken),
    developer_name: djStr(data.developer_name),
    university_or_department: djStr(data.university_or_department),
    student_name: djStr(data.student_name),
    is_full_intro: Boolean(data.is_full_intro),
    intro_spoken: djStr(data.intro_spoken),
    intro_display: djStr(data.intro_display),
    has_custom_avatar: Boolean(assets.has_custom_avatar),
    assets: {
      idle: djStr(urls.idle),
      wave: djStr(urls.wave),
      blink: djStr(urls.blink),
      mouth_open: djStr(urls.mouth_open),
    },
  };

  // 4. AvatarPlayer
  const avatarPlayer = new window.AvatarPlayer(avatarConfig);
  const introImg = document.getElementById('introAvatarImg');
  const cornerImg = document.getElementById('lectureCornerAvatarImg');
  if (introImg) avatarPlayer.registerElement(introImg, 'intro');
  if (cornerImg) avatarPlayer.registerElement(cornerImg, 'corner');

  // 5. LecturePlayer
  const lecturePlayer = new window.LecturePlayer(avatarPlayer, {
    slidesList,
    lessonTitle,
    courseTitle,
    dayNum,
    csrfToken: getCookie('csrftoken') || '',
    watchTimeUrl: data.watch_time_url || `/lesson/${lesson.id}/watch-time/`,
  });
  window.lecturePlayer = lecturePlayer;

  // 6. IntroSequence (10s introduction + auto-transition)
  const introSequence = new window.IntroSequence(avatarPlayer, avatarConfig, () => {
    lecturePlayer.startPlayback();
  });
  window.introSequence = introSequence;

  // 7. Slide explanation drawer hooks
  const toggleSlideExplanation = function (show) {
    const drawer = document.getElementById('slideExplanationDrawer');
    if (!drawer) return;
    if (show) {
      window.updateExplanationContent(lecturePlayer.currentIdx);
      drawer.classList.remove('d-none');
      drawer.classList.add('d-flex');
    } else {
      drawer.classList.remove('d-flex');
      drawer.classList.add('d-none');
    }
  };
  const focusSlideExplanation = function () {
    window.toggleSlideExplanation(true);
  };
  const playCurrentSlideVoice = function () {
    lecturePlayer.togglePlay();
  };

  // 8. Synchronize the explanation drawer with the active slide
  const updateExplanationContent = function (idx) {
    const slide = slidesList && slidesList[idx] ? slidesList[idx] : {};
    const titleText = slide.title || `Slide ${idx + 1}`;

    const drawerNum = document.getElementById('drawerSlideNum');
    const drawerTitle = document.getElementById('drawerSlideTitle');
    const drawerConcept = document.getElementById('drawerConceptText');
    const drawerExample = document.getElementById('drawerExampleText');
    const drawerTakeaway = document.getElementById('drawerTakeawayText');

    if (drawerNum) drawerNum.innerText = idx + 1;
    if (drawerTitle) drawerTitle.innerText = titleText;

    let conceptVal = slide.concept_explanation || slide.teacher_briefing || slide.speaker_notes || '';
    if (!conceptVal && slide.key_points && Array.isArray(slide.key_points)) {
      conceptVal = slide.key_points.join('\n\n• ');
      if (conceptVal) conceptVal = '• ' + conceptVal;
    } else if (!conceptVal && slide.points && Array.isArray(slide.points)) {
      conceptVal = slide.points.join('\n\n• ');
      if (conceptVal) conceptVal = '• ' + conceptVal;
    }
    if (!conceptVal) {
      conceptVal = `This module explores the foundational mechanics and operational architecture of ${lessonTitle}. Pay strict attention to system invariants, thread boundaries, and state consistency.`;
    }
    if (drawerConcept) drawerConcept.innerText = conceptVal;

    let exampleVal = slide.real_world_example || slide.industry_context || slide.use_case || '';
    if (!exampleVal) {
      exampleVal = `Enterprise Infrastructure: Scalable production environments (such as Stripe, Netflix, and Amazon AWS) implement these exact contracts to enforce fault isolation and sub-millisecond p99 latency guarantees.`;
    }
    if (drawerExample) drawerExample.innerText = exampleVal;

    let takeawayVal = slide.key_takeaway || slide.teacher_core_rule || slide.takeaway || '';
    if (!takeawayVal) {
      takeawayVal = `Enforce explicit invariants and defensive validation: verify boundaries before committing state changes.`;
    }
    if (drawerTakeaway) drawerTakeaway.innerText = takeawayVal;

    // Hidden card elements (for DOM query compatibility)
    const textExpNum = document.getElementById('textExpSlideNum');
    const textExpTitle = document.getElementById('textExpSlideTitle');
    const textExpConcept = document.getElementById('textExpConcept');
    const textExpExample = document.getElementById('textExpExample');
    const textExpTakeaway = document.getElementById('textExpTakeaway');
    if (textExpNum) textExpNum.innerText = idx + 1;
    if (textExpTitle) textExpTitle.innerText = titleText;
    if (textExpConcept) textExpConcept.innerText = conceptVal;
    if (textExpExample) textExpExample.innerText = exampleVal;
    if (textExpTakeaway) textExpTakeaway.innerText = takeawayVal;
  };

  const globals = { toggleSlideExplanation, focusSlideExplanation, playCurrentSlideVoice, updateExplanationContent };
  Object.assign(window, globals);

  // Close explanation drawer on Escape key
  const onEscape = function (e) {
    if (e.key === 'Escape' || e.code === 'Escape') {
      window.toggleSlideExplanation(false);
    }
  };
  document.addEventListener('keydown', onEscape);

  // Initial drawer content synchronization
  window.updateExplanationContent(0);

  return {
    destroy() {
      document.removeEventListener('keydown', onEscape);
      introSequence.destroy();
      lecturePlayer.destroy();
      avatarPlayer.destroy();
      const owned = { ...globals, lecturePlayer, introSequence };
      PLAYER_GLOBALS.forEach((name) => {
        if (window[name] === owned[name]) delete window[name];
      });
      if ('speechSynthesis' in window) {
        try { window.speechSynthesis.cancel(); } catch { /* ignore */ }
      }
    },
  };
}

// Owner-approved fix: #fullscreenBtn had no handler. Toggle fullscreen on the player card.
function toggleFullscreen() {
  const doc = document;
  const current = doc.fullscreenElement || doc.webkitFullscreenElement;
  if (current) {
    (doc.exitFullscreen || doc.webkitExitFullscreen)?.call(doc);
    return;
  }
  const target = doc.getElementById('presentationWrapper') || doc.getElementById('presentationCanvas');
  if (!target) return;
  const request = target.requestFullscreen || target.webkitRequestFullscreen;
  if (request) {
    const result = request.call(target);
    if (result && typeof result.catch === 'function') result.catch(() => {});
  }
}

const callGlobal = (name, ...args) => () => {
  if (typeof window[name] === 'function') window[name](...args);
};

const LessonPlayer = memo(function LessonPlayer({ data }) {
  const { lesson } = data;
  const assets = data.avatar_assets || {};
  const urls = assets.resolved_urls || {};
  const avatarName = data.avatar_name_display;
  const assignmentUrl = `/assignment/?lesson_id=${lesson.id}`;
  const quizUrl = `/quiz/?lesson_id=${lesson.id}`;
  const pptUrl = data.download_ppt_url || `/lesson/${lesson.id}/download-ppt/`;

  useEffect(() => {
    let cancelled = false;
    let session = null;

    const start = () => {
      if (cancelled) return;
      if (activeSession) activeSession.destroy();
      session = createPlayerSession(data);
      activeSession = session;
    };

    // The player posts watch time with X-CSRFToken; make sure the cookie exists first.
    if (getCookie('csrftoken')) {
      start();
    } else {
      fetch('/api/v1/auth/csrf/', { credentials: 'same-origin' }).catch(() => {}).finally(start);
    }

    return () => {
      cancelled = true;
      if (session) {
        session.destroy();
        if (activeSession === session) activeSession = null;
      }
      const doc = document;
      if (doc.fullscreenElement && doc.exitFullscreen) doc.exitFullscreen().catch(() => {});
    };
  }, [data]);

  return (
    <div className="container-fluid px-3 px-md-4 py-3" ref={rawStyle('max-width: 100% !important;')}>

      {/* Navigation Breadcrumbs / Title Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between border-bottom pb-3 mb-4" ref={rawStyle('border-color: #D4AF37 !important;')}>
        <div>
          <span className="text-muted small fw-bold text-uppercase" ref={rawStyle('letter-spacing: 1px; color: #8C7320 !important;')}>
            <i className="bi bi-mortarboard-fill me-1"></i> COURSE: {data.course_title}
          </span>
          <h2 className="fw-bold mb-0 mt-1" style={{ color: '#01411C' }}>
            <span className="badge golden-badge me-2 fs-6">Day {lesson.day_number}</span>{lesson.title}
          </h2>
        </div>
        <div className="mt-2 mt-md-0 d-flex flex-wrap gap-2 align-items-center">

          <span id="lessonWatchTimeBadge" className={`badge ${lesson.watch_time_completed ? 'bg-success' : 'bg-secondary'} rounded-pill py-2 px-3 fw-semibold shadow-sm d-flex align-items-center gap-1`}>
            <i className="bi bi-stopwatch me-1"></i> Watch Time: {lesson.watch_time_seconds || 0}s / {lesson.required_watch_seconds || 180}s
          </span>

          <a href={pptUrl} className="btn btn-sm btn-golden shadow-sm fw-semibold d-flex align-items-center gap-1" title="Download editable .pptx file">
            <i className="bi bi-file-earmark-slides-fill"></i> Download PPT (.pptx)
          </a>
          <Link to={assignmentUrl} className="btn btn-sm btn-outline-success rounded-pill fw-semibold shadow-sm">
            <i className="bi bi-pencil-square me-1"></i> Assignment Challenge
          </Link>
          <Link to={quizUrl} className="btn btn-sm btn-outline-dark rounded-pill fw-semibold shadow-sm">
            <i className="bi bi-patch-question me-1"></i> Diagnostic Quiz
          </Link>
          <Link to="/course_content/" className="btn btn-outline-secondary btn-sm px-3 rounded-pill fw-semibold shadow-sm">
            <i className="bi bi-arrow-left me-1"></i> Back to Syllabus
          </Link>
        </div>
      </div>

      {/* MASTERCLASS STUDIO SCREEN: SLIDES STAGE (LEFT) + SLIDE EXPLANATION IN TEXT (RIGHT) */}
      <div className="row g-4 align-items-stretch mb-4" id="masterclassStudio">

        {/* COLUMN 1: LIVE SLIDE PRESENTATION & AUDIO PLAYER (WIDESCREEN 100% FOCUS) */}
        <div className="col-12 d-flex flex-column">
          <div className="card border-0 shadow-lg h-100 presentation-card overflow-hidden d-flex flex-column" id="presentationWrapper">

            {/* Player Header Bar */}
            <div className="card-header bg-white border-bottom border-warning-subtle d-flex flex-wrap justify-content-between align-items-center py-2 px-3 gap-2">
              <div className="d-flex align-items-center flex-wrap gap-2">
                <span className="badge" style={{ background: 'linear-gradient(135deg, #064E3B, #106E53)', color: '#D4AF37', fontWeight: 700, fontSize: '0.8rem', padding: '6px 12px', borderRadius: '8px' }}>
                  <i className="bi bi-file-earmark-slides-fill me-1"></i> ALVIX Slide Player
                </span>
                <span className="badge bg-light text-dark border fw-bold" id="slideCounterBadge">
                  Slide <span id="currentSlideNum">1</span> of <span id="totalSlidesNum">{data.total_slides}</span>
                </span>
              </div>

              {/* Slide & Audio Explanation Action Options */}
              <div className="d-flex align-items-center gap-2 flex-wrap">
                <button type="button" className="btn btn-sm btn-golden fw-bold px-3 py-1 rounded-pill shadow-sm" id="btnHeaderSlideExp" onClick={callGlobal('focusSlideExplanation')} title="View on-screen text breakdown & practical examples">
                  <i className="bi bi-file-text-fill me-1"></i> 1. Slide Explanation
                </button>
                <button type="button" className="btn btn-sm btn-outline-success fw-bold px-3 py-1 rounded-pill shadow-sm" id="btnHeaderAudio" onClick={callGlobal('playCurrentSlideVoice')} title="Play / Pause spoken audio explanation">
                  <i id="headerAudioIcon" className="bi bi-volume-up-fill me-1"></i> 2. Audio Explanation
                </button>
                {/* Sound wave animation */}
                <div className="d-flex align-items-center gap-2 ps-2 border-start" id="voiceIndicator">
                  <div className="sound-wave" id="soundWave">
                    <span className="bar"></span>
                    <span className="bar"></span>
                    <span className="bar"></span>
                    <span className="bar"></span>
                    <span className="bar"></span>
                  </div>
                  <span className="small fw-bold text-success" id="playerStatus">Ready to Learn</span>
                </div>
              </div>
            </div>

            {/* 16:9 Presentation Slide Canvas */}
            <div className="presentation-canvas-container position-relative flex-grow-1" id="presentationCanvas">

              {/* Slide Viewport (Active Slide HTML injected here) */}
              <div id="slideViewport" className="w-100 h-100 position-relative p-4 p-md-5 d-flex flex-column justify-content-between">
                {/* Populated dynamically by JavaScript */}
              </div>

              {/* Slide Explanation Drawer (Available during Fullscreen) */}
              <div id="slideExplanationDrawer" className="position-absolute w-100 h-100 top-0 start-0 p-4 p-md-5 d-none flex-column" style={{ background: 'rgba(255, 255, 255, 0.98)', backdropFilter: 'blur(8px)', zIndex: 30, overflowY: 'auto', borderRadius: '20px' }}>
                <div className="d-flex justify-content-between align-items-center border-bottom pb-2 mb-3">
                  <div className="d-flex align-items-center gap-2">
                    <span className="badge" style={{ background: '#064E3B', color: '#D4AF37', fontSize: '0.85rem', padding: '6px 12px', borderRadius: '8px' }}>
                      <i className="bi bi-file-text-fill text-warning me-1"></i> Slide <span id="drawerSlideNum">1</span> Detailed Explanation
                    </span>
                    <h5 className="mb-0 fw-bold text-success text-truncate" id="drawerSlideTitle" style={{ maxWidth: '520px' }}>Core Concepts</h5>
                  </div>
                  <button type="button" className="btn btn-sm btn-outline-secondary rounded-circle" onClick={callGlobal('toggleSlideExplanation', false)} title="Close Explanation (Esc)">
                    <i className="bi bi-x-lg"></i>
                  </button>
                </div>

                {/* Content Breakdown & Practical Examples */}
                <div className="row g-3 my-auto">
                  {/* Simple Concept Breakdown */}
                  <div className="col-lg-6">
                    <div className="card h-100 p-3 rounded-4 shadow-sm bg-white" ref={rawStyle('border-left: 4.5px solid #064E3B !important; border: 1.5px solid #e2e8f0;')}>
                      <div className="d-flex align-items-center gap-2 mb-2">
                        <span className="badge rounded-circle p-2" style={{ background: '#f0fdf4', color: '#064E3B' }}><i className="bi bi-lightbulb-fill fs-5"></i></span>
                        <h6 className="fw-bold mb-0 text-success">Simple Concept Explanation</h6>
                      </div>
                      <div className="small text-secondary" id="drawerConceptText" style={{ lineHeight: 1.7, fontSize: '0.92rem', whiteSpace: 'pre-line' }}>
                        {/* Injected by JavaScript */}
                      </div>
                    </div>
                  </div>

                  {/* Real-World Practical Example */}
                  <div className="col-lg-6">
                    <div className="card h-100 p-3 rounded-4 shadow-sm" ref={rawStyle('background: #FEF9E7; border: 1.8px solid #D4AF37 !important;')}>
                      <div className="d-flex align-items-center gap-2 mb-2">
                        <span className="badge rounded-circle p-2" style={{ background: '#064E3B', color: '#D4AF37' }}><i className="bi bi-building-fill-check fs-5"></i></span>
                        <h6 className="fw-bold mb-0 text-dark">Real-World Practical Example</h6>
                      </div>
                      <div className="small text-dark" id="drawerExampleText" style={{ lineHeight: 1.7, fontSize: '0.92rem', whiteSpace: 'pre-line' }}>
                        {/* Injected by JavaScript */}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Key Takeaway & Audio Play Button */}
                <div className="mt-3 p-3 rounded-3 d-flex flex-wrap align-items-center justify-content-between gap-2 shadow-sm" style={{ background: 'linear-gradient(135deg, #064E3B, #106E53)', color: '#ffffff', border: '1.5px solid #D4AF37' }}>
                  <div className="d-flex align-items-center gap-2">
                    <i className="bi bi-bookmark-star-fill text-warning fs-5"></i>
                    <div>
                      <span className="badge bg-warning text-dark fw-bold me-2">KEY TAKEAWAY</span>
                      <span className="small fw-semibold text-light" id="drawerTakeawayText"></span>
                    </div>
                  </div>
                  <button type="button" className="btn btn-sm btn-golden fw-bold px-3 py-2 rounded-pill shadow-sm" onClick={callGlobal('playCurrentSlideVoice')}>
                    <i className="bi bi-volume-up-fill me-1"></i> Listen to Audio Explanation
                  </button>
                </div>
              </div>

              {/* Completion Celebration Overlay */}
              <div id="completionOverlay" className="position-absolute w-100 h-100 d-none flex-column align-items-center justify-content-center" style={{ background: 'rgba(6, 78, 59, 0.96)', zIndex: 24 }}>
                <div className="text-center p-4 text-white" style={{ maxWidth: '620px' }}>
                  <div className="rounded-circle d-inline-flex align-items-center justify-content-center mb-3 shadow-lg" style={{ width: '80px', height: '80px', background: '#D4AF37', color: '#064E3B' }}>
                    <i className="bi bi-trophy-fill fs-1"></i>
                  </div>
                  <h3 className="fw-bold mb-1 text-warning">Day {lesson.day_number} Presentation Completed!</h3>
                  <p className="text-light opacity-90 small mb-4">
                    You have successfully reviewed all lecture slides and voice explanations for <strong>{lesson.title}</strong>. Advance your learning with the assignment or quiz.
                  </p>
                  <div className="d-flex flex-wrap justify-content-center gap-2">
                    <button id="replayFullBtn" className="btn btn-outline-warning rounded-pill px-4 fw-semibold">
                      <i className="bi bi-arrow-repeat me-1"></i> Replay Presentation
                    </button>
                    <a href={pptUrl} className="btn rounded-pill px-4 fw-bold" style={{ background: '#D4AF37', color: '#064E3B' }}>
                      <i className="bi bi-file-earmark-slides me-1"></i> Download PPT (.pptx)
                    </a>
                    <Link to={assignmentUrl} className="btn btn-success rounded-pill px-4 fw-semibold">
                      <i className="bi bi-pencil-square me-1"></i> Start Assignment
                    </Link>
                    <Link to={quizUrl} className="btn btn-outline-light rounded-pill px-4 fw-semibold">
                      <i className="bi bi-question-circle me-1"></i> Take Quiz
                    </Link>
                  </div>
                </div>
              </div>

              {/* 1. INARA INTRODUCTION CENTER STAGE OVERLAY */}
              <div id="inaraIntroStage" className="inara-intro-stage">
                <div className="inara-intro-content text-center text-white p-3 p-md-4">
                  {/* ALVIX Brand Pill */}
                  <div className="inara-intro-brand-pill mb-2">
                    <i className="bi bi-mortarboard-fill text-warning me-1"></i>
                    <span>ALVIX &bull; Adaptive Learning System</span>
                  </div>

                  {/* Lesson Title & Course Track */}
                  <h3 className="fw-bold text-white mb-1" style={{ textShadow: '0 2px 10px rgba(0,0,0,0.6)' }}>
                    Day {lesson.day_number}: {lesson.title}
                  </h3>
                  <p className="text-white-50 small mb-3">
                    {data.course_title} &bull; Masterclass Lecture
                  </p>

                  {/* Inara Center Avatar Stage */}
                  <div className="inara-intro-avatar-wrapper position-relative mx-auto my-3" id="inaraIntroAvatarWrapper">
                    <div className="inara-halo"></div>
                    <img
                      id="introAvatarImg"
                      className="inara-avatar-img inara-waving"
                      src={urls.wave || urls.idle || undefined}
                      alt={avatarName}
                    />
                  </div>

                  {/* Live Spoken Captions Card */}
                  <div className="intro-captions-card p-3 rounded-4 shadow mx-auto mb-3" style={{ maxWidth: '650px', background: 'rgba(0, 0, 0, 0.55)', backdropFilter: 'blur(12px)', border: '1.5px solid #D4AF37' }}>
                    <div className="d-flex align-items-center justify-content-center gap-2 mb-1">
                      <span className="badge" style={{ background: '#D4AF37', color: '#064E3B', fontWeight: 800, fontSize: '0.72rem' }}>
                        <i className="bi bi-chat-quote-fill me-1"></i> {avatarName}
                      </span>
                      <span className="small text-white-50">Teacher Introduction</span>
                    </div>
                    <p id="introCaptionsText" className="text-white small mb-0 fw-medium" style={{ lineHeight: 1.6 }}>
                      &quot;{data.intro_display}&quot;
                    </p>
                  </div>

                  {/* Action Buttons */}
                  <div className="d-flex align-items-center justify-content-center gap-3">
                    <button type="button" id="btnStartIntro" className="btn btn-golden fw-bold rounded-pill px-4 py-2 shadow-lg">
                      <i className="bi bi-play-fill fs-5 me-1 align-middle"></i> Start Introduction
                    </button>
                    <button type="button" id="btnSkipIntro" className="btn btn-outline-light rounded-pill px-3 py-2 shadow">
                      <i className="bi bi-skip-forward-fill me-1"></i> Skip Intro
                    </button>
                  </div>
                </div>
              </div>

              {/* 2. INARA CORNER LECTURE AVATAR WIDGET (BOTTOM-RIGHT) */}
              <div id="aiTeacherAvatarContainer" className="ai-teacher-avatar-badge-wrapper">
                <div id="inaraLectureAvatarContainer" className="inara-corner-badge is-hidden ai-teacher-avatar-badge" title={`${avatarName} presenting the lecture`}>
                  <div className="avatar-inner-flex">
                    <div className="inara-corner-img-box">
                      <img
                        id="lectureCornerAvatarImg"
                        className="inara-breathing"
                        src={urls.idle || undefined}
                        alt={avatarName}
                      />
                    </div>

                    {/* Built-in SVG Cartoon Avatar fallback / placeholder definition */}
                    <div className="d-none" id="avatarPlaceholderSvgDef">
                      <svg id="teacherAvatarSvg" viewBox="0 0 120 130" width="72" height="80" xmlns="http://www.w3.org/2000/svg">
                        <defs>
                          <linearGradient id="hijabGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="#106E53" />
                            <stop offset="100%" stopColor="#064E3B" />
                          </linearGradient>
                          <linearGradient id="goldTrim" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#D4AF37" />
                            <stop offset="100%" stopColor="#B8860B" />
                          </linearGradient>
                        </defs>
                        <path d="M 22 125 C 22 62, 30 18, 60 18 C 90 18, 98 62, 98 125 C 84 129, 36 129, 22 125 Z" fill="url(#hijabGrad)" />
                        <g id="avatarHeadGroup">
                          <path d="M 38 48 C 50 38, 70 38, 82 48 C 74 42, 46 42, 38 48 Z" fill="url(#goldTrim)" />
                          <path d="M 39 52 C 39 36, 81 36, 81 52 C 81 80, 72 96, 60 96 C 48 96, 39 80, 39 52 Z" fill="#FDDEC7" />
                          <g id="avatarMouthGroup">
                            <path className="avatar-mouth-idle" d="M 54 84 Q 60 89 66 84" stroke="#DC2626" strokeWidth="2.2" fill="none" strokeLinecap="round" />
                          </g>
                        </g>
                      </svg>
                    </div>

                    <div className="avatar-info-box">
                      <div className="d-flex align-items-center gap-1 mb-1">
                        <span className="avatar-live-dot"></span>
                        <span className="avatar-title-label">{avatarName} &bull; AI Teacher</span>
                      </div>
                      <div className="avatar-speech-status">
                        <div className="mini-sound-bars">
                          <span></span><span></span><span></span><span></span>
                        </div>
                        <span id="avatarSpeechText" className="avatar-speech-msg">Ready to teach</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating Teacher Live Subtitles Banner */}
              <div className="floating-caption-bar shadow-sm" id="captionBar">
                <div className="d-flex align-items-center gap-2">
                  <span className="badge rounded-pill bg-warning text-dark px-2 py-1 small fw-bold">
                    <i className="bi bi-volume-up-fill me-1"></i> Teacher Voice
                  </span>
                  <p className="mb-0 text-white small fw-normal text-truncate-2" id="captionText">
                    Welcome to today&apos;s masterclass presentation. Click Play or &apos;Audio Explanation&apos; to listen.
                  </p>
                </div>
              </div>

            </div>

            {/* Slide Progress Scrubber Bar */}
            <div className="progress rounded-0" id="slideProgressWrapper" style={{ height: '5px', background: '#e2e8f0' }}>
              <div id="slideProgressBar" className="progress-bar" role="progressbar" style={{ width: '14%', background: 'linear-gradient(90deg, #D4AF37, #106E53)', transition: 'width 0.4s ease' }}></div>
            </div>

            {/* Player Control Bar */}
            <div className="card-footer bg-light border-0 py-3 px-3 px-md-4" id="slideControlFooter">
              <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">

                {/* Playback Controls */}
                <div className="d-flex align-items-center gap-2">
                  <button id="prevSlideBtn" className="btn btn-sm btn-outline-dark rounded-circle control-icon-btn" title="Previous Slide (Left Arrow)">
                    <i className="bi bi-chevron-left"></i>
                  </button>

                  <button id="mainPlayPauseBtn" className="btn btn-golden rounded-circle shadow-sm d-flex align-items-center justify-content-center" style={{ width: '44px', height: '44px' }} title="Play / Pause Audio (Spacebar)">
                    <i id="mainPlayIcon" className="bi bi-play-fill fs-4 text-dark ms-1"></i>
                  </button>

                  <button id="nextSlideBtn" className="btn btn-sm btn-outline-dark rounded-circle control-icon-btn" title="Next Slide (Right Arrow)">
                    <i className="bi bi-chevron-right"></i>
                  </button>

                  <button id="replaySlideBtn" className="btn btn-sm btn-outline-secondary rounded-circle control-icon-btn ms-1" title="Replay Current Slide">
                    <i className="bi bi-arrow-repeat"></i>
                  </button>

                  <span id="videoTimeCounter" className="small fw-bold text-secondary font-monospace ms-2" style={{ fontSize: '0.85rem' }}>00:00 / 00:56</span>
                </div>

                {/* Dynamic Slide Navigation Dots / Pills */}
                <div className="d-flex align-items-center gap-1 flex-wrap justify-content-center" id="slideDotsContainer">
                  {/* Populated dynamically by JavaScript */}
                </div>

                {/* Audio & Screen Controls */}
                <div className="d-flex align-items-center gap-2">
                  {/* Closed Captions Toggle Button */}
                  <button id="captionsToggleBtn" className="btn btn-sm btn-golden rounded-circle control-icon-btn shadow-sm" title="Toggle Closed Captions (Subtitles)">
                    <i className="bi bi-chat-quote-fill"></i>
                  </button>

                  {/* Speed dropdown */}
                  <div className="dropdown">
                    <button className="btn btn-sm btn-outline-secondary dropdown-toggle rounded-pill fw-semibold px-2" type="button" data-bs-toggle="dropdown" id="speedBtn">
                      <i className="bi bi-speedometer2 me-1"></i><span id="speedLabel">1.0x</span>
                    </button>
                    <ul className="dropdown-menu dropdown-menu-end shadow-sm">
                      <li><a className="dropdown-item speed-option" href="#" data-speed="0.75">0.75x (Slower)</a></li>
                      <li><a className="dropdown-item speed-option active" href="#" data-speed="1.0">1.0x (Normal)</a></li>
                      <li><a className="dropdown-item speed-option" href="#" data-speed="1.25">1.25x (Fast)</a></li>
                      <li><a className="dropdown-item speed-option" href="#" data-speed="1.5">1.5x (Faster)</a></li>
                    </ul>
                  </div>

                  {/* Mute / Unmute Button */}
                  <button id="muteToggleBtn" className="btn btn-sm btn-outline-secondary rounded-circle control-icon-btn" title="Toggle Audio Voice">
                    <i id="muteIcon" className="bi bi-volume-up-fill"></i>
                  </button>

                  {/* Fullscreen Button */}
                  <button id="fullscreenBtn" className="btn btn-sm btn-outline-secondary rounded-circle control-icon-btn" title="Fullscreen Presentation" onClick={toggleFullscreen}>
                    <i className="bi bi-fullscreen"></i>
                  </button>
                </div>

              </div>
            </div>

          </div>
        </div>

        {/* COLUMN 2: LIVE SLIDE EXPLANATION (CONCEALED INTO DRAWER OVERLAY AS REQUESTED) */}
        <div className="col-xl-5 col-lg-5 d-none" id="slideExplanationColumn" ref={rawStyle('display: none !important;')}>
          <div className="card border-0 shadow-lg h-100 rounded-4 overflow-hidden d-flex flex-column explanation-panel-card" id="slideExplanationCard" ref={rawStyle('border: 2px solid #D4AF37 !important; background: #ffffff;')}>

            {/* Explanation Panel Header */}
            <div className="card-header bg-white border-bottom border-warning-subtle py-3 px-3 px-md-4 d-flex justify-content-between align-items-center gap-2">
              <div className="d-flex align-items-center gap-2">
                <span className="badge" style={{ background: '#064E3B', color: '#D4AF37', fontSize: '0.82rem', padding: '6px 12px', borderRadius: '8px' }}>
                  <i className="bi bi-file-text-fill text-warning me-1"></i> Slide <span id="textExpSlideNum">1</span> Explanation
                </span>
                <h6 className="mb-0 fw-bold text-success text-truncate" id="textExpSlideTitle" style={{ maxWidth: '220px' }}>Core Concepts</h6>
              </div>
              <button type="button" className="btn btn-sm btn-golden fw-bold rounded-pill px-3 shadow-sm d-flex align-items-center gap-1" id="btnSideAudio" onClick={callGlobal('playCurrentSlideVoice')}>
                <i className="bi bi-volume-up-fill"></i> <span id="btnSideAudioLabel">Listen Audio</span>
              </button>
            </div>

            {/* Explanation Scrollable Body with Clean Structured Text Cards */}
            <div className="card-body p-3 p-md-4 d-flex flex-column gap-3 explanation-scroll-container flex-grow-1" style={{ background: '#fdfcf9' }}>

              {/* 1. Simple Concept Explanation in Text */}
              <div className="card border-0 shadow-sm rounded-4 p-3 bg-white" ref={rawStyle('border-left: 4.5px solid #064E3B !important; border: 1.5px solid #e2e8f0;')}>
                <div className="d-flex align-items-center gap-2 mb-2">
                  <span className="badge rounded-circle p-2" style={{ background: '#f0fdf4', color: '#064E3B' }}><i className="bi bi-lightbulb-fill fs-5"></i></span>
                  <h6 className="fw-bold mb-0 text-success">1. Simple Concept Explanation</h6>
                </div>
                <div className="small text-secondary" id="textExpConcept" style={{ lineHeight: 1.7, fontSize: '0.93rem', whiteSpace: 'pre-line' }}>
                  {/* Injected dynamically by JavaScript for current slide */}
                </div>
              </div>

              {/* 2. Real-World Practical Example in Text */}
              <div className="card border-0 shadow-sm rounded-4 p-3" ref={rawStyle('background: #FEF9E7; border: 1.8px solid #D4AF37 !important;')}>
                <div className="d-flex align-items-center gap-2 mb-2">
                  <span className="badge rounded-circle p-2" style={{ background: '#064E3B', color: '#D4AF37' }}><i className="bi bi-building-fill-check fs-5"></i></span>
                  <h6 className="fw-bold mb-0 text-dark">2. Real-World Practical Example</h6>
                </div>
                <div className="small text-dark" id="textExpExample" style={{ lineHeight: 1.7, fontSize: '0.93rem', whiteSpace: 'pre-line' }}>
                  {/* Injected dynamically by JavaScript for current slide */}
                </div>
              </div>

              {/* 3. Key Takeaway Rule in Text */}
              <div className="p-3 rounded-4 shadow-sm d-flex flex-column gap-2" style={{ background: 'linear-gradient(135deg, #064E3B, #106E53)', color: '#ffffff', border: '1.5px solid #D4AF37' }}>
                <div className="d-flex align-items-center gap-2">
                  <i className="bi bi-bookmark-star-fill text-warning fs-5"></i>
                  <span className="badge bg-warning text-dark fw-bold">KEY TAKEAWAY</span>
                </div>
                <div className="small fw-semibold text-light" id="textExpTakeaway" style={{ lineHeight: 1.6, fontSize: '0.9rem' }}>
                  {/* Injected dynamically by JavaScript for current slide */}
                </div>
              </div>

              {/* Audio Explanation Info Box */}
              <div className="p-3 rounded-3 border bg-white small text-muted d-flex align-items-center justify-content-between">
                <div className="d-flex align-items-center gap-2">
                  <i className="bi bi-headphones text-success fs-5"></i>
                  <span>Audio Voice: <strong>gTTS Synthesized Speech</strong></span>
                </div>
                <button type="button" className="btn btn-sm btn-outline-success rounded-pill fw-semibold" onClick={callGlobal('playCurrentSlideVoice')}>
                  <i className="bi bi-play-circle-fill me-1"></i> Audio Explanation
                </button>
              </div>

            </div>

          </div>
        </div>

      </div>

    </div>
  );
});

export default function DailyLessonPage() {
  const { lessonId } = useParams();
  const { data, ready, notFound } = usePageData(`/lessons/${lessonId}/`);
  usePageAssets({ css });

  if (notFound) return <NotFoundPage />;
  if (!ready) return <AdminLoader />;
  // Keyed by lesson so navigating to another lesson builds a fresh player on fresh DOM.
  return <LessonPlayer key={data.lesson.id} data={data} />;
}
