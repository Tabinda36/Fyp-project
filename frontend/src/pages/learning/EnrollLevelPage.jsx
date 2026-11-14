import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { useFlash } from '../../hooks/useFlash';
import AdminLoader from '../../layouts/AdminLoader';
import { setPageError } from '../../hooks/pageStatus';
import NotFoundPage from '../NotFoundPage';

/*
 * /enroll-level/:slug/ — view `enroll_level_view` (no template, redirect only).
 * Runs POST /api/v1/learning/enroll-level/<slug>/ once on mount, then navigates to the
 * returned redirect (/course_content/?course_id=..) with the success message.
 */
export default function EnrollLevelPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { addMessages } = useFlash();
  const [notFound, setNotFound] = useState(false);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const started = useRef(null);

  useEffect(() => {
    const key = `${slug}#${attempt}`;
    if (started.current === key) return; // StrictMode re-runs effects: enrol only once per attempt
    started.current = key;
    apiFetch(`/learning/enroll-level/${encodeURIComponent(slug)}/`, { method: 'POST' })
      .then((res) => {
        addMessages(res.messages);
        navigate(res.redirect, { replace: true });
      })
      .catch((err) => {
        if (err.status === 401 || err.status === 403) {
          navigate(`/login/?next=${encodeURIComponent(location.pathname + location.search)}`, { replace: true });
        } else if (err.status === 404) {
          setNotFound(true);
        } else {
          // Server/network failure: show the error card with Retry instead of a blank page.
          console.error('Error:', err);
          setPageError({
            title: !err.status ? 'Can’t reach the server' : 'Could not start this course',
            message: !err.status
              ? 'Check that the backend is running and your connection is online, then try again.'
              : `The server returned an error (${err.status}) while enrolling you. Please try again in a moment.`,
            retry: () => { setPageError(null); setFailed(false); setAttempt((a) => a + 1); },
          });
          setFailed(true);
        }
      });
  }, [slug, attempt, navigate, addMessages, location.pathname, location.search]);

  useEffect(() => () => setPageError(null), []);

  if (notFound) return <NotFoundPage />;
  return <AdminLoader label={failed ? 'Loading' : 'Setting up your course'} />;
}
