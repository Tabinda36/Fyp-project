import { useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { useFlash } from '../hooks/useFlash';

/*
 * Shows the flash queue (Django-style `messages` pushed with addMessages) as toasts for
 * admin pages that don't render it themselves. Pages that render their own alerts
 * (Avatar Settings) are skipped via `disabled`.
 */
export default function AdminFlash({ disabled = false }) {
  const { queue, dismiss } = useFlash();
  const shown = useRef(new Set());

  useEffect(() => {
    if (disabled) return;
    queue.forEach((m) => {
      if (shown.current.has(m.id)) return;
      shown.current.add(m.id);
      const tag = m.tags || 'info';
      if (tag === 'error' || tag === 'danger') toast.error(m.message);
      else if (tag === 'success') toast.success(m.message);
      else toast(m.message, { icon: tag === 'warning' ? '⚠️' : 'ℹ️' });
      dismiss(m.id);
    });
  }, [queue, dismiss, disabled]);

  return null;
}
