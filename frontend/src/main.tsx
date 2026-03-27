import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AuthLayout from './layouts/AuthLayout';
import AppLayout from './layouts/AppLayout';
import AdminLayout from './layouts/AdminLayout';
import LoginPage from './pages/LoginPage';
import CatalogPage from './pages/CatalogPage';
import ChallengeDetailsPage from './pages/ChallengeDetailsPage';
import MyResultsPage from './pages/MyResultsPage';
import TracksPage from './pages/TracksPage';
import TrackDetailPage from './pages/TrackDetailPage';
import AdminUsersPage from './pages/admin/AdminUsersPage';
import AdminResultsPage from './pages/admin/AdminResultsPage';
import AdminContainersPage from './pages/admin/AdminContainersPage';
import './main.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
          </Route>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/tracks" replace />} />
            <Route path="/tracks" element={<TracksPage />} />
            <Route path="/tracks/:id" element={<TrackDetailPage />} />
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
