import AdminLoader from '../../layouts/AdminLoader';
import { useState } from 'react';
import { ApiError, apiFetch } from '../../api/client';
import { bootstrapTag, useFlash, useFlashMessages } from '../../hooks/useFlash';
import { usePageData } from '../../hooks/usePageData';
import { rawStyle } from './adminModals';

/*
 * `{{ form.<field> }}`: renders the exact <input> Django's widget produced, from the
 * widget context the API returns (type, name, value, attrs incl. class, placeholder,
 * maxlength, required, aria-describedby, aria-invalid, id, checked).
 */
function FormWidget({ widget }) {
  const { class: className, maxlength, checked, ...attrs } = widget.attrs;
  const props = { ...attrs, type: widget.type, name: widget.name, className };
  if (maxlength !== undefined) props.maxLength = maxlength;
  if (widget.type === 'checkbox') props.defaultChecked = Boolean(checked);
  else if (widget.value !== null && widget.value !== undefined && widget.value !== '') props.defaultValue = widget.value;
  return <input {...props} />;
}

const FRAMES = [
  { key: 'idle', file: 'inara_idle.png', alt: 'Idle Pose', icon: 'bi-person-x', caption: 'Base Idle Pose (Closed Mouth)' },
  { key: 'wave', file: 'inara_wave.png', alt: 'Wave Pose', icon: 'bi-hand-index-thumb', caption: 'Waving Intro Pose (One Hand Raised)' },
  { key: 'blink', file: 'inara_blink.png', alt: 'Blink Pose', icon: 'bi-eye-slash', caption: 'Blink Frame (Eyes Closed)' },
  { key: 'mouth_open', file: 'inara_mouth_open.png', alt: 'Speaking Pose', icon: 'bi-chat-dots', caption: 'Speech Mouth Sync (Open Mouth)' },
];

