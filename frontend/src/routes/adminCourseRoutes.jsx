// Admin course-management pages rendered INSIDE <AdminLayout>.
import { Route } from 'react-router-dom';
import CoursesInfoPage from '../pages/admin/CoursesInfoPage';
import AddCoursePage from '../pages/admin/AddCoursePage';
import CourseDetailsPage from '../pages/admin/CourseDetailsPage';
import LevelCourseViewPage from '../pages/admin/LevelCourseViewPage';
import LevelRegeneratePage from '../pages/admin/LevelRegeneratePage';
import LevelUsersTelemetryPage from '../pages/admin/LevelUsersTelemetryPage';

export const adminCourseRoutes = [
  <Route key="courses_info" path="/courses_info/" element={<CoursesInfoPage />} />,
  <Route key="add_course" path="/add_course/" element={<AddCoursePage />} />,
  <Route key="course_details" path="/course_details/:slug/" element={<CourseDetailsPage />} />,
  <Route key="admin_course_level_detail" path="/admindashboard/level/:slug/course/" element={<LevelCourseViewPage />} />,
  <Route key="admin_regenerate_deep_curriculum" path="/admindashboard/level/:slug/regenerate/" element={<LevelRegeneratePage />} />,
  <Route key="admin_course_level_users" path="/admindashboard/level/:slug/users/" element={<LevelUsersTelemetryPage />} />,
];
