// Port of main_front/signup.html: account creation followed by email verification.
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../hooks/useAuth';
import { usePageAssets } from '../../hooks/usePageAssets';
import { LOGO_DARK, LOGO_LIGHT } from '../../cdn';
import rawCss from './SignupPage.css?raw';
import authCss from './AuthPages.css?raw';
import AuthShowcase from './AuthShowcase';
import ThemeToggle from './ThemeToggle';
import { usePublicTheme } from './usePublicTheme';
import { ROOT_PASSTHROUGH } from './rootPassthrough';
import {
  PASSWORD_RULES,
  validateConfirmPassword,
  validateEmail,
  validateFullName,
  validateNewPassword,
  validateOtp,
  validateUsername,
} from './authValidation';
import { FieldError, PasswordEye, Spinner, useAuthForm } from './useAuthForm';

const css = authCss + rawCss + ROOT_PASSTHROUGH;

const INITIAL = { full_name: '', username: '', email: '', password: '', confirm_password: '' };
const VALIDATORS = {
  full_name: (v) => validateFullName(v.full_name),
  username: (v) => validateUsername(v.username),
  email: (v) => validateEmail(v.email),
  password: (v) => validateNewPassword(v.password),
  confirm_password: (v) => validateConfirmPassword(v.confirm_password, v.password),
};
const OTP_INITIAL = { verification_code: '' };
const OTP_VALIDATORS = { verification_code: (v) => validateOtp(v.verification_code) };
const RESEND_SECONDS = 30;
const TOAST_ID = 'signup';

/** Which field a backend error message belongs to, so it can be shown under that input. */
function fieldForServerError(message = '') {
  const m = message.toLowerCase();
  if (m.includes('username')) return 'username';
  if (m.includes('email')) return 'email';
  if (m.includes('full name')) return 'full_name';
  if (m.includes('do not match')) return 'confirm_password';
  if (m.includes('password')) return 'password';
  return null;
}

function networkAwareMessage(err, fallback) {
  if (!err.status || err.status >= 500) return 'Server is not responding. Please try again in a moment.';
  return err.data?.error || err.message || fallback;
}

