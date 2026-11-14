// Thin fetch wrapper for the Django API (/api/v1).
// Session cookie auth + Django CSRF (X-CSRFToken from the csrftoken cookie).

export const API_BASE = '/api/v1';

export function getCookie(name) {
  const match = document.cookie
    .split(';')
    .map((c) => c.trim())
    .find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

export class ApiError extends Error {
  constructor(status, data) {
    super((data && data.detail) || `Request failed (${status})`);
    this.status = status;
    this.data = data || {};
    this.errors = (data && data.errors) || {};
  }
}

let csrfReady = null;
async function ensureCsrf(force = false) {
  if (!force && getCookie('csrftoken')) return;
  if (force || !csrfReady) {
    csrfReady = fetch(`${API_BASE}/auth/csrf/`, { credentials: 'same-origin' }).catch(() => null);
  }
  await csrfReady;
  // A failed fetch (server down/restarting) must not be cached forever: try again next time.
  if (!getCookie('csrftoken')) csrfReady = null;
}

function isCsrfFailure(status, data) {
  return status === 403 && typeof data?.detail === 'string' && data.detail.startsWith('CSRF Failed');
}

/**
 * apiFetch('/student/dashboard/')
 * apiFetch('/auth/login/', { method: 'POST', body: { email, password } })
 * apiFetch('/student/profile/', { method: 'POST', body: formDataInstance })  // multipart
 */
export async function apiFetch(path, { method = 'GET', body, query, signal } = {}) {
  const url = new URL(path.startsWith('http') ? path : `${API_BASE}${path}`, window.location.origin);
  if (query) {
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
    });
  }

  const unsafe = method !== 'GET' && method !== 'HEAD';
  const headers = { Accept: 'application/json' };
  let payload = body;
  if (unsafe && body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  // Unsafe requests get one retry with a fresh CSRF token (stale/missing cookie).
  for (let attempt = 0; ; attempt += 1) {
    if (unsafe) {
      await ensureCsrf(attempt > 0);
      headers['X-CSRFToken'] = getCookie('csrftoken') || '';
    }
    const res = await fetch(url, { method, headers, body: payload, credentials: 'same-origin', signal });
    const isJson = (res.headers.get('content-type') || '').includes('application/json');
    const data = isJson ? await res.json() : null;
    if (unsafe && attempt === 0 && isCsrfFailure(res.status, data)) continue;
    if (!res.ok) throw new ApiError(res.status, data);
    return data;
  }
}

/** Convert a plain object (and File values) into FormData for multipart posts. */
export function toFormData(obj) {
  const fd = new FormData();
  Object.entries(obj).forEach(([k, v]) => {
    if (v === undefined || v === null) return;
    fd.append(k, v);
  });
  return fd;
}
