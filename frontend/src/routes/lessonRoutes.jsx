// Lesson player / assignment / quiz pages rendered INSIDE <StudentLayout>.
import { Route } from 'react-router-dom';
import DailyLessonPage from '../pages/lessons/DailyLessonPage';
import AssignmentPage from '../pages/lessons/AssignmentPage';
import QuizPage from '../pages/lessons/QuizPage';

export const lessonRoutes = [
  <Route key="daily-lesson" path="/daily-lesson/:lessonId/" element={<DailyLessonPage />} />,
  <Route key="assignment" path="/assignment/" element={<AssignmentPage />} />,
  <Route key="quiz" path="/quiz/" element={<QuizPage />} />,
  <Route key="quiz-detail" path="/quiz/:lessonId/" element={<QuizPage />} />,
];
