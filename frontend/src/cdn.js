// Exact CDN stylesheets used by the original Django templates.
// Pages pass the ones their template loaded to usePageAssets(), keeping versions identical.

export const BOOTSTRAP_533 = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css';
export const BOOTSTRAP_530 = 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css';
export const ICONS_1113 = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css';
export const ICONS_1111 = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css';

export const googleFont = (query) => `https://fonts.googleapis.com/css2?${query}&display=swap`;

export const FONT_ADMIN = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Poppins:wght@700;800;900');

export const LOGO_LIGHT = '/assets/brand/alvix-logo.png';
export const LOGO_DARK = LOGO_LIGHT;
export const LOGO = LOGO_LIGHT;
