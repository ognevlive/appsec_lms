import { Link } from 'react-router-dom';
import Icon from './Icon';

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export default function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav className="flex items-center gap-2 mb-6">
      {items.map((item, idx) => (
        <span key={idx} className="flex items-center gap-2">
          {idx > 0 && <Icon name="chevron_right" size="sm" className="text-outline-variant" />}
          {item.to ? (
            <Link
              to={item.to}
              className="text-[10px] uppercase tracking-widest text-on-surface-variant hover:text-primary transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-[10px] uppercase tracking-widest text-on-surface">
              {item.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
