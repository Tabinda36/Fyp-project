/**
 * ALVIX Inara Lesson Player & Animated Teacher Avatar Engine
 * -------------------------------------------------------------
 * Modular Components:
 *   1. AvatarPlayer: Frame preloading, swapping (idle, wave, blink, mouth_open),
 *      CSS transforms (waving tilt, breathing scale, head tilt), reduced-motion support.
 *   2. IntroSequence: Center-stage 10-second introduction sequence with ALVIX branding,
 *      TTS speech (using phonetic pronunciation), live captions, skip button,
 *      and smooth 1s auto-transition to the slides.
 *   3. LecturePlayer: Cinematic full-width presentation player, corner avatar placement,
 *      slide skipping prevention (students cannot skip forward until narration ends),
 *      rendering for all dynamic slides (13+ slides), Web Audio / Web Speech mouth sync,
 *      drawer explanation synchronization, and watch-time telemetry.
 */

class AvatarPlayer {
    constructor(config = {}) {
        this.config = config;
        this.avatarName = config.avatar_name || "Inara";
        this.assets = config.assets || {};
        this.hasCustomAvatar = !!config.has_custom_avatar;
        this.currentFrame = 'idle';
        this.isWaving = false;
        this.isBlinking = false;
        this.isSpeaking = false;
        this.isPaused = false;
        this.waveTimer = null;
        this.blinkTimeout = null;
        this.blinkResetTimeout = null;
        this._destroyed = false;
        this.preloadedImages = {};
        this.registeredElements = [];

        // Check prefers-reduced-motion
        this.prefersReducedMotion = false;
        try {
            if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                this.prefersReducedMotion = true;
            }
        } catch (e) {}

        this.init();
    }

    init() {
        this.preloadFrames();
        this.startBlinkLoop();
    }

    preloadFrames() {
        const frameKeys = ['idle', 'wave', 'blink', 'mouth_open'];
        frameKeys.forEach(key => {
            const url = this.assets[key];
            if (url) {
                const img = new Image();
                img.src = url;
                this.preloadedImages[key] = img;
            }
        });
    }

    registerElement(imgEl, role = 'corner') {
        if (!imgEl) return;
        if (!this.registeredElements.some(item => item.el === imgEl)) {
            this.registeredElements.push({ el: imgEl, role });
            this.updateElement(imgEl, this.currentFrame);
            if (!this.prefersReducedMotion && role === 'corner') {
                imgEl.classList.add('inara-breathing');
            }
        }
    }

    setFrame(frameKey) {
        if (this._destroyed) return;
        this.currentFrame = frameKey;
        this.registeredElements.forEach(item => {
            this.updateElement(item.el, frameKey);
        });
    }

    updateElement(imgEl, frameKey) {
        if (!imgEl) return;
        // Fallback rule: if frame is missing, fallback to idle
        const targetUrl = this.assets[frameKey] || this.assets['idle'];
        if (targetUrl && imgEl.src !== targetUrl) {
            imgEl.src = targetUrl;
        }
    }

    startWaving() {
        if (this.isWaving) return;
        this.isWaving = true;
        let toggle = false;

        this.registeredElements.forEach(item => {
            if (!this.prefersReducedMotion) {
                item.el.classList.add('inara-waving');
            }
        });

        clearInterval(this.waveTimer);
        this.waveTimer = setInterval(() => {
            if (this.isPaused) return;
            toggle = !toggle;
            if (toggle) {
                this.setFrame('wave');
            } else {
                this.setFrame(this.isSpeaking ? 'mouth_open' : 'idle');
            }
        }, 450);
    }

    stopWaving() {
        this.isWaving = false;
        clearInterval(this.waveTimer);
        this.registeredElements.forEach(item => {
            item.el.classList.remove('inara-waving');
        });
        this.setFrame(this.isSpeaking ? 'mouth_open' : 'idle');
    }

    startBlinkLoop() {
        const scheduleNext = () => {
            if (this._destroyed) return;
            // Blink every 3 to 5 seconds
            const delay = Math.random() * 2000 + 3000;
            this.blinkTimeout = setTimeout(() => {
                if (!this.isPaused && !this.isWaving) {
                    this.setFrame('blink');
                    this.blinkResetTimeout = setTimeout(() => {
                        if (!this.isWaving) {
                            this.setFrame(this.isSpeaking ? 'mouth_open' : 'idle');
                        }
                        scheduleNext();
                    }, 150);
                } else {
                    scheduleNext();
                }
            }, delay);
        };
        scheduleNext();
    }

    setSpeaking(speaking) {
        if (this._destroyed) return;
        this.isSpeaking = speaking;
        const cornerBadge = document.getElementById('inaraLectureAvatarContainer') || document.getElementById('aiTeacherAvatarContainer');
        const speechMsg = document.getElementById('avatarSpeechText');

        if (speaking) {
            if (cornerBadge) cornerBadge.classList.add('is-speaking');
            if (speechMsg) speechMsg.innerText = `${this.avatarName} Lecturing...`;
            if (!this.isWaving) this.setFrame('mouth_open');
        } else {
            if (cornerBadge) cornerBadge.classList.remove('is-speaking');
            if (speechMsg) speechMsg.innerText = "Ready to teach";
            if (!this.isWaving) this.setFrame('idle');
        }
    }

    setHeadTilt(direction) {
        if (this.prefersReducedMotion) return;
        this.registeredElements.forEach(item => {
            item.el.classList.remove('inara-tilt-left', 'inara-tilt-right');
            if (direction === 'left') item.el.classList.add('inara-tilt-left');
            if (direction === 'right') item.el.classList.add('inara-tilt-right');
        });
        setTimeout(() => {
            this.registeredElements.forEach(item => {
                item.el.classList.remove('inara-tilt-left', 'inara-tilt-right');
            });
        }, 650);
    }

    pause() {
        this.isPaused = true;
        this.setSpeaking(false);
        this.registeredElements.forEach(item => {
            item.el.style.animationPlayState = 'paused';
        });
    }

    resume() {
        this.isPaused = false;
        this.registeredElements.forEach(item => {
            item.el.style.animationPlayState = 'running';
        });
    }

    // Teardown for single-page apps (React unmount). Stops every timer; no visual change.
    destroy() {
        this._destroyed = true;
        clearInterval(this.waveTimer);
        clearTimeout(this.blinkTimeout);
        clearTimeout(this.blinkResetTimeout);
        this.registeredElements = [];
    }
}


