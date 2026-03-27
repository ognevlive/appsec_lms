import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface TopNavProps {
  variant: 'student' | 'admin';
}

export default function TopNav({ variant }: TopNavProps) {
  const { user } = useAuth();

  const linkClass = (isActive: boolean) =>
    `text-xs uppercase tracking-widest transition-colors duration-150 ${
      isActive
        ? 'text-primary border-b-2 border-primary pb-1 font-bold'
        : 'text-on-surface-variant hover:text-on-surface'
    }`;

  return (
    <header className="bg-surface-container-low fixed top-0 left-0 w-full z-50 flex justify-between items-center px-6 h-16">
      <div className="flex items-center gap-8">
        <span className="text-xl font-bold tracking-tighter text-primary font-headline uppercase">
          LMS AppSec
        </span>
        <nav className="hidden md:flex items-center gap-6">
          {variant === 'student' ? (
            <>
              <NavLink to="/challenges" className={({ isActive }) => linkClass(isActive)}>
                Задания
              </NavLink>
              <NavLink to="/my-results" className={({ isActive }) => linkClass(isActive)}>
                Мои результаты
              </NavLink>
            </>
          ) : (
            <>
              <span className="text-xs uppercase tracking-tight text-on-surface-variant">
                Админка
              </span>
              <div className="h-4 w-px bg-outline-variant/30" />
              <NavLink to="/admin/users" className={({ isActive }) => linkClass(isActive)}>
                Пользователи
              </NavLink>
              <NavLink to="/admin/results" className={({ isActive }) => linkClass(isActive)}>
                Результаты
              </NavLink>
              <NavLink to="/admin/containers" className={({ isActive }) => linkClass(isActive)}>
                Контейнеры
              </NavLink>
            </>
          )}
        </nav>
      </div>
      <div className="flex items-center gap-4">
        {variant === 'student' && (
          <div className="hidden lg:flex items-center bg-surface-container-lowest px-3 py-1.5 rounded-sm border border-outline-variant/15">
            <span className="material-symbols-outlined text-on-surface-variant text-sm mr-2">
              search
            </span>
            <input
              className="bg-transparent border-none text-[10px] focus:ring-0 focus:outline-none p-0 text-on-surface-variant uppercase tracking-widest w-48 placeholder:text-outline-variant"
              placeholder="ПОИСК УЯЗВИМОСТЕЙ..."
              type="text"
            />
          </div>
        )}
        <div className="flex items-center gap-3 pl-4 border-l border-outline-variant/20">
          {variant === 'admin' && (
            <div className="text-right hidden sm:block">
              <p className="text-[10px] font-bold text-tertiary uppercase tracking-widest leading-none">
                Администратор
              </p>
              <p className="text-xs text-on-surface font-medium">{user?.full_name || user?.username}</p>
            </div>
          )}
          {variant === 'student' && (
            <span className="text-on-surface-variant text-xs uppercase font-medium tracking-tight">
              {user?.full_name || user?.username}
            </span>
          )}
          <div className={`w-8 h-8 rounded-sm flex items-center justify-center text-xs font-bold ${
            variant === 'admin'
              ? 'bg-tertiary/20 text-tertiary border border-tertiary/30'
              : 'bg-surface-container-high text-primary border border-primary/20'
          }`}>
            {(user?.full_name || user?.username || '?').charAt(0).toUpperCase()}
          </div>
        </div>
      </div>
    </header>
  );
}
