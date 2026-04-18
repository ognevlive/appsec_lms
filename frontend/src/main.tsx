import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AuthLayout from './layouts/AuthLayout';
import AppLayout from './layouts/AppLayout';
import AdminLayout from './layouts/AdminLayout';
import LoginPage from './pages/LoginPage';
import CatalogPage from './pages/CatalogPage';
import ChallengeDetailsPage from './pages/ChallengeDetailsPage';
import MyResultsPage from './pages/MyResultsPage';
import CoursesPage from './pages/CoursesPage';
import CourseDetailPage from './pages/CourseDetailPage';
import AdminUsersPage from './pages/admin/AdminUsersPage';
import AdminResultsPage from './pages/admin/AdminResultsPage';
import AdminContainersPage from './pages/admin/AdminContainersPage';
import './main.css';

function TrackIdRedirect() {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/courses/${id}`} replace />;
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
          </Route>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/courses" replace />} />
            <Route path="/courses" element={<CoursesPage />} />
            <Route path="/courses/:slug" element={<CourseDetailPage />} />
            <Route path="/tracks" element={<Navigate to="/courses" replace />} />
            <Route path="/tracks/:id" element={<TrackIdRedirect />} />
            <Route path="/challenges" element={<CatalogPage />} />
            <Route path="/challenges/:id" element={<ChallengeDetailsPage />} />
            <Route path="/my-results" element={<MyResultsPage />} />
          </Route>
          <Route element={<AdminLayout />}>
            <Route path="/admin" element={<Navigate to="/admin/users" replace />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
            <Route path="/admin/results" element={<AdminResultsPage />} />
            <Route path="/admin/containers" element={<AdminContainersPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