class IntroSequence {
    constructor(avatarPlayer, config = {}, onComplete = null) {
        this.avatar = avatarPlayer;
        this.config = config;
        this.onComplete = onComplete;
        this.isCompleted = false;
        this.introTimer = null;
        this.autoStartTimer = null;
        this.speakRetryTimer = null;
        this.stageHideTimer = null;
        this._destroyed = false;
        this._onStartClick = (e) => {
            e.stopPropagation();
            this.play();
        };
        this._onSkipClick = (e) => {
            e.stopPropagation();
            this.finishIntro(true);
        };

        this.stageEl = document.getElementById('inaraIntroStage');
        this.avatarWrapper = document.getElementById('inaraIntroAvatarWrapper');
        this.captionsBox = document.getElementById('introCaptionsText');
        this.btnStart = document.getElementById('btnStartIntro');
        this.btnSkip = document.getElementById('btnSkipIntro');
        this.cornerContainer = document.getElementById('inaraLectureAvatarContainer') || document.getElementById('aiTeacherAvatarContainer');

        this.spokenText = config.intro_spoken || "";
        this.displayText = config.intro_display || "";
        this.avatarNameSpoken = config.avatar_name_spoken || config.avatar_name || "Inara";

        this.init();
    }

    init() {
        if (this.btnStart) {
            this.btnStart.addEventListener('click', this._onStartClick);
        }
        if (this.btnSkip) {
            this.btnSkip.addEventListener('click', this._onSkipClick);
        }

        // Auto-start intro 600ms after load
        this.autoStartTimer = setTimeout(() => {
            if (!this.isCompleted) {
                this.play();
            }
        }, 600);
    }

    play() {
        if (this.isCompleted) return;
        if (this.btnStart) {
            this.btnStart.classList.add('d-none');
        }
        if (this.captionsBox) {
            this.captionsBox.innerText = `"${this.displayText}"`;
        }

        // Start waving animation & mouth sync
        this.avatar.startWaving();
        this.avatar.setSpeaking(true);

        // Strict 10-second intro rule: Inara introduces herself in 10 seconds of lecture start,
        // then transitions automatically to the slides!
        if (this.introTimer) clearTimeout(this.introTimer);
        this.introTimer = setTimeout(() => {
            this.finishIntro(false);
        }, 10000);

        this.speakText(this.spokenText, () => {
            if (this.introTimer) clearTimeout(this.introTimer);
            this.finishIntro(false);
        });
    }

    speakText(text, onEnded) {
        if (!('speechSynthesis' in window)) {
            setTimeout(onEnded, 4500);
            return;
        }

        try {
            window.speechSynthesis.cancel();
            if (window.speechSynthesis.paused) {
                window.speechSynthesis.resume();
            }
        } catch (e) {}

        const executeSpeak = () => {
            if (this._destroyed) return;
            const utterance = new SpeechSynthesisUtterance(text);
            const voices = window.speechSynthesis.getVoices();

            // Prioritize natural female English voices
            const isFemale = (v) => {
                const n = (v.name || '').toLowerCase();
                if (['david', 'guy', 'george', 'mark', 'michael', 'paul', 'james'].some(m => n.includes(m))) return false;
                return ['female', 'jenny', 'aria', 'zira', 'samantha', 'victoria', 'karen', 'moira', 'natural', 'google us english'].some(h => n.includes(h));
            };

            const selectedVoice = voices.find(v => v.lang.startsWith('en') && isFemale(v)) ||
                                  voices.find(v => v.lang.startsWith('en') && !['david', 'guy'].some(m => (v.name||'').toLowerCase().includes(m))) ||
                                  voices.find(v => v.lang.startsWith('en')) ||
                                  voices[0];

            if (selectedVoice) utterance.voice = selectedVoice;
            utterance.rate = 1.05; // Slightly brisk pacing to fit smoothly within 10s
            utterance.pitch = 1.05;

            // Word-boundary mouth sync
            let mouthTimer = null;
            utterance.onboundary = (e) => {
                if (this._destroyed) return;
                if (e.name === 'word') {
                    const introImg = document.getElementById('introAvatarImg');
                    if (introImg) {
                        this.avatar.updateElement(introImg, 'mouth_open');
                        clearTimeout(mouthTimer);
                        mouthTimer = setTimeout(() => {
                            this.avatar.updateElement(introImg, 'wave');
                        }, 130);
                    }
                }
            };

            utterance.onend = () => {
                if (this._destroyed) return;
                this.avatar.setSpeaking(false);
                this.avatar.stopWaving();
                if (onEnded) onEnded();
            };

            utterance.onerror = (err) => {
                if (this._destroyed) return;
                console.warn("SpeechSynthesis notice during intro:", err);
                this.avatar.setSpeaking(false);
                this.avatar.stopWaving();
                if (onEnded) onEnded();
            };

            try {
                window.speechSynthesis.speak(utterance);
            } catch (err) {
                if (onEnded) onEnded();
            }
        };

        const voices = window.speechSynthesis.getVoices();
        if (!voices || voices.length === 0) {
            window.speechSynthesis.onvoiceschanged = () => {
                executeSpeak();
                window.speechSynthesis.onvoiceschanged = null;
            };
            this.speakRetryTimer = setTimeout(executeSpeak, 250);
        } else {
            executeSpeak();
        }
    }

    finishIntro(skipped = false) {
        if (this.isCompleted) return;
        this.isCompleted = true;

        if (this.introTimer) {
            clearTimeout(this.introTimer);
            this.introTimer = null;
        }

        if (skipped && 'speechSynthesis' in window) {
            try { window.speechSynthesis.cancel(); } catch (e) {}
        }

        this.avatar.stopWaving();
        this.avatar.setSpeaking(false);

        // Smooth 1-second transition: Inara shrinks and moves from center to bottom-right corner
        if (this.stageEl) {
            this.stageEl.classList.add('inara-stage-transitioning');
            this.stageHideTimer = setTimeout(() => {
                this.stageEl.classList.add('d-none');
            }, 950);
        }

        if (this.cornerContainer) {
            this.cornerContainer.classList.remove('is-hidden');
            this.cornerContainer.classList.remove('d-none');
        }

        if (this.onComplete) {
            this.onComplete();
        }
    }

    // Teardown for single-page apps (React unmount): stops speech and timers, removes listeners.
    destroy() {
        this._destroyed = true;
        this.isCompleted = true;
        clearTimeout(this.introTimer);
        clearTimeout(this.autoStartTimer);
        clearTimeout(this.speakRetryTimer);
        clearTimeout(this.stageHideTimer);
        if (this.btnStart) this.btnStart.removeEventListener('click', this._onStartClick);
        if (this.btnSkip) this.btnSkip.removeEventListener('click', this._onSkipClick);
        if ('speechSynthesis' in window) {
            try {
                window.speechSynthesis.onvoiceschanged = null;
                window.speechSynthesis.cancel();
            } catch (e) {}
        }
    }
}


