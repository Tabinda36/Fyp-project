import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

function loginRedirect(location) {
  const next = encodeURIComponent(location.pathname + location.search);
  return <Navigate to={`/login/?next=${next}`} replace />;
}

/** Equivalent of @login_required */
export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return null;
  if (!user) return loginRedirect(location);
  return <Outlet />;
}

/** Equivalent of @login_required + @user_passes_test(admin_required) */
export function RequireAdmin() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return null;
  if (!user || !user.is_admin) return loginRedirect(location);
  return <Outlet />;
}
