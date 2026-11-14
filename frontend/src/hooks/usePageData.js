import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useApi } from './useApi';
import { useFlash } from './useFlash';
import { setPageError } from './pageStatus';

/**
 * useApi + the conventions every page endpoint follows:
 *  - `{ redirect: '/path/' }` in the payload  -> navigate there (like a Django redirect)
 *  - `{ messages: [...] }` in the payload      -> pushed to flash messages
 *  - 401/403                                  -> /login/?next=<current path>
 *  - 404                                      -> `notFound` flag for the page
 */
export function usePageData(path, query) {
  const result = useApi(path, query);
  const navigate = useNavigate();
  const location = useLocation();
  const { addMessages } = useFlash();
  const { data, error } = result;

  useEffect(() => {
    if (!data) return;
    if (data.messages) addMessages(data.messages);
    if (data.redirect) navigate(data.redirect, { replace: true });
  }, [data, addMessages, navigate]);

  useEffect(() => {
    if (error && (error.status === 401 || error.status === 403)) {
      const next = encodeURIComponent(location.pathname + location.search);
      navigate(`/login/?next=${next}`, { replace: true });
    }
  }, [error, navigate, location.pathname, location.search]);

  // Server/network failures (not auth/404): let the page loader show an error + Retry.
  const { reload } = result;
  useEffect(() => {
    if (!error || [401, 403, 404].includes(error.status)) return undefined;
    const offline = !error.status;
    setPageError({
      title: offline ? 'Can’t reach the server' : 'Something went wrong',
      message: offline
        ? 'Check that the backend is running and your connection is online, then try again.'
        : `The server returned an error (${error.status}). Please try again in a moment.`,
      retry: reload,
    });
    return () => setPageError(null);
  }, [error, reload]);

  return { ...result, notFound: error?.status === 404, ready: Boolean(data) && !data.redirect };
}
