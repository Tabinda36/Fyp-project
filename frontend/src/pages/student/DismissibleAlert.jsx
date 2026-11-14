import { useState } from 'react';
import { useFlash } from '../../hooks/useFlash';

/*
 * `<div class="alert ... alert-dismissible fade show">` + `<button class="btn-close" data-bs-dismiss="alert">`
 * with the same markup and fade-out, but closed through React: Bootstrap's own handler would
 * remove a DOM node React still owns.
 */
export default function DismissibleAlert({ id, className, style, role = 'alert', children }) {
  const { dismiss } = useFlash();
  const [shown, setShown] = useState(true);

  const close = (event) => {
    event.stopPropagation(); // keep Bootstrap's document-level data-bs-dismiss handler out of it
    setShown(false);
    setTimeout(() => dismiss(id), 150); // Bootstrap's .fade transition
  };

  return (
    <div className={`${className}${shown ? ' show' : ''}`} role={role} style={style}>
      {children}
      <button type="button" className="btn-close" data-bs-dismiss="alert" aria-label="Close" onClick={close}></button>
    </div>
  );
}