/* Port of `admin_db/admin_settings.html` (rendered inside AdminLayout). */
export default function AvatarSettingsPage() {
  const { data, ready, reload, setData } = usePageData('/admin/avatar-settings/');
  const { addMessages, dismiss } = useFlash();
  const messages = useFlashMessages();
  const [formVersion, setFormVersion] = useState(0);

  const onSubmit = async (event) => {
    event.preventDefault();
    const body = new FormData(event.currentTarget);
    // A new request consumes the messages already displayed (Django semantics).
    messages.forEach((m) => dismiss(m.id));
    try {
      const res = await apiFetch('/admin/avatar-settings/', { method: 'POST', body });
      addMessages(res.messages);
      await reload();
    } catch (err) {
      if (!(err instanceof ApiError) || err.status !== 400) throw err;
      // Invalid form: the view re-rendered the bound form with an error message.
      setData(err.data); // usePageData adds err.data.messages
    }
    setFormVersion((v) => v + 1);
  };

  // Bootstrap's alert dismiss (fade out, then remove) driven through the flash queue so
  // React keeps ownership of the node.
  const closeAlert = (event, id) => {
    event.stopPropagation();
    event.currentTarget.closest('.alert')?.classList.remove('show');
    setTimeout(() => dismiss(id), 150);
  };

  if (!ready) return <AdminLoader />;
  const { form, avatar_settings: avatarSettings, asset_status: assetStatus } = data;

  return (
    <div className="container-fluid py-2">
      {/* Header */}
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-3 border-bottom border-warning-subtle">
        <div>
          <h2 className="fw-bold mb-1" style={{ color: '#064e3b', letterSpacing: '-0.5px' }}>
            <i className="bi bi-person-badge me-2" style={{ color: '#d4af37' }}></i>AI Teacher &amp; Avatar Settings
          </h2>
          <p className="text-muted mb-0 small">
            Configure your custom cartoon avatar, voice pronunciation, developer attribution, and lesson player animations.
          </p>
        </div>
        <div className="d-flex align-items-center gap-2">
          <span className="badge px-3 py-2" style={{ background: '#fefce8', color: '#064e3b', border: '1.5px solid #d4af37', fontWeight: 700 }}>
            <i className="bi bi-folder-check me-1"></i> public/assets/avatar/
          </span>
        </div>
      </div>

      {/* Feedback Messages */}
      {messages.length > 0 && (
        <div className="mb-4">
          {messages.map((message) => (
            <div key={message.id} className={`alert alert-${bootstrapTag(message.tags)} alert-dismissible fade show shadow-sm border-0`} role="alert">
              <i className="bi bi-info-circle-fill me-2"></i> {message.message}
              <button type="button" className="btn-close" data-bs-dismiss="alert" aria-label="Close" onClick={(e) => closeAlert(e, message.id)}></button>
            </div>
          ))}
        </div>
      )}

      {/* ASSET VERIFICATION ALERT BANNER */}
      {assetStatus.all_exist ? (
        <div className="alert alert-success d-flex align-items-center gap-3 p-3 rounded-4 shadow-sm mb-4 border-0" ref={rawStyle('background: #f0fdf4; border-left: 5px solid #16a34a !important;')}>
          <i className="bi bi-check-circle-fill fs-3 text-success"></i>
          <div>
            <h6 className="fw-bold text-success mb-1">All Cartoon Avatar Assets Present &amp; Verified</h6>
            <p className="mb-0 small text-secondary">
              All 4 PNG frames are present in <code>{assetStatus.avatar_dir}</code> with transparent backgrounds. Inara&apos;s full animation set (waving, idle breathing, blinking, and speech mouth sync) is active.
            </p>
          </div>
        </div>
      ) : assetStatus.none_exist ? (
        <div className="alert alert-danger d-flex align-items-center gap-3 p-3 rounded-4 shadow-sm mb-4 border-0" ref={rawStyle('background: #fef2f2; border-left: 5px solid #dc2626 !important;')}>
          <i className="bi bi-exclamation-triangle-fill fs-2 text-danger"></i>
          <div>
            <h6 className="fw-bold text-danger mb-1">Warning: No Avatar Assets Found in public/assets/avatar/</h6>
            <p className="mb-0 small text-secondary">
              No cartoon frames were found in <code>{assetStatus.avatar_dir}</code>. The lesson player is currently falling back to the built-in SVG placeholder. To use your custom cartoon teacher, place <code>inara_idle.png</code>, <code>inara_wave.png</code>, <code>inara_blink.png</code>, and <code>inara_mouth_open.png</code> in that folder.
            </p>
          </div>
        </div>
      ) : (
        <div className="alert alert-warning d-flex align-items-center gap-3 p-3 rounded-4 shadow-sm mb-4 border-0" ref={rawStyle('background: #fffbeb; border-left: 5px solid #d97706 !important;')}>
          <i className="bi bi-exclamation-circle-fill fs-3 text-warning"></i>
          <div>
            <h6 className="fw-bold text-warning mb-1">Partial Avatar Assets Detected</h6>
            <p className="mb-0 small text-secondary">
              Found {assetStatus.present_count} of {assetStatus.total_required} frames. Missing frames:{' '}
              <strong>{assetStatus.missing_files.join(', ')}</strong>.{' '}
              {assetStatus.has_idle ? (
                <>Missing frames will automatically fall back to <code>inara_idle.png</code> without breaking playback.</>
              ) : (
                <><code>inara_idle.png</code> is missing; fallback to built-in placeholder is active.</>
              )}
            </p>
          </div>
        </div>
      )}

      <div className="row g-4">
        {/* LEFT COLUMN: SETTINGS FORM */}
        <div className="col-lg-6">
          <div className="card border-0 shadow-sm rounded-4 h-100" ref={rawStyle('border-top: 4px solid #d4af37 !important;')}>
            <div className="card-header bg-white py-3 border-bottom">
              <h5 className="fw-bold mb-0" style={{ color: '#064e3b' }}>
                <i className="bi bi-sliders me-2" style={{ color: '#d4af37' }}></i>Avatar &amp; Developer Identity
              </h5>
              <small className="text-muted">Changes saved here are instantly reflected across all course lessons.</small>
            </div>
            <div className="card-body p-4">
              <form method="POST" onSubmit={onSubmit} key={formVersion}>

                {/* Avatar Name */}
                <div className="mb-3">
                  <label className="form-label fw-bold small text-dark">
                    Avatar Real Name <span className="text-danger">*</span>
                  </label>
                  <FormWidget widget={form.avatar_name} />
                  <div className="form-text small">
                    The real name displayed visually on the screen and in captions (default: <strong>Inara</strong>).
                  </div>
                </div>

                {/* Developer Name */}
                <div className="mb-3">
                  <label className="form-label fw-bold small text-dark">
                    Developer Name <span className="text-danger">*</span>
                  </label>
                  <FormWidget widget={form.developer_name} />
                  <div className="form-text small">
                    The developer credited by Inara in the lesson introduction (e.g. <em>Tabinda Rukhsar</em>).
                  </div>
                </div>

                {/* University / Department */}
                <div className="mb-3">
                  <label className="form-label fw-bold small text-dark">
                    University or Department <span className="text-muted">(Optional)</span>
                  </label>
                  <FormWidget widget={form.university_or_department} />
                  <div className="form-text small">
                    Mentioned in the introduction: <em>&quot;ALVIX was developed by {'{developer}'} at {'{university_or_department}'} as a final year project.&quot;</em> Leave empty if not applicable.
                  </div>
                </div>

                {/* Avatar Name Pronunciation */}
                <div className="mb-3">
                  <label className="form-label fw-bold small text-dark">
                    Avatar Speech Pronunciation <span className="text-muted">(Optional for TTS)</span>
                  </label>
                  <FormWidget widget={form.avatar_name_pronunciation} />
                  <div className="form-text small">
                    Phonetic spelling used <strong>ONLY for speech synthesis</strong> so the voice engine pronounces the name correctly (e.g. <code>ee-nah-rah</code>). The screen always displays the real name.
                  </div>
                </div>

                {/* Play Full Intro Every Day */}
                <div className="mb-4 p-3 rounded-3" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                  <div className="form-check form-switch">
                    <FormWidget widget={form.play_full_intro_every_day} />{' '}
                    <label className="form-check-label fw-bold text-dark small" htmlFor={form.play_full_intro_every_day.id_for_label}>
                      Play Full Introduction Every Day
                    </label>
                  </div>
                  <div className="form-text small mt-1">
                    Default is <strong>Off (False)</strong>: Day 1 plays the full introduction, while subsequent days play a quick greeting (<em>&quot;Welcome back, {'{student}'}! Today we will learn...&quot;</em>). Turn on to play the full introduction on every day.
                  </div>
                </div>

                <div className="d-flex justify-content-end">
                  <button type="submit" className="btn px-4 py-2 fw-bold shadow-sm rounded-pill" style={{ background: 'linear-gradient(135deg, #064E3B, #106E53)', color: '#D4AF37', border: '1.5px solid #D4AF37' }}>
                    <i className="bi bi-save2-fill me-1"></i> Save Avatar Settings
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: LIVE PREVIEW & ASSET CARDS */}
        <div className="col-lg-6">
          {/* Intro Script Preview */}
          <div className="card border-0 shadow-sm rounded-4 mb-4" ref={rawStyle('border-top: 4px solid #064E3B !important;')}>
            <div className="card-header bg-white py-3 border-bottom d-flex justify-content-between align-items-center">
              <h6 className="fw-bold mb-0 text-success">
                <i className="bi bi-chat-quote-fill me-2 text-warning"></i>Live Introduction Script Preview
              </h6>
              <span className="badge bg-light text-dark border">Day 1 Masterclass</span>
            </div>
            <div className="card-body p-3">
              <div className="p-3 rounded-3 shadow-sm mb-3" style={{ background: '#FEF9E7', borderLeft: '4px solid #D4AF37' }}>
                <span className="badge bg-dark text-warning small mb-2">On-Screen Caption Text</span>
                <p className="small text-dark mb-0 fw-medium" style={{ lineHeight: 1.6 }}>
                  &quot;Assalamu alaikum, {'{Student}'}! I am <strong>{avatarSettings.avatar_name}</strong>, your AI teacher at ALVIX, the adaptive learning system with AI-driven content. ALVIX was developed by <strong>{avatarSettings.developer_name}</strong>{avatarSettings.university_or_department ? <> at <strong>{avatarSettings.university_or_department}</strong></> : null} as a final year project. In this course, Python Mastery, I will guide you step by step. Today, in Day 1, we will learn Introduction to Python. Let us begin!&quot;
                </p>
              </div>

              <div className="p-3 rounded-3 shadow-sm" style={{ background: '#F0FDF4', borderLeft: '4px solid #16A34A' }}>
                <span className="badge bg-success text-white small mb-2">Spoken by TTS Voice</span>
                <p className="small text-dark mb-0 font-monospace" style={{ lineHeight: 1.6 }}>
                  &quot;Assalamu alaikum, {'{Student}'}! I am <span className="text-success fw-bold">{avatarSettings.get_spoken_name}</span>, your AI teacher at ALVIX...&quot;
                </p>
              </div>
            </div>
          </div>

          {/* Asset Inspection Grid */}
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-header bg-white py-3 border-bottom d-flex justify-content-between align-items-center">
              <h6 className="fw-bold mb-0" style={{ color: '#064e3b' }}>
                <i className="bi bi-images me-2" style={{ color: '#d4af37' }}></i>Cartoon Frame Assets Status
              </h6>
              <span className="badge bg-secondary-subtle text-secondary small">512×512 Transparent PNG</span>
            </div>
            <div className="card-body p-3">
              <div className="row g-3">
                {FRAMES.map((frame) => {
                  const status = assetStatus.file_status[frame.key];
                  return (
                    <div className="col-sm-6" key={frame.key}>
                      <div className="p-2 border rounded-3 text-center h-100 bg-light d-flex flex-column align-items-center justify-content-between">
                        <div className="w-100 d-flex justify-content-between align-items-center mb-1">
                          <span className="badge bg-dark text-warning small font-monospace">{frame.file}</span>
                          {status.exists ? (
                            <span className="badge bg-success-subtle text-success border border-success"><i className="bi bi-check2"></i> Present</span>
                          ) : frame.key === 'idle' ? (
                            <span className="badge bg-danger-subtle text-danger border border-danger"><i className="bi bi-x"></i> Missing</span>
                          ) : (
                            <span className="badge bg-warning-subtle text-warning border border-warning"><i className="bi bi-arrow-repeat"></i> Fallback</span>
                          )}
                        </div>
                        <div className="my-2 p-2 rounded-3" style={{ background: 'linear-gradient(135deg, #064E3B, #022C22)', border: '1px solid #D4AF37' }}>
                          {status.exists ? (
                            <img src={status.url} alt={frame.alt} style={{ width: '80px', height: '80px', objectFit: 'contain' }} />
                          ) : (
                            <div className="d-flex align-items-center justify-content-center text-white-50" style={{ width: '80px', height: '80px' }}>
                              <i className={`bi ${frame.icon} fs-1`}></i>
                            </div>
                          )}
                        </div>
                        <small className="text-muted fw-semibold">{frame.caption}</small>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
