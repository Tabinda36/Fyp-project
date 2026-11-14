import { useLocation } from 'react-router-dom';
import { usePageData } from '../../hooks/usePageData';
import AdminLoader from '../../layouts/AdminLoader';
import NotFoundPage from '../NotFoundPage';

/*
 * /daily_lesson/ — view `daily_lesson_view` (redirect only).
 * GET /api/v1/learning/current-lesson/ returns `redirect: '/daily-lesson/<id>/'`, or the
 * "No active lesson found." message with `redirect: '/course-content/'`; usePageData follows it.
 */
export default function CurrentLessonPage() {
  const { search } = useLocation();
  const params = new URLSearchParams(search);
  const { notFound, error } = usePageData('/learning/current-lesson/', {
    lesson_id: params.get('lesson_id'),
    course_id: params.get('course_id'),
  });
  if (notFound) return <NotFoundPage />;
  // Server/network failure: error card with Retry (the loader stays hidden on a normal redirect).
  return error ? <AdminLoader /> : null;
}
