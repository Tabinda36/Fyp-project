// Port of main_front/verify_otp.html (legacy standalone page). Uses the signup verify endpoint with `otp_code`.
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../hooks/useAuth';
import { usePageAssets } from '../../hooks/usePageAssets';
import { usePageData } from '../../hooks/usePageData';
import rawCss from './VerifyOtpPage.css?raw';
import { ROOT_PASSTHROUGH } from './rootPassthrough';
import { validateOtp } from './authValidation';

const css = rawCss + ROOT_PASSTHROUGH;
const TOAST_ID = 'verify-otp';

export default function VerifyOtpPage() {
  usePageAssets({ css, title: 'ALVIX - Verify OTP' });
  const { ready } = usePageData('/public/signup/verify/'); // {redirect: '/signup/'} when nothing is pending
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    const invalid = validateOtp(code);
    if (invalid) {
      setError(invalid);
      toast.error(invalid, { id: TOAST_ID });
      return;
    }
    setSubmitting(true);
    const loading = toast.loading('Verifying your code…', { id: TOAST_ID });
    try {
      const res = await apiFetch('/public/signup/verify/', { method: 'POST', body: { otp_code: code } });
      await refresh();
      toast.success('Your email is verified. Welcome to ALVIX!', { id: loading });
      navigate(res.redirect || '/assessment/');
    } catch (err) {
      if (err.data?.redirect) {
        toast.error('Your signup session has expired. Please register again.', { id: loading });
        navigate(err.data.redirect);
        return;
      }
      const message = err.data?.error || err.message || 'Could not verify your code.';
      setError(message);
      toast.error(message, { id: loading });
      setCode('');
    } finally {
      setSubmitting(false);
    }
  }

  if (!ready) return null;

  return (
    <div className="card">
      <h2>Email Verification</h2>
      <p>Enter the 6-digit verification code sent to your email address.</p>

      <form method="POST" noValidate onSubmit={handleSubmit}>
        <input
          type="text"
          name="otp_code"
          placeholder="------"
          maxLength={6}
          inputMode="numeric"
          autoComplete="one-time-code"
          value={code}
          onChange={(e) => {
            setCode(e.target.value.replace(/\D/g, '').slice(0, 6));
            setError(null);
          }}
          aria-invalid={Boolean(error) || undefined}
          required
          autoFocus
        />
        <button type="submit" disabled={submitting}>{submitting ? 'Verifying…' : 'Verify'}</button>
      </form>

      {error && <div className="error" role="alert">{error}</div>}
    </div>
  );
}
