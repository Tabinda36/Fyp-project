import { usePageError } from '../hooks/pageStatus';

/**
 * Centred loading indicator for admin/student pages while their data loads.
 * If the page's data request failed (server/network error), shows an error card with Retry instead.
 */
export default function AdminLoader({ label = 'Loading' }) {
  const failure = usePageError();

  if (failure) {
    return (
      <div className="adm-loader adm-loader--error" role="alert">
        <span className="adm-loader__error-icon" aria-hidden="true"><i className="bi bi-cloud-slash"></i></span>
        <strong className="adm-loader__error-title">{failure.title}</strong>
        <p className="adm-loader__error-text">{failure.message}</p>
        <button type="button" className="adm-loader__retry" onClick={() => failure.retry?.()}>
          <i className="bi bi-arrow-clockwise"></i> Try again
        </button>
      </div>
    );
  }

  return (
    <div className="adm-loader" role="status" aria-live="polite">
      <span className="adm-loader__ring" aria-hidden="true" />
      <span className="adm-loader__text">{label}…</span>
    </div>
  );
}
