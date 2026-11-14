// Port of student_dashboard/logout.html (standalone confirm page).
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { usePageAssets } from '../../hooks/usePageAssets';
import { ICONS_1113, googleFont } from '../../cdn';
import rawCss from './LogoutPage.css?raw';
import { ROOT_PASSTHROUGH } from './rootPassthrough';

const css = rawCss + ROOT_PASSTHROUGH;

const FONT = googleFont('family=Plus+Jakarta+Sans:wght@400;500;600;700;800');

export default function LogoutPage() {
  usePageAssets({ links: [ICONS_1113, FONT], css, title: 'Confirm Logout - ALVIX' });
  const { logout } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    await logout();
    navigate('/login/');
  }

  function handleCancel(e) {
    e.preventDefault();
    window.history.back();
  }

  return (
    <div className="logout-card">
      <div className="logout-icon-wrapper">
        <i className="bi bi-box-arrow-right"></i>
      </div>

      <h2>Confirm Logout</h2>
      <p>Are you sure you want to log out from <strong>ALVIX</strong>?</p>

      <form action="/logout/" method="post" onSubmit={handleSubmit}>
        <button type="submit" className="btn-logout">
          <i className="bi bi-check-circle-fill"></i> Yes, Logout
        </button>
      </form>

      {/* Original: href="javascript:history.back()" (React blocks javascript: URLs) */}
      <a href="#" className="btn-cancel" onClick={handleCancel}>
        <i className="bi bi-x-circle"></i> Cancel
      </a>
    </div>
  );
}
