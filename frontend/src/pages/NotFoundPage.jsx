import { Link } from 'react-router-dom';
import { usePageAssets } from '../hooks/usePageAssets';

export default function NotFoundPage() {
  usePageAssets({ title: 'Page not found | ALVIX' });
  return (
    <div style={{ fontFamily: 'sans-serif', padding: '3rem', textAlign: 'center', color: '#064e3b' }}>
      <h1>Page not found</h1>
      <p>The page you requested does not exist.</p>
      <Link to="/" style={{ color: '#047857' }}>Go to ALVIX home</Link>
    </div>
  );
}
