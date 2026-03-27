import Icon from './Icon';

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-4 mt-8">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="w-10 h-10 flex items-center justify-center bg-surface-container-high border border-outline-variant/20 text-on-surface-variant hover:bg-surface-bright hover:text-on-surface disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <Icon name="chevron_left" size="sm" />
      </button>
      <span className="text-xs font-mono text-on-surface-variant uppercase tracking-wider">
        {page} / {totalPages}
      </span>
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="w-10 h-10 flex items-center justify-center bg-surface-container-high border border-outline-variant/20 text-on-surface-variant hover:bg-surface-bright hover:text-on-surface disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <Icon name="chevron_right" size="sm" />
      </button>
    </div>
  );
}
