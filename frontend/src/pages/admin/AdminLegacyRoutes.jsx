import { useEffect, useRef } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { useFlash } from '../../hooks/useFlash';
import NotFoundPage from '../NotFoundPage';

/*
 * Legacy admin URLs that never rendered a page of their own.
 */

/**
 * `/delete_user/<id>/`: the legacy view deleted the user on a plain GET, so any link an admin
 * clicked could delete an account. For safety this route no longer deletes anything; users are
 * deleted from User Management through its confirmation modal.
 */
export function DeleteUserRoute() {
  const { userId } = useParams();
  if (!/^\d+$/.test(userId)) return <NotFoundPage />;
  return <Navigate to="/user_management/" replace />;
}

/** `/edit_user/<id>/`: editing now lives on the user details page. */
export function EditUserRoute() {
  const { userId } = useParams();
  if (!/^\d+$/.test(userId)) return <NotFoundPage />;
  return <Navigate to={`/user_management/${userId}/?tab=edit`} replace />;
}

/** `/toggle_system_mode/`: only flashed a message and redirected to the dashboard (no state changes). */
export function ToggleSystemModeRoute() {
  const navigate = useNavigate();
  const { addMessage } = useFlash();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    addMessage('success', 'System mode updated successfully.');
    navigate('/admindashboard/', { replace: true });
  }, [addMessage, navigate]);

  return null;
}
