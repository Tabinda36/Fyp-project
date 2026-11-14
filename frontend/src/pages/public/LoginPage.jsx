// Port of main_front/login.html as a standalone public page.
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../hooks/useAuth';
import { usePageAssets } from '../../hooks/usePageAssets';
import { LOGO_DARK, LOGO_LIGHT } from '../../cdn';
import rawCss from './LoginPage.css?raw';
import authCss from './AuthPages.css?raw';
import AuthShowcase from './AuthShowcase';
import ThemeToggle from './ThemeToggle';
import { usePublicTheme } from './usePublicTheme';
import { ROOT_PASSTHROUGH } from './rootPassthrough';
import { validateEmail, validateLoginPassword } from './authValidation';
import { FieldError, PasswordEye, Spinner, useAuthForm } from './useAuthForm';

const css = authCss + rawCss + ROOT_PASSTHROUGH;

const INITIAL = { email: '', password: '', remember_account: false };
const VALIDATORS = {
  email: (v) => validateEmail(v.email),
  password: (v) => validateLoginPassword(v.password),
};
const TOAST_ID = 'login';

export default function LoginPage() {
  usePageAssets({ css, title: 'ALVIX - Welcome Back' });
  const { theme, setTheme } = usePublicTheme();
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [showPass, setShowPass] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const form = useAuthForm(INITIAL, VALIDATORS);
  const { values, fieldProps, visibleError, validateAll, errors, setValue, handleChange } = form;

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    const firstInvalid = validateAll();
    if (firstInvalid) {
      toast.error(errors[firstInvalid], { id: TOAST_ID });
      document.getElementById(firstInvalid)?.focus();
      return;
    }

    setSubmitting(true);
    const loading = toast.loading('Signing you in…', { id: TOAST_ID });
    try {
      const res = await apiFetch('/auth/login/', {
        method: 'POST',
        body: {
          email: values.email.trim(),
          password: values.password,
          remember_account: values.remember_account,
        },
      });
      await refresh();
      toast.success('Signed in successfully. Welcome back!', { id: loading });
      navigate(res.redirect || '/');
    } catch (err) {
      const message = err.status >= 500 || !err.status
        ? 'Server is not responding. Please try again in a moment.'
        : err.data?.error || err.message || 'Invalid email or password.';
      toast.error(message, { id: loading });
      setValue('password', '');
      setShowPass(false);
      document.getElementById('password')?.focus();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page login-page">
      <section className="auth-form-panel">
        <div className="auth-form-inner">
          <div className="auth-form-header">
            <Link to="/" className="auth-brand" aria-label="ALVIX home">
              <img className="auth-brand__logo" src={theme === 'Light' ? LOGO_LIGHT : LOGO_DARK} alt="ALVIX" />
            </Link>
            <ThemeToggle theme={theme} onChange={setTheme} />
          </div>

          <header className="auth-heading">
            <p className="auth-heading__eyebrow">Welcome back</p>
            <h1>Continue your journey.</h1>
            <p>Sign in to pick up where your learning left off.</p>
          </header>

          <form className="login-form" method="POST" noValidate onSubmit={handleSubmit} aria-busy={submitting}>
            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <div className="login-input-wrap">
                <svg className="login-input-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="3" y="5" width="18" height="14" rx="2" />
                  <path d="M3 7l9 6 9-6" />
                </svg>
                <input
                  type="email"
                  id="email"
                  {...fieldProps('email')}
                  placeholder="you@example.com"
                  autoComplete="email"
                  inputMode="email"
                  autoCapitalize="none"
                  spellCheck={false}
                  maxLength={254}
                  disabled={submitting}
                  required
                />
              </div>
              <FieldError name="email" message={visibleError('email')} />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <div className="login-input-wrap">
                <svg className="login-input-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="4" y="11" width="16" height="10" rx="2" />
                  <path d="M8 11V8a4 4 0 0 1 8 0v3" />
                </svg>
                <input
                  type={showPass ? 'text' : 'password'}
                  id="password"
                  {...fieldProps('password')}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  disabled={submitting}
                  required
                />
                <button
                  type="button"
                  className="login-toggle-pass"
                  aria-label={showPass ? 'Hide password' : 'Show password'}
                  aria-pressed={showPass}
                  onClick={() => setShowPass((shown) => !shown)}
                >
                  <PasswordEye visible={showPass} />
                </button>
              </div>
              <FieldError name="password" message={visibleError('password')} />
            </div>

            <label className="remember-row" htmlFor="remember_account">
              <input
                type="checkbox"
                name="remember_account"
                id="remember_account"
                checked={values.remember_account}
                onChange={handleChange}
                disabled={submitting}
              />
              <span>Remember me</span>
            </label>

            <button type="submit" className="auth-submit" disabled={submitting}>
              {submitting ? <Spinner /> : null}
              {submitting ? 'Signing in…' : 'Sign in'}
              {submitting ? null : <span aria-hidden="true">→</span>}
            </button>
          </form>

          <p className="auth-switch">
            New to ALVIX? <Link to="/signup/">Create an account</Link>
          </p>
        </div>
      </section>
      <AuthShowcase />
    </main>
  );
}
