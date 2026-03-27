import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import TopNav from '../components/TopNav';
import Sidebar from '../components/Sidebar';
import MobileNav from '../components/MobileNav';

export default function AppLayout() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <span className="text-primary animate-pulse font-headline text-xl">Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen bg-background">
      <TopNav variant="student" />
      <Sidebar variant="student" />
      <main className="md:ml-64 pt-20 px-6 pb-24 md:pb-12 min-h-screen">
        <Outlet />
      </main>
      <MobileNav variant="student" />
    </div>
  );
}
