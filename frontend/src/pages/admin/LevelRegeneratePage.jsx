import { useEffect, useRef } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useFlash } from '../../hooks/useFlash';
import { apiFetch } from '../../api/client';
import { REGEN_CONFIRM } from './LevelCourseViewPage';

/* `/admindashboard/level/<slug>/regenerate/` (admin_regenerate_deep_curriculum): no page of its own.
   Regenerates the deep curriculum, then goes back to the level studio with the success message. */
export default function LevelRegeneratePage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { addMessages } = useFlash();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // run once (StrictMode re-runs effects in development)
    started.current = true;
    // Regeneration replaces the level's curriculum. Never run it just because a URL was opened:
    // the studio button confirms first (and passes state); any other visit asks here.
    if (!location.state?.confirmed && !window.confirm(REGEN_CONFIRM)) {
      navigate(`/admindashboard/level/${slug}/course/`, { replace: true });
      return;
    }
    apiFetch(`/admin-courses/levels/${slug}/regenerate/`, { method: 'POST' })
      .then((res) => {
        addMessages(res.messages);
        navigate(res.redirect || `/admindashboard/level/${slug}/course/`, { replace: true });
      })
      .catch((err) => {
        if (err.status === 401 || err.status === 403) {
          navigate(`/login/?next=${encodeURIComponent(location.pathname)}`, { replace: true });
        } else {
          navigate(`/admindashboard/level/${slug}/course/`, { replace: true });
        }
      });
  }, [slug, navigate, addMessages, location.pathname, location.state]);

  return null;
}
