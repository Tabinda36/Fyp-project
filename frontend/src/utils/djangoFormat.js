/*
 * Ports of the Django template filters used by ALVIX templates, producing the
 * same output so text in React matches the server-rendered pages exactly.
 * Dates arrive from the API as ISO strings already converted to the server
 * time zone (Asia/Karachi) by Django, so we format the wall-clock parts as-is.
 */

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const MONTHS_AP = ['Jan.', 'Feb.', 'March', 'April', 'May', 'June', 'July', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'];
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

/** Parse "2026-11-14T10:05:00+05:00" or "2026-11-14" into wall-clock parts (no TZ shift). */
function parts(value) {
  if (!value) return null;
  const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (!m) return null;
  return {
    Y: +m[1], n: +m[2], j: +m[3],
    G: m[4] !== undefined ? +m[4] : 0,
    i: m[5] !== undefined ? +m[5] : 0,
    s: m[6] !== undefined ? +m[6] : 0,
  };
}

const pad = (n) => String(n).padStart(2, '0');
const NBSP = String.fromCharCode(160); // Django's timesince joins number and unit with a non-breaking space

/** Django `|date:"..."` — supports the format characters ALVIX templates use. */
export function djDate(value, format = 'N j, Y') {
  const p = parts(value);
  if (!p) return '';
  const dow = new Date(p.Y, p.n - 1, p.j).getDay();
  const h12 = p.G % 12 === 0 ? 12 : p.G % 12;
  const map = {
    d: pad(p.j), j: String(p.j), D: DAYS[dow].slice(0, 3), l: DAYS[dow],
    m: pad(p.n), n: String(p.n), M: MONTHS[p.n - 1].slice(0, 3), F: MONTHS[p.n - 1], N: MONTHS_AP[p.n - 1], b: MONTHS[p.n - 1].slice(0, 3).toLowerCase(),
    Y: String(p.Y), y: String(p.Y).slice(-2),
    H: pad(p.G), G: String(p.G), h: pad(h12), g: String(h12), i: pad(p.i), s: pad(p.s),
    A: p.G < 12 ? 'AM' : 'PM', a: p.G < 12 ? 'a.m.' : 'p.m.',
    P: p.i === 0 ? (p.G === 0 ? 'midnight' : p.G === 12 ? 'noon' : `${h12} ${p.G < 12 ? 'a.m.' : 'p.m.'}`) : `${h12}:${pad(p.i)} ${p.G < 12 ? 'a.m.' : 'p.m.'}`,
  };
  let out = '';
  for (let k = 0; k < format.length; k += 1) {
    const ch = format[k];
    if (ch === '\\') { out += format[k + 1] || ''; k += 1; } else out += ch in map ? map[ch] : ch;
  }
  return out;
}

/** Django `|timesince` (largest two units, e.g. "3 days, 4 hours"). */
export function timesince(value, now = new Date()) {
  if (!value) return '';
  const then = new Date(value);
  let seconds = Math.max(0, Math.floor((now - then) / 1000));
  const units = [
    ['year', 365 * 86400], ['month', 30 * 86400], ['week', 7 * 86400],
    ['day', 86400], ['hour', 3600], ['minute', 60],
  ];
  const out = [];
  for (const [name, size] of units) {
    const count = Math.floor(seconds / size);
    if (count || out.length) {
      if (count) out.push(`${count}${NBSP}${name}${count === 1 ? '' : 's'}`);
      seconds -= count * size;
      if (out.length === 2 || (out.length && !count)) break;
    }
  }
  return out.length ? out.join(', ') : `0${NBSP}minutes`;
}

/** Django `|truncatechars:n` */
export function truncatechars(value, n) {
  const s = value == null ? '' : String(value);
  return s.length > n ? `${s.slice(0, Math.max(0, n - 1))}…` : s;
}

/** Django `|truncatewords:n` */
export function truncatewords(value, n) {
  const words = (value == null ? '' : String(value)).split(/\s+/).filter(Boolean);
  return words.length > n ? `${words.slice(0, n).join(' ')} …` : words.join(' ');
}

/** Django `|floatformat:d` (default -1: one decimal only when needed) */
export function floatformat(value, d = -1) {
  const num = Number(value);
  if (Number.isNaN(num)) return '';
  const places = Math.abs(d);
  const fixed = num.toFixed(places);
  if (d < 0 && Number(fixed) === Math.trunc(num) && Number.isInteger(Number(fixed))) return String(Math.round(num));
  return fixed;
}

/** Django `|default:x` */
export const dflt = (value, fallback) => (value === null || value === undefined || value === '' || value === false || (Array.isArray(value) && !value.length) ? fallback : value);

/** Django `{% widthratio a b max %}` */
export const widthratio = (a, b, max) => (Number(b) ? Math.round((Number(a) / Number(b)) * max) : 0);

/** Django `|linebreaksbr` -> array of strings/<br/> for JSX: lines(value).map(...) */
export const lines = (value) => (value == null ? [] : String(value).split(/\r\n|\r|\n/));
