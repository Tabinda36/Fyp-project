import { Link } from 'react-router-dom';
import { usePageAssets } from '../../hooks/usePageAssets';
import { LOGO_DARK, LOGO_LIGHT } from '../../cdn';
import rawCss from './MainPage.css?raw';
import ThemeToggle from './ThemeToggle';
import { usePublicTheme } from './usePublicTheme';
import { ROOT_PASSTHROUGH } from './rootPassthrough';

const css = rawCss + ROOT_PASSTHROUGH;

const STEPS = [
  {
    number: '01',
    title: 'Set your goal',
    text: 'Choose what you want to learn.',
    icon: (
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="0.6" /></svg>
    ),
  },
  {
    number: '02',
    title: 'Learn every day',
    text: 'Follow focused lessons at your pace.',
    icon: (
      <svg viewBox="0 0 24 24"><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v15H5.5A1.5 1.5 0 0 1 4 17.5z" /><path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v15h5.5a1.5 1.5 0 0 0 1.5-1.5z" /></svg>
    ),
  },
  {
    number: '03',
    title: 'See your progress',
    text: 'Build confidence as your skills grow.',
    icon: (
      <svg viewBox="0 0 24 24"><path d="M4 19h16" /><path d="M6 15l4-4 3 3 5-6" /><path d="M14 8h4v4" /></svg>
    ),
  },
];

export default function MainPage() {
  usePageAssets({ css, title: 'ALVIX - AI Course Generator' });
  const { theme, setTheme } = usePublicTheme();

  return (
    <main className="welcome-page">
      <section className="welcome-copy">
        <header className="welcome-header">
          <Link to="/" className="welcome-brand" aria-label="ALVIX home">
            <img className="welcome-brand__logo" src={theme === 'Light' ? LOGO_LIGHT : LOGO_DARK} alt="ALVIX" />
          </Link>
          <div className="welcome-header__actions">
            <ThemeToggle theme={theme} onChange={setTheme} />
            <Link to="/login/" className="welcome-signin">Sign in</Link>
          </div>
        </header>

        <div className="welcome-content">
          <span className="welcome-badge">AI-powered learning</span>
          <h1>Learn at your pace.<br /><span>Grow with purpose.</span></h1>
          <p className="welcome-intro">
            Turn a learning goal into a clear, personal path. ALVIX brings together daily
            lessons, practical checks, and progress that adapts as you learn.
          </p>

          <div className="welcome-actions">
            <Link to="/signup/" className="welcome-primary">
              Start your journey
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" /></svg>
            </Link>
            <span>Personalized learning, one step at a time</span>
          </div>

          <p className="welcome-steps__title">How it works</p>
          <ol className="welcome-steps">
            {STEPS.map((step) => (
              <li key={step.number}>
                <div className="welcome-steps__top">
                  <span className="welcome-steps__icon" aria-hidden="true">{step.icon}</span>
                  <span className="welcome-steps__number">{step.number}</span>
                </div>
                <strong>{step.title}</strong>
                <small>{step.text}</small>
              </li>
            ))}
          </ol>
        </div>

        <footer className="welcome-footer">
          <span>Made for your next chapter.</span>
          <span>© {new Date().getFullYear()} ALVIX</span>
        </footer>
      </section>

      <aside className="welcome-visual" aria-label="AI-powered learning">
        <img
          className="welcome-visual__image"
          src="/assets/brand/learning-hero.jpg"
          alt="Glowing neural network illustration representing AI-powered learning"
        />
        <div className="welcome-visual__overlay" />
        <span className="welcome-visual__tag">Learning, reimagined</span>
        <div className="welcome-visual__note">
          <span className="welcome-visual__note-mark" aria-hidden="true">01</span>
          <div>
            <strong>From curious to confident</strong>
            <span>Daily lessons. A path that adapts to you.</span>
          </div>
        </div>
      </aside>
    </main>
  );
}
