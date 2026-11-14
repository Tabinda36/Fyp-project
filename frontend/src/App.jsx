import { Route, Routes } from 'react-router-dom';
import StudentLayout from './layouts/StudentLayout';
import AdminLayout from './layouts/AdminLayout';
import { RequireAdmin, RequireAuth } from './routes/guards';
import { publicAuthRoutes, publicRoutes } from './routes/publicRoutes';
import { studentRoutes } from './routes/studentRoutes';
import { learningRoutes, learningStandaloneRoutes } from './routes/learningRoutes';
import { lessonRoutes } from './routes/lessonRoutes';
import { adminRoutes } from './routes/adminRoutes';
import { adminCourseRoutes } from './routes/adminCourseRoutes';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <Routes>
      {publicRoutes}

      <Route element={<RequireAuth />}>
        {publicAuthRoutes}
        {learningStandaloneRoutes}
        <Route element={<StudentLayout />}>
          {studentRoutes}
          {learningRoutes}
          {lessonRoutes}
        </Route>
      </Route>

      <Route element={<RequireAdmin />}>
        <Route element={<AdminLayout />}>
          {adminRoutes}
          {adminCourseRoutes}
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
