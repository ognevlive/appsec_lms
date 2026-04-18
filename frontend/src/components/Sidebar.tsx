import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface SidebarProps {
  variant: 'student' | 'admin';
}

interface SidebarItem {
  to: string;
  icon: string;
  label: string;
}

const studentItems: SidebarItem[] = [
  { to: '/courses', icon: 'school', label: 'Курсы' },
  { to: '/challenges', icon: 'security', label: 'Уязвимости' },
  { to: '/my-results', icon: 'analytics', label: 'Мои результаты' },
];

const adminItems: SidebarItem[] = [
  { to: '/admin/users', icon: 'group', label: 'Пользователи' },
  { to: '/admin/courses', icon: 'school', label: 'Курсы' },
  { to: '/admin/tasks', icon: 'task_alt', label: 'Таски' },
  { to: '/admin/results', icon: 'bug_report', label: 'Результаты' },
  { to: '/admin/containers', icon: 'dns', label: 'Контейнеры' },
];

export default function Sidebar({ variant }: SidebarProps) {
  const { logout } = useAuth();
  const items = variant === 'student' ? studentItems : adminItems;

  const itemClass = (isActive: boolean) =>
    `flex items-center gap-3 px-4 py-3 transition-all duration-150 ${
      isActive
        ? 'bg-primary/10 text-primary border-l-4 border-primary'
        : 'text-on-surface-variant hover:bg-[#1a1b26] hover:text-on-surface'
    }`;

  return (
    <aside className="fixed left-0 top-16 h-[calc(100vh-64px)] w-64 bg-surface-container-low border-r border-outline-variant/15 z-40 hidden md:flex flex-col">
      <div className="p-6 flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_#8eff71]" />
        <div>
          <h3 className="text-on-surface font-medium text-sm">
            {variant === 'admin' ? 'Сектор Админа' : 'Студент'}
          </h3>
          <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter">
            Система активна
          </p>
        </div>
      </div>
      <nav className="flex-1 px-2 space-y-1">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => itemClass(isActive)}
          >
            {({ isActive }) => (
              <>
                <span
                  className="material-symbols-outlined"
                  style={isActive ? { fontVariationSettings: "'FILL' 1" } : undefined}
                >
                  {item.icon}
                </span>
                <span className="font-body font-medium text-sm">{item.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-outline-variant/10">
        <button
          onClick={logout}
          className="flex items-center gap-3 text-on-surface-variant px-4 py-3 hover:bg-[#1a1b26] hover:text-on-surface transition-all duration-150 w-full"
        >
          <span className="material-symbols-outlined">logout</span>
          <span className="font-body font-medium text-sm">Выход</span>
        </button>
      </div>
    </aside>
  );
}
