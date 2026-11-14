import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch } from '../api/client';

/**
 * Loads page data from the API.
 *   const { data, loading, error, reload, setData } = useApi('/student/dashboard/', { course_id });
 * Pass `null` as path to skip loading.
 */
export function useApi(path, query) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState(null);
  const queryKey = JSON.stringify(query || {});
  const controllerRef = useRef(null);

  const load = useCallback(async () => {
    if (!path) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch(path, { query: JSON.parse(queryKey), signal: controller.signal });
      setData(result);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [path, queryKey]);

  useEffect(() => {
    load();
    return () => controllerRef.current?.abort();
  }, [load]);

  return { data, loading, error, reload: load, setData };
}