class LecturePlayer {
    constructor(avatarPlayer, options = {}) {
        this.avatar = avatarPlayer;
        this.slidesList = options.slidesList || [];
        this.lessonTitle = options.lessonTitle || "Masterclass Lecture";
        this.courseTitle = options.courseTitle || "Academic Course";
        this.dayNum = options.dayNum || 1;
        this.csrfToken = options.csrfToken || "";
        this.watchTimeUrl = options.watchTimeUrl || "";

        this.totalSlides = Math.max(1, this.slidesList.length || 13);
        this.currentIdx = 0;
        this.isPlaying = false;
        this.isMuted = false;
        this.playbackSpeed = 1.0;
        this.autoAdvanceTimeout = null;
        this.watchdogTimer = null;
        this.mutedTickerTimer = null;
        // Narration session id. Jumping to a slide cancels the old speech; the browser then fires
        // the old utterance's onerror/onend *after* the jump, which used to count as "slide
        // finished" and auto-advance again (and again), so a jump never landed on the chosen slide.
        // Handlers of a superseded narration compare their id and do nothing.
        this.narrationId = 0;

        // Slide skipping prevention:
        // Student CANNOT skip forward until narration ends for current slide
        this.completedSlides = new Set();
        this.canAdvance = false;

        // Native HTML5 Audio & Web Audio API
        this.lectureAudio = new Audio();
        this.lectureAudio.preload = 'auto';
        this.audioCtx = null;
        this.analyser = null;
        this.sourceNode = null;
        this.rafId = null;

        // Estimated slide durations
        this.slideDurations = this.slidesList.map(s => {
            const words = (s.narration || '').split(/\s+/).filter(Boolean).length;
            return Math.max(12.0, Math.round((words / 2.3) * 10) / 10 + 2.0);
        });
        if (this.slideDurations.length === 0) {
            this.slideDurations = [12.0];
        }
        this.totalDurationSeconds = Math.max(60, this.slideDurations.reduce((a, b) => a + b, 0));

        // UI references
        this.slideViewport = document.getElementById('slideViewport');
        this.playOverlay = document.getElementById('playOverlay');
        this.mainPlayPauseBtn = document.getElementById('mainPlayPauseBtn');
        this.mainPlayIcon = document.getElementById('mainPlayIcon');
        this.prevSlideBtn = document.getElementById('prevSlideBtn');
        this.nextSlideBtn = document.getElementById('nextSlideBtn');
        this.replaySlideBtn = document.getElementById('replaySlideBtn');
        this.currentSlideNum = document.getElementById('currentSlideNum');
        this.totalSlidesNum = document.getElementById('totalSlidesNum');
        this.slideProgressBar = document.getElementById('slideProgressBar');
        this.videoTimeCounter = document.getElementById('videoTimeCounter');
        this.soundWave = document.getElementById('soundWave');
        this.playerStatus = document.getElementById('playerStatus');
        this.captionText = document.getElementById('captionText');
        this.muteToggleBtn = document.getElementById('muteToggleBtn');
        this.muteIcon = document.getElementById('muteIcon');
        this.completionOverlay = document.getElementById('completionOverlay');
        this.replayFullBtn = document.getElementById('replayFullBtn');
        this.speedLabel = document.getElementById('speedLabel');
        this.captionsToggleBtn = document.getElementById('captionsToggleBtn');
        this.captionBar = document.getElementById('captionBar');

        // Watch-Time Tracking
        this.lastActivityTime = Date.now();
        this.accumulatedWatchSec = 0;
        this.watchTimeInterval = null;

        // Registered DOM listeners, removed by destroy()
        this._listeners = [];
        this._destroyed = false;

        this.init();
    }

    _listen(target, type, handler, options) {
        target.addEventListener(type, handler, options);
        this._listeners.push([target, type, handler, options]);
    }

    init() {
        if (this.totalSlidesNum) this.totalSlidesNum.innerText = this.totalSlides;
        this.bindEvents();
        this.setupAudioAnalysis();
        this.setupWatchTimeTracker();
        this.buildSlideDots();
        this.renderSlide(0);
        this.updateSlideNavigationState();
        this.updateVideoProgress(0);
    }

