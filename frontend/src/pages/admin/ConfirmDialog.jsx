import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

/**
 * Accessible confirmation dialog (replaces the old Bootstrap modals).
 * <ConfirmDialog open title message confirmLabel tone="danger" busy onConfirm onCancel />
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  detail,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'danger',
  busy = false,
  onConfirm,
  onCancel,
}) {
  const cancelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    cancelRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape' && !busy) onCancel(); };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, busy, onCancel]);

  if (!open) return null;

  return createPortal(
    <div className="adm-dialog" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) onCancel(); }}>
      <div className={`adm-dialog__panel is-${tone}`} role="alertdialog" aria-modal="true" aria-labelledby="adm-dialog-title" aria-describedby="adm-dialog-msg">
        <span className="adm-dialog__icon" aria-hidden="true">
          <i className={`bi ${tone === 'danger' ? 'bi-trash3-fill' : 'bi-question-circle-fill'}`}></i>
        </span>
        <h2 id="adm-dialog-title" className="adm-dialog__title">{title}</h2>
        <p id="adm-dialog-msg" className="adm-dialog__msg">{message}</p>
        {detail ? <p className="adm-dialog__detail">{detail}</p> : null}
        <div className="adm-dialog__actions">
          <button type="button" ref={cancelRef} className="adm-dialog__btn adm-dialog__btn--ghost" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </button>
          <button type="button" className={`adm-dialog__btn adm-dialog__btn--${tone}`} onClick={onConfirm} disabled={busy}>
            {busy ? <span className="adm-dialog__spinner" aria-hidden="true" /> : null}
            {busy ? 'Please wait…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
