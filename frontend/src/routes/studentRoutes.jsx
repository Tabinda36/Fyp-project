// Student pages rendered INSIDE <StudentLayout> (login required).
import { Route } from 'react-router-dom';
import DashboardPage from '../pages/student/DashboardPage';
import AssessmentPage from '../pages/student/AssessmentPage';
import ProfilePage from '../pages/student/ProfilePage';
import NotificationsPage from '../pages/student/NotificationsPage';
import ReportsPage from '../pages/student/ReportsPage';
import PerformancePage from '../pages/student/PerformancePage';
import SettingsPage from '../pages/student/SettingsPage';

export const studentRoutes = [
  <Route key="dashboard" path="/dashboard/" element={<DashboardPage />} />,
  <Route key="student_assessment" path="/assessment/" element={<AssessmentPage />} />,
  <Route key="profile" path="/profile/" element={<ProfilePage />} />,
  <Route key="notifications" path="/notifications/" element={<NotificationsPage />} />,
  <Route key="reports" path="/reports/" element={<ReportsPage />} />,
  <Route key="performance" path="/performance/" element={<PerformancePage />} />,
  <Route key="settings" path="/settings/" element={<SettingsPage />} />,
];