    setupAudioAnalysis() {
        try {
            const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtxClass) return;

            const initCtx = () => {
                if (!this.audioCtx) {
                    this.audioCtx = new AudioCtxClass();
                    this.analyser = this.audioCtx.createAnalyser();
                    this.analyser.fftSize = 256;
                    this.sourceNode = this.audioCtx.createMediaElementSource(this.lectureAudio);
                    this.sourceNode.connect(this.analyser);
                    this.analyser.connect(this.audioCtx.destination);
                }
                if (this.audioCtx.state === 'suspended') {
                    this.audioCtx.resume();
                }
            };

            const dataArray = new Uint8Array(128);
            const checkVolume = () => {
                if (!this.isPlaying || this.isMuted || this.lectureAudio.paused || this.lectureAudio.ended) {
                    this.avatar.setFrame('idle');
                    return;
                }
                if (this.analyser) {
                    this.analyser.getByteFrequencyData(dataArray);
                    let sum = 0;
                    for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
                    const avg = sum / dataArray.length;

                    // Swap mouth based on volume threshold
                    if (avg > 18) {
                        this.avatar.setFrame('mouth_open');
                    } else {
                        this.avatar.setFrame('idle');
                    }
                }
                this.rafId = requestAnimationFrame(checkVolume);
            };

            this._listen(this.lectureAudio, 'play', () => {
                initCtx();
                cancelAnimationFrame(this.rafId);
                this.rafId = requestAnimationFrame(checkVolume);
            });

            this._listen(this.lectureAudio, 'pause', () => {
                cancelAnimationFrame(this.rafId);
                this.avatar.setFrame('idle');
            });

            this._listen(this.lectureAudio, 'ended', () => {
                cancelAnimationFrame(this.rafId);
                this.avatar.setFrame('idle');
                if (this.isPlaying) this.onSlideFinished();
            });

            this._listen(this.lectureAudio, 'timeupdate', () => {
                if (!this.isPlaying || this.isMuted) return;
                this.updateVideoProgress(this.lectureAudio.currentTime);
            });

            this._listen(this.lectureAudio, 'error', (e) => {
                // Ignore errors from a source we already left (e.g. src cleared on teardown/jump).
                if (this._destroyed || !this.isPlaying || !this.lectureAudio.getAttribute('src')) return;
                console.warn("Lecture audio file failed to load, switching to speech fallback:", e);
                const slide = this.slidesList[this.currentIdx] || {};
                this.playWithWebSpeech(slide.narration || '');
            });
        } catch (e) {
            console.warn("Web Audio API AnalyserNode note:", e);
        }
    }

    playTransitionChime() {
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (!AudioCtx) return;
            const ctx = new AudioCtx();
            if (ctx.state === 'suspended') ctx.resume();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'sine';
            osc.frequency.setValueAtTime(520, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(780, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.06, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.18);
            osc.start();
            osc.stop(ctx.currentTime + 0.2);
        } catch (e) {}
    }

    updateSlideNavigationState() {
        // Full Slide Jumping: student can freely jump between any slides!
        if (this.nextSlideBtn) {
            const isLast = (this.currentIdx >= this.totalSlides - 1);
            this.nextSlideBtn.disabled = isLast;
            this.nextSlideBtn.classList.toggle('disabled', isLast);
            this.nextSlideBtn.classList.toggle('opacity-50', isLast);
            this.nextSlideBtn.style.cursor = isLast ? 'default' : 'pointer';
            this.nextSlideBtn.title = isLast ? 'Final slide reached' : 'Jump to Next Slide';
        }

        if (this.prevSlideBtn) {
            const isFirst = (this.currentIdx === 0);
            this.prevSlideBtn.disabled = isFirst;
            this.prevSlideBtn.classList.toggle('disabled', isFirst);
            this.prevSlideBtn.classList.toggle('opacity-50', isFirst);
            this.prevSlideBtn.style.cursor = isFirst ? 'default' : 'pointer';
            this.prevSlideBtn.title = isFirst ? 'First slide' : 'Jump to Previous Slide';
        }

        // All slide dots are clickable and jump directly to that slide!
        const dots = document.querySelectorAll('.slide-dot');
        dots.forEach((dot, idx) => {
            dot.classList.toggle('active', idx === this.currentIdx);
            dot.classList.remove('locked', 'opacity-50');
            dot.style.cursor = 'pointer';
            dot.title = `Jump to Slide ${idx + 1}`;
        });
    }

    showSkipLockedToast() {
        if (this.playerStatus) {
            this.playerStatus.innerHTML = `<span class="text-danger fw-bold"><i class="bi bi-lock-fill me-1"></i>Please listen to the current slide narration before advancing</span>`;
            setTimeout(() => {
                if (this.playerStatus) {
                    this.playerStatus.innerText = this.isPlaying ? `${this.avatar.avatarName} Lecturing (Slide ${this.currentIdx + 1} of ${this.totalSlides})` : `Slide ${this.currentIdx + 1} of ${this.totalSlides}`;
                }
            }, 3000);
        }
    }

    renderSlide(idx) {
        if (!this.slidesList || this.slidesList.length === 0) return;
        const slide = this.slidesList[idx] || {};
        const type = slide.type || 'cover';

        let html = '';

        if (type === 'cover') {
            const pts = slide.key_points || slide.bullet_points || slide.points || [];
            let ptsHtml = '';
            if (pts.length > 0) {
                ptsHtml = `
                    <div class="row g-2 justify-content-center text-start my-2 mx-auto" style="max-width: 780px;">
                        ${pts.map(p => `
                            <div class="col-md-4">
                                <div class="p-2 rounded-3 bg-black bg-opacity-25 border border-warning border-opacity-25 text-light small h-100">
                                    <i class="bi bi-check2-circle text-warning me-1"></i> ${p}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            html = `
                <div class="h-100 d-flex flex-column justify-content-between slide-fade-in text-center p-3 p-md-4 rounded-4" style="background: linear-gradient(135deg, #064E3B 0%, #022C22 100%); border: 3px solid #D4AF37; box-shadow: 0 10px 30px rgba(6,78,59,0.35);">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge px-3 py-1 fw-bold" style="background: #D4AF37; color: #064E3B; font-size: 0.75rem;">
                            ${slide.badge || `ALVIX MASTER LECTURE SERIES • DAY ${this.dayNum}`}
                        </span>
                        <span class="text-white-50 small fw-bold">16:9 MASTERCLASS FORMAT</span>
                    </div>

                    <div class="my-auto py-2">
                        <h1 class="display-6 fw-bold text-white mb-2" style="letter-spacing: -0.5px; text-shadow: 0 2px 10px rgba(0,0,0,0.4);">
                            ${slide.title || this.lessonTitle}
                        </h1>
                        <h5 class="fw-semibold mb-2" style="color: #FEF9E7;">
                            Curriculum Track: ${slide.course_name || this.courseTitle}
                        </h5>
                        <p class="text-white-50 small mx-auto mb-2" style="max-width: 680px;">
                            ${slide.subtitle || 'Comprehensive University Masterclass & Architectural Blueprint'}
                        </p>
                        ${ptsHtml}
                    </div>

                    <div class="text-white-50 small border-top border-warning border-opacity-25 pt-2 d-flex justify-content-between">
                        <span>ALVIX AI ACADEMY</span>
                        <span>DAY ${this.dayNum}: ${this.lessonTitle}</span>
                    </div>
                </div>
            `;
        } else if (type === 'concepts' || (slide.concept_1 && slide.concept_2)) {
            const c1 = slide.concept_1 || { name: 'Core Foundations', points: [] };
            const c2 = slide.concept_2 || { name: 'System Mechanics', points: [] };
            const c3 = slide.concept_3 || { name: 'Contract Enforcement', points: [] };

            html = `
                <div class="h-100 d-flex flex-column justify-content-between slide-fade-in p-3 p-md-4 rounded-4 bg-white" style="border: 2px solid #D4AF37;">
                    <div class="d-flex justify-content-between align-items-center border-bottom pb-2 mb-2">
                        <span class="badge px-3 py-1 fw-bold" style="background: #064E3B; color: #D4AF37;">${slide.badge || 'THEORETICAL FOUNDATIONS'}</span>
                        <span class="badge bg-light text-dark border">Slide ${idx + 1} of ${this.totalSlides}</span>
                    </div>
                    <h4 class="fw-bold text-success mb-3">${slide.title || 'Theoretical Mechanics'}</h4>
                    <div class="row g-3 my-auto">
                        <div class="col-md-4">
                            <div class="card h-100 p-3 bg-light border-0 rounded-3 shadow-xs" style="border-left: 4px solid #064E3B !important;">
                                <h6 class="fw-bold text-success mb-2">${c1.name}</h6>
                                <ul class="list-unstyled mb-0 small text-dark">${(c1.points || []).map(p => `<li class="mb-1">• ${p}</li>`).join('')}</ul>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card h-100 p-3 bg-light border-0 rounded-3 shadow-xs" style="border-left: 4px solid #106E53 !important;">
                                <h6 class="fw-bold text-success mb-2">${c2.name}</h6>
                                <ul class="list-unstyled mb-0 small text-dark">${(c2.points || []).map(p => `<li class="mb-1">• ${p}</li>`).join('')}</ul>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="card h-100 p-3 bg-light border-0 rounded-3 shadow-xs" style="border-left: 4px solid #D4AF37 !important;">
                                <h6 class="fw-bold text-success mb-2">${c3.name}</h6>
                                <ul class="list-unstyled mb-0 small text-dark">${(c3.points || []).map(p => `<li class="mb-1">• ${p}</li>`).join('')}</ul>
                            </div>
                        </div>
                    </div>
                    <div class="text-muted small pt-2 border-top d-flex justify-content-between">
                        <span>Day ${this.dayNum}: ${this.lessonTitle}</span>
                        <span>ALVIX Academic Curriculum</span>
                    </div>
                </div>
            `;
        } else {
            // General Dynamic Slide Renderer (Architecture, Code, Academic, Enterprise, Complexity, Labs, etc.)
            const rawPoints = slide.points || slide.key_points || slide.bullet_points || slide.architecture_layers || slide.learning_objectives || slide.checkpoints || slide.pro_tips || [];
            let pointsHtml = '';
            if (Array.isArray(rawPoints) && rawPoints.length > 0) {
                pointsHtml = rawPoints.map((p, pIdx) => {
                    const textVal = typeof p === 'object' ? (p.name ? `${p.name}: ${(p.points||[]).join(', ')}` : JSON.stringify(p)) : p;
                    return `
                        <li class="d-flex align-items-start gap-2 mb-2 p-2 rounded-2 bg-light border border-light-subtle">
                            <span class="badge rounded-pill bg-success-subtle text-success border border-success fw-bold" style="font-size: 0.75rem;">${pIdx + 1}</span>
                            <span class="text-dark small fw-medium" style="line-height: 1.5;">${textVal}</span>
                        </li>
                    `;
                }).join('');
            } else if (slide.teacher_briefing) {
                pointsHtml = `<div class="p-3 bg-light rounded-3 text-secondary small" style="line-height: 1.6;">${slide.teacher_briefing}</div>`;
            } else {
                pointsHtml = `<div class="p-3 bg-light rounded-3 text-secondary small">Comprehensive exploration and industry best practices for this unit.</div>`;
            }

            const codeVal = slide.code || slide.code_snippet || '';
            const diagramVal = slide.diagram || slide.data_flow || '';
            let rightBlockHtml = '';
            if (codeVal) {
                rightBlockHtml = `
                    <div class="col-lg-6">
                        <div class="rounded-3 shadow-sm overflow-hidden h-100" style="background: #0F172A; border: 1.5px solid #D4AF37;">
                            <div class="d-flex align-items-center justify-content-between px-3 py-1 bg-black bg-opacity-50 border-bottom border-secondary">
                                <span class="text-warning small font-monospace"><i class="bi bi-code-slash me-1"></i>${slide.code_title || 'Blueprint Pattern'}</span>
                                <span class="badge bg-dark text-warning border border-warning" style="font-size: 0.7rem;">Executable</span>
                            </div>
                            <pre class="slide-code-box mb-0 p-3 text-warning font-monospace" style="font-size: 0.82rem; max-height: 270px; overflow-y: auto;">${codeVal}</pre>
                        </div>
                    </div>
                `;
            } else if (diagramVal) {
                rightBlockHtml = `
                    <div class="col-lg-6">
                        <div class="rounded-3 shadow-sm overflow-hidden h-100 p-3 bg-light border border-success-subtle" style="border-left: 4px solid #D4AF37 !important;">
                            <div class="d-flex align-items-center justify-content-between pb-2 mb-2 border-bottom border-secondary-subtle">
                                <span class="text-success fw-bold small"><i class="bi bi-diagram-3-fill me-1 text-warning"></i>Execution Data Flow</span>
                                <span class="badge bg-success-subtle text-success border border-success" style="font-size: 0.7rem;">System Architecture</span>
                            </div>
                            <div class="p-3 bg-white rounded-2 border shadow-sm text-secondary small" style="line-height: 1.6; white-space: pre-line;">
                                <i class="bi bi-bezier2 me-1 text-primary"></i> ${diagramVal}
                            </div>
                        </div>
                    </div>
                `;
            }

            html = `
                <div class="h-100 d-flex flex-column justify-content-between slide-fade-in">
                    <div>
                        <div class="d-flex justify-content-between align-items-center mb-2 pb-1 border-bottom">
                            <span class="badge px-3 py-1 fw-bold" style="background: #064E3B; color: #D4AF37; font-size: 0.75rem;">
                                ${slide.badge || `MODULE ${idx + 1}`}
                            </span>
                            <span class="badge bg-light text-dark border">Slide ${idx + 1} of ${this.totalSlides}</span>
                        </div>
                        <h4 class="fw-bold text-success mb-3">${slide.title || `Concept Exploration ${idx + 1}`}</h4>
                        <div class="row g-3 align-items-stretch">
                            <div class="${(codeVal || diagramVal) ? 'col-lg-6' : 'col-12'}">
                                <ul class="list-unstyled mb-0">${pointsHtml}</ul>
                            </div>
                            ${rightBlockHtml}
                        </div>
                    </div>
                    <div class="border-top pt-2 mt-2 d-flex justify-content-between align-items-center text-muted small">
                        <span>ALVIX Masterclass Series • Day ${this.dayNum}</span>
                        <span>${this.lessonTitle}</span>
                    </div>
                </div>
            `;
        }

        if (this.slideViewport) this.slideViewport.innerHTML = html;
        if (this.currentSlideNum) this.currentSlideNum.innerText = idx + 1;

        const progressPercent = Math.round(((idx + 1) / this.totalSlides) * 100);
        if (this.slideProgressBar) this.slideProgressBar.style.width = `${progressPercent}%`;

        // Update active dot in dots list
        const dots = document.querySelectorAll('.slide-dot');
        dots.forEach((dot, dotIdx) => {
            dot.classList.toggle('active', dotIdx === idx);
        });

        // Update live caption
        if (this.captionText) {
            const narration = slide.narration || `Lecture content for slide ${idx + 1}.`;
            this.captionText.innerText = narration;
        }

        // Synchronize Slide Explanation Drawer with current slide
        if (typeof window.updateExplanationContent === 'function') {
            window.updateExplanationContent(idx);
        }
    }

    playWithWebSpeech(narration) {
        if (this._destroyed) return;
        if (!('speechSynthesis' in window)) {
            const fallbackMs = (this.slideDurations[this.currentIdx] || 8) * 1000;
            clearTimeout(this.autoAdvanceTimeout);
            this.autoAdvanceTimeout = setTimeout(() => {
                if (this.isPlaying) this.onSlideFinished();
            }, fallbackMs);
            return;
        }

        const narrationId = ++this.narrationId;
        const isCurrent = () => !this._destroyed && narrationId === this.narrationId;

        try {
            window.speechSynthesis.cancel();
            if (window.speechSynthesis.paused) {
                window.speechSynthesis.resume();
            }
        } catch (e) {}

        const utterance = new SpeechSynthesisUtterance(narration);
        const voices = window.speechSynthesis.getVoices();

        const isFemale = (v) => {
            const n = (v.name || '').toLowerCase();
            if (['david', 'guy', 'george', 'mark', 'michael', 'paul', 'james'].some(m => n.includes(m))) return false;
            return ['female', 'jenny', 'aria', 'zira', 'samantha', 'victoria', 'karen', 'moira', 'natural', 'google us english'].some(h => n.includes(h));
        };

        const preferredVoice = voices.find(v => v.lang.startsWith('en') && isFemale(v)) ||
                               voices.find(v => v.lang.startsWith('en') && !['david', 'guy'].some(m => (v.name||'').toLowerCase().includes(m))) ||
                               voices.find(v => v.lang.startsWith('en')) ||
                               voices[0];

        if (preferredVoice) utterance.voice = preferredVoice;
        utterance.rate = this.playbackSpeed;
        utterance.pitch = 1.05;

        this.avatar.setSpeaking(true);
        if (this.soundWave) this.soundWave.classList.add('speaking');

        let mouthTimer = null;
        utterance.onboundary = (e) => {
            if (!isCurrent()) return;
            if (e.name === 'word') {
                this.avatar.setFrame('mouth_open');
                clearTimeout(mouthTimer);
                mouthTimer = setTimeout(() => {
                    this.avatar.setFrame('idle');
                }, 130);
            } else if (e.name === 'sentence') {
                this.avatar.setHeadTilt(Math.random() > 0.5 ? 'left' : 'right');
            }
        };

        utterance.onend = () => {
            if (!isCurrent()) return;  // a jump cancelled this narration
            this.avatar.setSpeaking(false);
            if (this.soundWave) this.soundWave.classList.remove('speaking');
            if (this.isPlaying) {
                this.onSlideFinished();
            }
        };

        utterance.onerror = (err) => {
            if (!isCurrent()) return;  // "interrupted"/"canceled" after a jump: not a finished slide
            console.warn("SpeechSynthesis utterance error:", err);
            this.avatar.setSpeaking(false);
            if (this.soundWave) this.soundWave.classList.remove('speaking');
            if (this.isPlaying) {
                this.onSlideFinished();
            }
        };

        const estimatedMs = Math.max(8000, ((narration.split(/\s+/).length / 2.3) / this.playbackSpeed) * 1000 + 1500);
        clearTimeout(this.watchdogTimer);
        this.watchdogTimer = setTimeout(() => {
            if (isCurrent() && this.isPlaying && window.speechSynthesis.speaking) {
                window.speechSynthesis.cancel();
                this.onSlideFinished();
            }
        }, estimatedMs + 10000);

        try {
            window.speechSynthesis.speak(utterance);
        } catch (e) {
            console.warn("speechSynthesis speak failed, triggering fallback:", e);
            setTimeout(() => { if (isCurrent()) this.onSlideFinished(); }, 7000);
        }
    }

    playCurrentSlideAudio() {
        if (this._destroyed) return;
        clearTimeout(this.autoAdvanceTimeout);
        clearTimeout(this.watchdogTimer);
        clearInterval(this.mutedTickerTimer);

        if (!this.isPlaying) return;

        const slide = this.slidesList[this.currentIdx] || {};
        const narration = (slide.narration || `${this.lessonTitle}. Masterclass key concepts for slide ${this.currentIdx + 1}.`).trim();
        const audioUrl = slide.audio_url;

        if (this.captionText) {
            this.captionText.innerText = narration;
        }

        if (this.isMuted) {
            this.avatar.setSpeaking(false);
            if (this.soundWave) this.soundWave.classList.remove('speaking');
            if (this.playerStatus) {
                this.playerStatus.innerText = `Slide ${this.currentIdx + 1} of ${this.totalSlides} (Audio Muted)`;
            }

            const estimatedSec = Math.max(8.0, (narration.split(/\s+/).length / 2.3) / this.playbackSpeed);
            let elapsed = 0;
            this.mutedTickerTimer = setInterval(() => {
                if (!this.isPlaying || !this.isMuted) {
                    clearInterval(this.mutedTickerTimer);
                    return;
                }
                elapsed += 0.5;
                this.updateVideoProgress(elapsed);
                if (elapsed >= estimatedSec) {
                    clearInterval(this.mutedTickerTimer);
                    this.onSlideFinished();
                }
            }, 500);
            return;
        }

        // Try pre-rendered audio URL first, then fallback to Web Speech
        if (audioUrl && audioUrl.length > 5) {
            this.lectureAudio.src = audioUrl;
            this.lectureAudio.playbackRate = this.playbackSpeed;
            this.lectureAudio.currentTime = 0;
            this.avatar.setSpeaking(true);
            if (this.soundWave) this.soundWave.classList.add('speaking');

            const audioNarrationId = ++this.narrationId;
            const playPromise = this.lectureAudio.play();
            if (playPromise !== undefined) {
                playPromise.then(() => {
                    if (audioNarrationId !== this.narrationId) return;
                    if (this.playerStatus) {
                        this.playerStatus.innerText = `${this.avatar.avatarName} Lecturing (Slide ${this.currentIdx + 1} of ${this.totalSlides})`;
                    }
                }).catch(err => {
                    // AbortError from a jump (play() interrupted by pause()) is not a failure.
                    if (audioNarrationId !== this.narrationId || this._destroyed) return;
                    console.warn("Audio element play error, falling back to Web Speech:", err);
                    this.playWithWebSpeech(narration);
                });
            }
        } else {
            this.playWithWebSpeech(narration);
            if (this.playerStatus) {
                this.playerStatus.innerText = `${this.avatar.avatarName} Lecturing (Slide ${this.currentIdx + 1} of ${this.totalSlides})`;
            }

            let startMs = Date.now();
            const durationSec = Math.max(8.0, (narration.split(/\s+/).length / 2.3) / this.playbackSpeed);
            clearInterval(this.mutedTickerTimer);
            this.mutedTickerTimer = setInterval(() => {
                if (!this.isPlaying) {
                    clearInterval(this.mutedTickerTimer);
                    return;
                }
                const sec = (Date.now() - startMs) / 1000;
                this.updateVideoProgress(Math.min(sec, durationSec));
                if (sec >= durationSec) {
                    clearInterval(this.mutedTickerTimer);
                }
            }, 300);
        }
    }

    onSlideFinished() {
        if (this._destroyed) return;
        this.completedSlides.add(this.currentIdx);
        this.canAdvance = true;
        this.updateSlideNavigationState();

        if (this.currentIdx + 1 >= this.totalSlides) {
            this.isPlaying = false;
            this.updatePlayIcon();
            this.avatar.setSpeaking(false);
            this.avatar.setFrame('idle');
            this.updateVideoProgress(this.slideDurations[this.totalSlides - 1] || 7.5);
            if (this.completionOverlay) {
                this.completionOverlay.classList.remove('d-none');
                this.completionOverlay.classList.add('d-flex');
            }
            if (this.playerStatus) {
                this.playerStatus.innerText = "Lecture Finished • Congratulations!";
            }
        } else {
            // Auto advance smoothly to the next slide!
            this.goToSlide(this.currentIdx + 1, true);
        }
    }

    updateVideoProgress(currentSlideSec) {
        let elapsedBefore = 0;
        for (let i = 0; i < this.currentIdx; i++) {
            elapsedBefore += this.slideDurations[i] || 8.0;
        }
        const totalElapsed = elapsedBefore + currentSlideSec;
        const totalDuration = this.totalDurationSeconds;

        const formatMinSec = (s) => {
            const m = Math.floor(s / 60);
            const sec = Math.floor(s % 60);
            return `${m}:${sec < 10 ? '0' : ''}${sec}`;
        };

        if (this.videoTimeCounter) {
            this.videoTimeCounter.innerText = `${formatMinSec(totalElapsed)} / ${formatMinSec(totalDuration)}`;
        }
    }

    updatePlayIcon() {
        if (!this.mainPlayIcon) return;
        if (this.isPlaying) {
            this.mainPlayIcon.className = "bi bi-pause-fill";
            if (this.mainPlayPauseBtn) this.mainPlayPauseBtn.title = "Pause Lesson";
        } else {
            this.mainPlayIcon.className = "bi bi-play-fill";
            if (this.mainPlayPauseBtn) this.mainPlayPauseBtn.title = "Play Lesson";
        }
    }

    goToSlide(targetIdx, keepPlaying) {
        if (targetIdx < 0) targetIdx = 0;
        if (targetIdx >= this.totalSlides) targetIdx = this.totalSlides - 1;

        // Immediately cancel previous slide audio & speech synthesis (and ignore its late events)
        this.narrationId++;
        if (this.lectureAudio && !this.lectureAudio.paused) {
            this.lectureAudio.pause();
        }
        if ('speechSynthesis' in window) {
            try { window.speechSynthesis.cancel(); } catch (e) {}
        }
        clearTimeout(this.autoAdvanceTimeout);
        clearTimeout(this.watchdogTimer);
        clearInterval(this.mutedTickerTimer);

        // Jump to target slide
        this.currentIdx = targetIdx;
        this.completedSlides.add(targetIdx);
        this.renderSlide(this.currentIdx);
        this.updateSlideNavigationState();
        this.updateVideoProgress(0);

        // Synchronize explanation drawer with the jumped slide
        if (typeof window.updateExplanationContent === 'function') {
            window.updateExplanationContent(this.currentIdx);
        }

        if (this.isPlaying || keepPlaying) {
            this.isPlaying = true;
            this.updatePlayIcon();
            this.playCurrentSlideAudio();
        } else {
            if (this.playerStatus) {
                this.playerStatus.innerText = `Slide ${this.currentIdx + 1} of ${this.totalSlides} (Jumped)`;
            }
            if (this.soundWave) this.soundWave.classList.remove('speaking');
        }
    }

    startPlayback() {
        if (this.playOverlay) {
            this.playOverlay.style.opacity = "0";
            setTimeout(() => { this.playOverlay.style.display = "none"; }, 250);
        }
        if (this.completionOverlay) {
            this.completionOverlay.classList.add('d-none');
            this.completionOverlay.classList.remove('d-flex');
        }

        this.isPlaying = true;
        this.avatar.resume();
        this.updatePlayIcon();
        this.playTransitionChime();

        if (this.currentIdx >= this.totalSlides - 1 && this.completedSlides.has(this.currentIdx)) {
            this.goToSlide(0, true);
        } else {
            this.goToSlide(this.currentIdx, true);
        }
    }

    togglePlay() {
        if (this.isPlaying) {
            // Synchronized Pause: Voice, Avatar Animation, and Telemetry pause together!
            this.isPlaying = false;
            this.updatePlayIcon();
            this.avatar.pause();

            if (this.soundWave) this.soundWave.classList.remove('speaking');
            if (this.playerStatus) this.playerStatus.innerText = "Paused";

            if (this.lectureAudio && !this.lectureAudio.paused) {
                this.lectureAudio.pause();
            }
            if ('speechSynthesis' in window) {
                try { window.speechSynthesis.pause(); } catch (e) {}
            }
            clearTimeout(this.autoAdvanceTimeout);
            clearTimeout(this.watchdogTimer);
            clearInterval(this.mutedTickerTimer);
        } else {
            // Synchronized Resume
            this.isPlaying = true;
            this.updatePlayIcon();
            this.avatar.resume();

            if (this.lectureAudio && this.lectureAudio.src && this.lectureAudio.paused && this.lectureAudio.currentTime > 0) {
                this.lectureAudio.play();
                this.avatar.setSpeaking(true);
                if (this.soundWave) this.soundWave.classList.add('speaking');
            } else if ('speechSynthesis' in window && window.speechSynthesis.paused) {
                window.speechSynthesis.resume();
                this.avatar.setSpeaking(true);
                if (this.soundWave) this.soundWave.classList.add('speaking');
            } else {
                this.goToSlide(this.currentIdx, true);
            }
        }
    }

    buildSlideDots() {
        const dotsContainer = document.getElementById('slideDotsContainer');
        if (!dotsContainer) return;

        dotsContainer.innerHTML = '';
        for (let i = 0; i < this.totalSlides; i++) {
            const dot = document.createElement('button');
            dot.className = `slide-dot ${i === 0 ? 'active' : ''}`;
            dot.dataset.slide = i;
            dot.title = `Jump to Slide ${i + 1}`;
            dot.innerText = i + 1;
            dot.style.cursor = 'pointer';
            dot.onclick = (e) => {
                e.stopPropagation();
                if (this.playOverlay) this.playOverlay.style.display = "none";
                this.goToSlide(i, this.isPlaying);
            };
            dotsContainer.appendChild(dot);
        }
    }

    bindEvents() {
        if (this.mainPlayPauseBtn) {
            this._listen(this.mainPlayPauseBtn, 'click', (e) => {
                e.preventDefault();
                this.togglePlay();
            });
        }

        if (this.playOverlay) {
            this._listen(this.playOverlay, 'click', (e) => {
                e.preventDefault();
                this.startPlayback();
            });
        }

        if (this.replaySlideBtn) {
            this._listen(this.replaySlideBtn, 'click', (e) => {
                e.preventDefault();
                this.goToSlide(this.currentIdx, true);
            });
        }

        if (this.replayFullBtn) {
            this._listen(this.replayFullBtn, 'click', (e) => {
                e.preventDefault();
                if (this.completionOverlay) {
                    this.completionOverlay.classList.add('d-none');
                    this.completionOverlay.classList.remove('d-flex');
                }
                this.goToSlide(0, true);
            });
        }

        if (this.prevSlideBtn) {
            this._listen(this.prevSlideBtn, 'click', (e) => {
                e.preventDefault();
                if (this.currentIdx > 0) {
                    this.goToSlide(this.currentIdx - 1, this.isPlaying);
                }
            });
        }

        if (this.nextSlideBtn) {
            this._listen(this.nextSlideBtn, 'click', (e) => {
                e.preventDefault();
                if (this.currentIdx < this.totalSlides - 1) {
                    this.goToSlide(this.currentIdx + 1, this.isPlaying);
                }
            });
        }

        // Speed controls
        document.querySelectorAll('.speed-option').forEach(item => {
            this._listen(item, 'click', (e) => {
                e.preventDefault();
                const speed = parseFloat(item.dataset.speed || 1.0);
                this.playbackSpeed = speed;
                if (this.speedLabel) this.speedLabel.innerText = `${speed}x`;
                if (this.lectureAudio) this.lectureAudio.playbackRate = speed;
                if (this.isPlaying) this.goToSlide(this.currentIdx, true);
            });
        });

        // Mute toggle
        if (this.muteToggleBtn) {
            this._listen(this.muteToggleBtn, 'click', () => {
                this.isMuted = !this.isMuted;
                if (this.isMuted) {
                    if (this.muteIcon) this.muteIcon.className = "bi bi-volume-mute-fill text-danger";
                    this.lectureAudio.muted = true;
                    this.narrationId++;  // the cancelled speech must not count as a finished slide
                    if ('speechSynthesis' in window) {
                        try { window.speechSynthesis.cancel(); } catch (e) {}
                    }
                    this.avatar.setSpeaking(false);
                    if (this.soundWave) this.soundWave.classList.remove('speaking');
                    if (this.playerStatus) {
                        this.playerStatus.innerText = `Slide ${this.currentIdx + 1} of ${this.totalSlides} (Muted)`;
                    }
                    // Keep the lecture moving silently (muted timer) on the same slide.
                    if (this.isPlaying) this.goToSlide(this.currentIdx, true);
                } else {
                    if (this.muteIcon) this.muteIcon.className = "bi bi-volume-up-fill";
                    this.lectureAudio.muted = false;
                    if (this.playerStatus) {
                        this.playerStatus.innerText = this.isPlaying ? `${this.avatar.avatarName} Lecturing (Slide ${this.currentIdx + 1} of ${this.totalSlides})` : "Audio Enabled";
                    }
                    if (this.isPlaying) this.goToSlide(this.currentIdx, true);
                }
            });
        }

        if (this.captionsToggleBtn && this.captionBar) {
            this._listen(this.captionsToggleBtn, 'click', () => {
                this.captionBar.classList.toggle('d-none');
                const isVisible = !this.captionBar.classList.contains('d-none');
                this.captionsToggleBtn.classList.toggle('btn-golden', isVisible);
                this.captionsToggleBtn.classList.toggle('btn-outline-secondary', !isVisible);
            });
        }

        this._listen(document, 'keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            if (e.code === 'Space') {
                e.preventDefault();
                this.togglePlay();
            } else if (e.code === 'ArrowRight') {
                e.preventDefault();
                if (this.currentIdx < this.totalSlides - 1) {
                    this.goToSlide(this.currentIdx + 1, this.isPlaying);
                }
            } else if (e.code === 'ArrowLeft') {
                e.preventDefault();
                if (this.currentIdx > 0) {
                    this.goToSlide(this.currentIdx - 1, this.isPlaying);
                }
            }
        });
    }

    setupWatchTimeTracker() {
        ['mousemove', 'keydown', 'scroll', 'click', 'touchstart'].forEach(evt => {
            this._listen(window, evt, () => {
                this.lastActivityTime = Date.now();
            }, { passive: true });
        });

        const INACTIVITY_THRESHOLD_MS = 60000;

        this.watchTimeInterval = setInterval(() => {
            const isTabVisible = document.visibilityState === 'visible' && !document.hidden;
            const isUserActive = (Date.now() - this.lastActivityTime) < INACTIVITY_THRESHOLD_MS;
            const isVoiceSpeaking = this.isPlaying && !this.isMuted && (
                (this.lectureAudio && !this.lectureAudio.paused && !this.lectureAudio.ended) ||
                (window.speechSynthesis && window.speechSynthesis.speaking && !window.speechSynthesis.paused) ||
                this.avatar.isSpeaking
            );

            // Verified counting: only when tab visible + user active + narration actively playing
            if (isTabVisible && isUserActive && isVoiceSpeaking) {
                this.accumulatedWatchSec += 1;

                if (this.accumulatedWatchSec >= 5 && this.watchTimeUrl) {
                    const sendSec = this.accumulatedWatchSec;
                    this.accumulatedWatchSec = 0;

                    fetch(this.watchTimeUrl, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": this.csrfToken
                        },
                        body: JSON.stringify({ seconds: sendSec })
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data && data.status === 'ok') {
                            const badge = document.getElementById('lessonWatchTimeBadge');
                            if (badge) {
                                const m = Math.floor(data.watch_time_seconds / 60);
                                const s = data.watch_time_seconds % 60;
                                const reqM = Math.floor(data.required_watch_seconds / 60);
                                badge.innerHTML = `<i class="bi bi-stopwatch me-1"></i> Watch Time: ${m}m ${s}s / ${reqM}m (${data.percentage}%)`;
                                if (data.is_completed) {
                                    badge.classList.remove('bg-secondary');
                                    badge.classList.add('bg-success');
                                }
                            }
                        }
                    })
                    .catch(err => console.debug("Watch-time telemetry heartbeat:", err));
                }
            }
        }, 1000);
    }

    // Teardown for single-page apps (React unmount): stops audio, speech, timers and listeners.
    destroy() {
        this._destroyed = true;
        this.isPlaying = false;
        clearTimeout(this.autoAdvanceTimeout);
        clearTimeout(this.watchdogTimer);
        clearInterval(this.mutedTickerTimer);
        clearInterval(this.watchTimeInterval);
        cancelAnimationFrame(this.rafId);
        this._listeners.forEach(([target, type, handler, options]) => {
            target.removeEventListener(type, handler, options);
        });
        this._listeners = [];
        try {
            this.lectureAudio.pause();
            this.lectureAudio.removeAttribute('src');
            this.lectureAudio.load();
        } catch (e) {}
        if ('speechSynthesis' in window) {
            try { window.speechSynthesis.cancel(); } catch (e) {}
        }
        if (this.audioCtx) {
            try { this.audioCtx.close(); } catch (e) {}
            this.audioCtx = null;
        }
    }
}

// Export classes to global window
window.AvatarPlayer = AvatarPlayer;
window.IntroSequence = IntroSequence;
window.LecturePlayer = LecturePlayer;
