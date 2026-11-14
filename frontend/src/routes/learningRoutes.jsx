// learningRoutes: pages INSIDE <StudentLayout>; learningStandaloneRoutes: login required, no layout
// (e.g. the certificate page, which renders <StudentLayout> itself only when locked).
import { Route } from 'react-router-dom';
import { CourseDetailPage, MyCoursePage } from '../pages/learning/MyCoursePage';
import CourseContentPage from '../pages/learning/CourseContentPage';
import GenerateCoursePage from '../pages/learning/GenerateCoursePage';
import EnrollLevelPage from '../pages/learning/EnrollLevelPage';
import CurrentLessonPage from '../pages/learning/CurrentLessonPage';
import CertificatePage from '../pages/learning/CertificatePage';

export const learningRoutes = [
  <Route key="mycourse" path="/mycourse/" element={<MyCoursePage />} />,
  <Route key="course_detail" path="/course/:courseId/" element={<CourseDetailPage />} />,
  <Route key="course_content" path="/course_content/" element={<CourseContentPage />} />,
  <Route key="course_content_view" path="/course-content/" element={<CourseContentPage />} />,
  <Route key="generate_course" path="/generate_course/" element={<GenerateCoursePage />} />,
  <Route key="enroll_level" path="/enroll-level/:slug/" element={<EnrollLevelPage />} />,
  <Route key="daily_lesson_current" path="/daily_lesson/" element={<CurrentLessonPage />} />,
];

export const learningStandaloneRoutes = [
  <Route key="certificate" path="/certificate/" element={<CertificatePage />} />,
  <Route key="certificate_course" path="/certificate/:courseId/" element={<CertificatePage />} />,
];
