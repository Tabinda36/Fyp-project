// Shared helpers for the User Management list and User Details pages.
import { apiFetch } from '../../api/client';
import { djDate } from '../../utils/djangoFormat';

export function initials(name = '') {
  const parts = name.replace(/[_.-]+/g, ' ').trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  return (parts[0][0] + (parts[1]?.[0] || parts[0][1] || '')).toUpperCase();
}

/** Stable pleasant hue per user for the initials avatar. */
export function avatarHue(seed = '') {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) h = (h * 31 + seed.charCodeAt(i)) % 360;
  return h;
}

export function normalizeUser(user) {
  const courses = (user.custom_generated_courses || []).filter((c) => c && c !== 'None');
  return {
    ...user,
    phone: user.profile?.phone || '',
    dob: user.profile?.dob ? djDate(user.profile.dob, 'Y-m-d') : '',
    courses,
  };
}

/** First success message from an API `ok()` payload. */
export function apiMessage(res, fallback) {
  const list = res?.messages || [];
  return list[0]?.message || fallback;
}

export function deleteUser(id) {
  return apiFetch('/admin/users/', { method: 'POST', body: { action: 'delete', user_id: String(id) } });
}

export function updateUser(id, fields) {
  return apiFetch('/admin/users/', { method: 'POST', body: { action: 'edit', user_id: String(id), ...fields } });
}

export function errorText(err, fallback) {
  if (!err?.status || err.status >= 500) return 'Server is not responding. Please try again.';
  if (err.status === 404) return 'This user no longer exists.';
  return err.data?.error || fallback;
}
