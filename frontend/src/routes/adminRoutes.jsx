// Admin pages rendered INSIDE <AdminLayout> (admin required).
import { Route } from 'react-router-dom';
import AdminDashboardPage from '../pages/admin/AdminDashboardPage';
import UserManagementPage from '../pages/admin/UserManagementPage';
import UserDetailPage from '../pages/admin/UserDetailPage';
import AdminReportsPage from '../pages/admin/AdminReportsPage';
import AdminNotificationsPage from '../pages/admin/AdminNotificationsPage';
import AnalyticsPage from '../pages/admin/AnalyticsPage';
import AvatarSettingsPage from '../pages/admin/AvatarSettingsPage';
import { DeleteUserRoute, EditUserRoute, ToggleSystemModeRoute } from '../pages/admin/AdminLegacyRoutes';

export const adminRoutes = [
  <Route key="admin_dashboard" path="/admindashboard/" element={<AdminDashboardPage />} />,
  <Route key="user_management" path="/user_management/" element={<UserManagementPage />} />,
  <Route key="user_detail" path="/user_management/:userId/" element={<UserDetailPage />} />,
  <Route key="edit_user" path="/edit_user/:userId/" element={<EditUserRoute />} />,
  <Route key="delete_user" path="/delete_user/:userId/" element={<DeleteUserRoute />} />,
  <Route key="toggle_system_mode" path="/toggle_system_mode/" element={<ToggleSystemModeRoute />} />,
  <Route key="analytics" path="/analytics/" element={<AnalyticsPage />} />,
  <Route key="admin_notifications" path="/admin_notifications/" element={<AdminNotificationsPage />} />,
  <Route key="admin_reports" path="/admin_reports/" element={<AdminReportsPage />} />,
  <Route key="admin_avatar_settings" path="/admindashboard/avatar-settings/" element={<AvatarSettingsPage />} />,
];
