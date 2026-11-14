import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/** Server-rendered pages always opened at the top; keep that on client-side navigation. */
export default function ScrollToTop() {
  const { pathname, search } = useLocation();
  useEffect(() => {
    if (!window.location.hash) window.scrollTo(0, 0);
  }, [pathname, search]);
  return null;
}
