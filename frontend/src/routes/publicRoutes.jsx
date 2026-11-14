// Public area routes (no layout). Paths must equal the original Django URL paths.
// publicRoutes: anyone; publicAuthRoutes: login required, standalone pages (e.g. suggested_courses).
import { Route } from 'react-router-dom';
import MainPage from '../pages/public/MainPage';
import LoginPage from '../pages/public/LoginPage';
import SignupPage from '../pages/public/SignupPage';
import VerifyOtpPage from '../pages/public/VerifyOtpPage';
import LogoutPage from '../pages/public/LogoutPage';
import SuggestedCoursesPage from '../pages/public/SuggestedCoursesPage';
import CertificateVerifyPage from '../pages/public/CertificateVerifyPage';

export const publicRoutes = [
  <Route key="mainpage" path="/" element={<MainPage />} />,
  <Route key="login" path="/login/" element={<LoginPage />} />,
  <Route key="signup" path="/signup/" element={<SignupPage />} />,
  <Route key="verify_otp" path="/verify-otp/" element={<VerifyOtpPage />} />,
  <Route key="logout" path="/logout/" element={<LogoutPage />} />,
  <Route key="verify_certificate" path="/verify-certificate/:certId/" element={<CertificateVerifyPage />} />,
];

export const publicAuthRoutes = [
  <Route key="suggested_courses" path="/suggested_courses/" element={<SuggestedCoursesPage />} />,
];
