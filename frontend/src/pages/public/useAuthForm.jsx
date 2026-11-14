// Controlled-form state for the auth pages: values, touched fields and live errors.
// Errors appear once a field is blurred (or on submit), then update as the user types.
import { useCallback, useMemo, useState } from 'react';
import { runValidators } from './authValidation';

export function useAuthForm(initialValues, validators) {
  const [values, setValues] = useState(initialValues);
  const [touched, setTouched] = useState({});

  const errors = useMemo(() => runValidators(validators, values), [validators, values]);

  const setValue = useCallback((name, value) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleChange = useCallback((event) => {
    const { name, type, checked, value } = event.target;
    setValue(name, type === 'checkbox' ? checked : value);
  }, [setValue]);

  const handleBlur = useCallback((event) => {
    const { name } = event.target;
    setTouched((prev) => (prev[name] ? prev : { ...prev, [name]: true }));
  }, []);

  /** Marks every validated field as touched; returns the first invalid field name or null. */
  const validateAll = useCallback(() => {
    setTouched(Object.fromEntries(Object.keys(validators).map((name) => [name, true])));
    return Object.keys(validators).find((name) => errors[name]) || null;
  }, [validators, errors]);

  const reset = useCallback((nextValues = initialValues) => {
    setValues(nextValues);
    setTouched({});
  }, [initialValues]);

  /** Props for an input: value/handlers plus aria wiring to its <FieldError>. */
  const fieldProps = useCallback((name) => {
    const showError = Boolean(touched[name] && errors[name]);
    return {
      name,
      value: values[name],
      onChange: handleChange,
      onBlur: handleBlur,
      'aria-invalid': showError || undefined,
      'aria-describedby': showError ? `${name}-error` : undefined,
      className: `form-control${showError ? ' is-invalid' : ''}${touched[name] && !errors[name] && values[name] ? ' is-valid' : ''}`,
    };
  }, [values, touched, errors, handleChange, handleBlur]);

  const visibleError = (name) => (touched[name] ? errors[name] || '' : '');

  return { values, setValue, errors, touched, fieldProps, visibleError, validateAll, reset, handleChange };
}

export function FieldError({ name, message }) {
  if (!message) return null;
  return (
    <span className="auth-field-error" id={`${name}-error`} role="alert">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7.5v5.5M12 16.5h.01" />
      </svg>
      {message}
    </span>
  );
}

export function PasswordEye({ visible }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
      {visible ? <path d="m3 3 18 18" /> : null}
    </svg>
  );
}

export function Spinner() {
  return <span className="auth-spinner" aria-hidden="true" />;
}