export default function SignupPage() {
  usePageAssets({ css, title: 'ALVIX - Student Registration' });
  const { theme, setTheme } = usePublicTheme();
  const { refresh } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState('details'); // 'details' | 'verify'
  const [pendingEmail, setPendingEmail] = useState('');
  const [debugCode, setDebugCode] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [serverError, setServerError] = useState(null); // { field, message, value }
  const [cooldown, setCooldown] = useState(0);

  const details = useAuthForm(INITIAL, VALIDATORS);
  const otp = useAuthForm(OTP_INITIAL, OTP_VALIDATORS);
  const { values } = details;

  const passedRules = PASSWORD_RULES.filter((rule) => rule.test(values.password)).length;
  const strengthLabel = values.password
    ? ['Very weak', 'Weak', 'Fair', 'Good', 'Strong'][Math.max(passedRules - 1, 0)]
    : 'Not entered';

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timer = window.setTimeout(() => setCooldown((s) => s - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  /** Client error first; otherwise a server error that still applies to the unchanged value. */
  function errorFor(name) {
    const clientError = details.visibleError(name);
    if (clientError) return clientError;
    if (serverError?.field === name && serverError.value === values[name]) return serverError.message;
    return '';
  }

  function propsFor(name) {
    const props = details.fieldProps(name);
    const message = errorFor(name);
    return {
      ...props,
      'aria-invalid': Boolean(message) || undefined,
      'aria-describedby': message ? `${name}-error` : undefined,
      className: message ? 'form-control is-invalid' : props.className,
      disabled: submitting,
    };
  }

  function payload() {
    return {
      full_name: values.full_name.trim().replace(/\s+/g, ' '),
      username: values.username.trim(),
      email: values.email.trim(),
      password: values.password,
      confirm_password: values.confirm_password,
    };
  }

  async function sendCode({ resend = false } = {}) {
    setSubmitting(true);
    const loading = toast.loading(resend ? 'Sending a new code…' : 'Creating your account…', { id: TOAST_ID });
    try {
      const res = await apiFetch('/public/signup/', { method: 'POST', body: payload() });
      toast.success(
        resend ? `A new code was sent to ${res.email}.` : 'Verification code sent. Check your email to continue.',
        { id: loading },
      );
      setPendingEmail(res.email);
      setDebugCode(res.verification_code_debug || null);
      setStep('verify');
      setCooldown(RESEND_SECONDS);
      otp.reset();
      return true;
    } catch (err) {
      const message = networkAwareMessage(err, 'Could not create your account.');
      toast.error(message, { id: loading });
      const field = fieldForServerError(err.data?.error);
      if (field) {
        setServerError({ field, message, value: values[field] });
        setStep('details');
        window.setTimeout(() => document.getElementById(field === 'email' ? 'signup_email' : field)?.focus(), 0);
      }
      return false;
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSignupSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    const firstInvalid = details.validateAll();
    if (firstInvalid) {
      toast.error(details.errors[firstInvalid], { id: TOAST_ID });
      document.getElementById(firstInvalid === 'email' ? 'signup_email' : firstInvalid === 'password' ? 'signup_password' : firstInvalid)?.focus();
      return;
    }
    setServerError(null);
    await sendCode();
  }

  async function handleVerifySubmit(e) {
    e.preventDefault();
    if (submitting) return;
    const firstInvalid = otp.validateAll();
    if (firstInvalid) {
      toast.error(otp.errors[firstInvalid], { id: TOAST_ID });
      document.getElementById('verification_code')?.focus();
      return;
    }

    setSubmitting(true);
    const loading = toast.loading('Verifying your code…', { id: TOAST_ID });
    try {
      const res = await apiFetch('/public/signup/verify/', {
        method: 'POST',
        body: { verify_code_submit: '1', verification_code: otp.values.verification_code.trim() },
      });
      await refresh();
      toast.success('Your email is verified. Welcome to ALVIX!', { id: loading });
      navigate(res.redirect || '/assessment/');
    } catch (err) {
      const data = err.data || {};
      toast.error(networkAwareMessage(err, 'Could not verify your email.'), { id: loading });
      if (err.status && err.status < 500 && data.step !== 'verify') {
        // Session expired or too many attempts: back to the details form, keep what was typed.
        setStep('details');
        details.setValue('confirm_password', '');
      } else {
        otp.reset();
        window.setTimeout(() => document.getElementById('verification_code')?.focus(), 0);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleOtpChange(e) {
    otp.setValue('verification_code', e.target.value.replace(/\D/g, '').slice(0, 6));
  }

  function handleOtpPaste(e) {
    const digits = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6);
    if (digits) {
      e.preventDefault();
      otp.setValue('verification_code', digits);
    }
  }

  function backToDetails() {
    setStep('details');
    setDebugCode(null);
  }

  const isVerifying = step === 'verify';
  const progress = isVerifying ? 100 : 50;
  const otpError = otp.visibleError('verification_code');

  return (
    <main className="auth-page signup-page">
      <section className="auth-form-panel">
        <div className="auth-form-inner">
          <div className="auth-form-header">
            <Link to="/" className="auth-brand" aria-label="ALVIX home">
              <img className="auth-brand__logo" src={theme === 'Light' ? LOGO_LIGHT : LOGO_DARK} alt="ALVIX" />
            </Link>
            <ThemeToggle theme={theme} onChange={setTheme} />
          </div>

          <header className="auth-heading">
            <p className="auth-heading__eyebrow">Start learning with ALVIX</p>
            <h1>{isVerifying ? 'Verify your email' : 'Create your account'}</h1>
            <p>
              {isVerifying
                ? <>Enter the 6-digit code sent to <strong className="auth-email">{pendingEmail}</strong>.</>
                : 'Set up your profile to get a learning path shaped around you.'}
            </p>
          </header>

          <div className="signup-progress">
            <div className="signup-progress__meta">
              <span>Registration progress</span>
              <span>Step {isVerifying ? '2' : '1'} of 2</span>
            </div>
            <div
              className="signup-progress__track"
              role="progressbar"
              aria-label="Registration progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
              aria-valuetext={`Step ${isVerifying ? '2' : '1'} of 2: ${isVerifying ? 'Email verification' : 'Account details'}`}
            >
              <span className="signup-progress__fill" style={{ width: `${progress}%` }} />
            </div>
            <ol className="signup-steps" aria-label="Registration steps">
              <li className={isVerifying ? 'signup-step is-complete' : 'signup-step is-current'} aria-current={!isVerifying ? 'step' : undefined}>
                <span className="signup-step__number">{isVerifying ? '✓' : '1'}</span>
                <span>Account details</span>
              </li>
              <li className={isVerifying ? 'signup-step is-current' : 'signup-step'} aria-current={isVerifying ? 'step' : undefined}>
                <span className="signup-step__number">2</span>
                <span>Email verification</span>
              </li>
            </ol>
          </div>

          {isVerifying ? (
            <>
              <div className="signup-info">
                <span className="signup-info__mark" aria-hidden="true">i</span>
                <p>Check your inbox (and spam folder) and enter the code below to confirm your email address.</p>
              </div>

              {debugCode ? (
                <p className="signup-test-code">
                  Testing code: <strong>{debugCode}</strong>
                </p>
              ) : null}

              <form method="POST" id="verifyForm" noValidate onSubmit={handleVerifySubmit} aria-busy={submitting}>
                <div className="form-group">
                  <label htmlFor="verification_code">6-digit verification code</label>
                  <input
                    type="text"
                    id="verification_code"
                    {...otp.fieldProps('verification_code')}
                    className={`${otp.fieldProps('verification_code').className} signup-code-input`}
                    onChange={handleOtpChange}
                    onPaste={handleOtpPaste}
                    placeholder="000000"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    disabled={submitting}
                    required
                    autoFocus
                  />
                  <FieldError name="verification_code" message={otpError} />
                </div>
                <button type="submit" className="auth-submit" disabled={submitting}>
                  {submitting ? <Spinner /> : null}
                  {submitting ? 'Verifying code…' : 'Verify and continue'}
                  {submitting ? null : <span aria-hidden="true">→</span>}
                </button>
              </form>

              <div className="signup-verify-actions">
                <button type="button" className="auth-link-button" onClick={backToDetails} disabled={submitting}>
                  ← Edit details
                </button>
                <button
                  type="button"
                  className="auth-link-button"
                  onClick={() => sendCode({ resend: true })}
                  disabled={submitting || cooldown > 0}
                >
                  {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="signup-info">
                <span className="signup-info__mark" aria-hidden="true">i</span>
                <p>Create your student profile, then confirm your email to begin your learning assessment.</p>
              </div>

              <form method="POST" id="signupForm" noValidate onSubmit={handleSignupSubmit} aria-busy={submitting}>
                <div className="form-group">
                  <label htmlFor="full_name">Full name</label>
                  <input
                    type="text"
                    id="full_name"
                    {...propsFor('full_name')}
                    placeholder="e.g. Alex Morgan"
                    autoComplete="name"
                    maxLength={80}
                    required
                  />
                  <FieldError name="full_name" message={errorFor('full_name')} />
                </div>

                <div className="form-group">
                  <label htmlFor="username">Username</label>
                  <input
                    type="text"
                    id="username"
                    {...propsFor('username')}
                    placeholder="Choose a unique username"
                    autoComplete="username"
                    autoCapitalize="none"
                    spellCheck={false}
                    maxLength={30}
                    required
                  />
                  <FieldError name="username" message={errorFor('username')} />
                </div>

                <div className="form-group">
                  <label htmlFor="signup_email">Email address</label>
                  <input
                    type="email"
                    id="signup_email"
                    {...propsFor('email')}
                    aria-describedby={errorFor('email') ? 'email-error' : undefined}
                    placeholder="you@example.com"
                    autoComplete="email"
                    inputMode="email"
                    autoCapitalize="none"
                    spellCheck={false}
                    maxLength={254}
                    required
                  />
                  <FieldError name="email" message={errorFor('email')} />
                </div>

                <div className="password-grid">
                  <div className="form-group">
                    <label htmlFor="signup_password">Password</label>
                    <div className="auth-password-wrap">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        id="signup_password"
                        {...propsFor('password')}
                        aria-describedby={errorFor('password') ? 'password-error' : 'password-rules'}
                        placeholder="Create a password"
                        autoComplete="new-password"
                        required
                      />
                      <button
                        type="button"
                        className="auth-password-toggle"
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        aria-pressed={showPassword}
                        onClick={() => setShowPassword((shown) => !shown)}
                      >
                        <PasswordEye visible={showPassword} />
                      </button>
                    </div>
                    <FieldError name="password" message={serverError?.field === 'password' && serverError.value === values.password ? serverError.message : (details.visibleError('password') ? 'Meet all the requirements below.' : '')} />
                  </div>
                  <div className="form-group">
                    <label htmlFor="confirm_password">Confirm password</label>
                    <div className="auth-password-wrap">
                      <input
                        type={showConfirmPassword ? 'text' : 'password'}
                        id="confirm_password"
                        {...propsFor('confirm_password')}
                        placeholder="Enter it again"
                        autoComplete="new-password"
                        required
                      />
                      <button
                        type="button"
                        className="auth-password-toggle"
                        aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                        aria-pressed={showConfirmPassword}
                        onClick={() => setShowConfirmPassword((shown) => !shown)}
                      >
                        <PasswordEye visible={showConfirmPassword} />
                      </button>
                    </div>
                    <FieldError
                      name="confirm_password"
                      message={errorFor('confirm_password') || (values.confirm_password && values.confirm_password !== values.password ? 'Passwords do not match.' : '')}
                    />
                  </div>
                </div>

                <div className="password-strength" data-strength={passedRules}>
                  <div className="password-strength__header">
                    <span>Password strength</span>
                    <strong>{strengthLabel}</strong>
                  </div>
                  <div
                    className="password-strength__track"
                    role="progressbar"
                    aria-label="Password strength"
                    aria-valuemin={0}
                    aria-valuemax={5}
                    aria-valuenow={passedRules}
                    aria-valuetext={`${strengthLabel}: ${passedRules} of 5 requirements met`}
                  >
                    <span className="password-strength__fill" style={{ width: `${(passedRules / PASSWORD_RULES.length) * 100}%` }} />
                  </div>
                  <ul className="password-rules" id="password-rules" aria-label="Password requirements">
                    {PASSWORD_RULES.map((rule) => {
                      const ok = rule.test(values.password);
                      return (
                        <li key={rule.label} className={ok ? 'is-valid' : ''}>
                          <span aria-hidden="true">{ok ? '✓' : '•'}</span>
                          {rule.label}
                        </li>
                      );
                    })}
                  </ul>
                </div>

                <button type="submit" className="auth-submit" disabled={submitting}>
                  {submitting ? <Spinner /> : null}
                  {submitting ? 'Sending verification code…' : 'Create account'}
                  {submitting ? null : <span aria-hidden="true">→</span>}
                </button>
              </form>
            </>
          )}

          <p className="auth-switch">
            Already have an account? <Link to="/login/">Sign in</Link>
          </p>
        </div>
      </section>
      <AuthShowcase />
    </main>
  );
}
