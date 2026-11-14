export default function AuthShowcase() {
  return (
    <aside className="auth-showcase" aria-label="About ALVIX learning">
      <img
        className="auth-showcase__image"
        src="/assets/brand/learning-hero.jpg"
        alt="Glowing neural network illustration representing AI-powered learning"
      />
      <div className="auth-showcase__overlay" />
      <div className="auth-showcase__content">
        <p className="auth-showcase__eyebrow">Learn · Adapt · Evolve</p>
        <h2>Make room for<br /><span>what&apos;s next.</span></h2>
        <p className="auth-showcase__description">
          Build real understanding with a learning path shaped around your goals and pace.
        </p>
        <ul className="auth-showcase__benefits">
          <li><span aria-hidden="true">01</span>Personalized course paths</li>
          <li><span aria-hidden="true">02</span>Focused daily lessons</li>
          <li><span aria-hidden="true">03</span>Progress you can follow</li>
        </ul>
      </div>
      <span className="auth-showcase__footer">Your next skill starts here.</span>
    </aside>
  );
}
