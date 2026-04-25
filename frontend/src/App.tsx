import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { Sidebar } from './components/layout/Sidebar';
import { AuthPage } from './pages/AuthPage';
import { QueryDashboard } from './pages/QueryDashboard';
import { HistoryPage } from './pages/HistoryPage';
import { AdminDashboard } from './pages/AdminDashboard';

const ProtectedRoute: React.FC<{ children: React.ReactNode; adminOnly?: boolean }> = ({ children, adminOnly }) => {
  const { user, isLoading } = useAuth();
  
  if (isLoading) return <div className="page-container loading-state"><span className="spinner"></span></div>;
  if (!user) return <Navigate to="/login" />;
  if (adminOnly && user.role !== 'admin' && user.role !== 'superuser') return <Navigate to="/" />;

  return <>{children}</>;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />
      <Route
        path="/*"
        element={
          <div id="root-layout">
            <Sidebar />
            <div className="main-wrapper">
              <main className="main-content">
                <Routes>
                  <Route path="/" element={<ProtectedRoute><QueryDashboard /></ProtectedRoute>} />
                  <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
                  <Route path="/admin" element={<ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>} />
                </Routes>
              </main>
            </div>
          </div>
        }
      />
    </Routes>
  );
};
