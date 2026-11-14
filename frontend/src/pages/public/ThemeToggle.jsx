export default function ThemeToggle({ theme, onChange, className = '' }) {
  const light = theme === 'Light';

  return (
    <button
      type="button"
      className={`theme-toggle ${className}`.trim()}
      aria-label={`Switch to ${light ? 'dark' : 'light'} theme`}
      aria-pressed={light}
      onClick={() => onChange(light ? 'Dark' : 'Light')}
    >
      <span className="theme-toggle__icon" aria-hidden="true">{light ? '☼' : '☾'}</span>
      <span>{light ? 'Light' : 'Dark'}</span>
    </button>
  );
}
