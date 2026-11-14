// Field validation for the public auth pages (login, signup, OTP).
// Rules mirror backend/alvixapp/page_context/public.py (signup_start) so the user sees
// the same verdict before and after submitting.

// Practical email check: one @, no spaces, a dot in the domain, a 2+ letter TLD.
const EMAIL_RE = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)*\.[A-Za-z]{2,}$/;
const USERNAME_RE = /^[A-Za-z0-9_.-]{3,30}$/;
const NAME_RE = /^[\p{L}][\p{L}\p{M}'’.\- ]*$/u;

export const PASSWORD_RULES = [
  { label: 'At least 8 characters', test: (value) => value.length >= 8 },
  { label: 'An uppercase letter', test: (value) => /[A-Z]/.test(value) },
  { label: 'A lowercase letter', test: (value) => /[a-z]/.test(value) },
  { label: 'A number', test: (value) => /\d/.test(value) },
  { label: 'A symbol', test: (value) => /[^A-Za-z0-9]/.test(value) },
];

export function validateEmail(raw) {
  const value = raw.trim();
  if (!value) return 'Email address is required.';
  if (value.length > 254) return 'Email address is too long.';
  if (!EMAIL_RE.test(value)) return 'Enter a valid email address, e.g. you@example.com.';
  return '';
}

export function validateFullName(raw) {
  const value = raw.trim();
  if (!value) return 'Full name is required.';
  if (value.length < 2) return 'Full name must be at least 2 characters.';
  if (value.length > 80) return 'Full name must be 80 characters or fewer.';
  if (!NAME_RE.test(value)) return 'Use letters, spaces, hyphens or apostrophes only.';
  return '';
}

export function validateUsername(raw) {
  const value = raw.trim();
  if (!value) return 'Username is required.';
  if (value.length < 3) return 'Username must be at least 3 characters.';
  if (value.length > 30) return 'Username must be 30 characters or fewer.';
  if (!USERNAME_RE.test(value)) return 'Use letters, numbers, dots, underscores or hyphens (no spaces).';
  return '';
}

export function validateNewPassword(value) {
  if (!value) return 'Password is required.';
  const missing = PASSWORD_RULES.filter((rule) => !rule.test(value));
  if (missing.length) return `Password needs: ${missing.map((r) => r.label.toLowerCase()).join(', ')}.`;
  return '';
}

export function validateConfirmPassword(value, password) {
  if (!value) return 'Please confirm your password.';
  if (value !== password) return 'Passwords do not match.';
  return '';
}

export function validateLoginPassword(value) {
  return value ? '' : 'Password is required.';
}

export function validateOtp(raw) {
  const value = raw.trim();
  if (!value) return 'Verification code is required.';
  if (!/^\d{6}$/.test(value)) return 'The code must be exactly 6 digits.';
  return '';
}

/** Run `validators` ({field: (values) => message}) and return only fields with errors. */
export function runValidators(validators, values) {
  return Object.fromEntries(
    Object.entries(validators)
      .map(([field, fn]) => [field, fn(values)])
      .filter(([, message]) => message),
  );
}
