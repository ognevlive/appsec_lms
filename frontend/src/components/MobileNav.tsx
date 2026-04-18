import { NavLink } from 'react-router-dom';

interface MobileNavProps {
  variant: 'student' | 'admin';
}

interface MobileNavItem {
  to: string;
  icon: string;
  label: string;
}

const studentItems: MobileNavItem[] = [
  { to: '/courses', icon: 'school', label: 'Курсы' },
  { to: '/challenges', icon: 'security', label: 'Задания' },
  { to: '/my-results', icon: 'analytics', label: 'Результаты' },
];

const adminItems: MobileNavItem[] = [
  { to: '/admin/users', icon: 'group', label: 'Пользователи' },
  { to: '/admin/results', icon: 'bug_report', label: 'Результаты' },
  { to: '/admin/containers', icon: 'dns', label: 'Контейнеры' },
];

export default function MobileNav({ variant }: MobileNavProps) {
  const items = variant === 'student' ? studentItems : adminItems;

  return (
    <nav className="fixed bottom-0 left-0 w-full bg-surface-container z-50 flex md:hidden border-t border-outline-variant/15">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center gap-1 py-3 transition-colors ${
              isActive ? 'text-primary' : 'text-on-surface-variant'
            }`
          }
        >
          <span className="material-symbols-outlined text-xl">{item.icon}</span>
          <span className="text-[9px] uppercase tracking-wider font-medium">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
