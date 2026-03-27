interface StatusBadgeProps {
  status: 'success' | 'fail' | 'pending' | 'available' | 'not_started';
  label?: string;
}

const config = {
  success: {
    bg: 'bg-primary/10',
    text: 'text-primary',
    label: 'Пройдено',
    icon: 'check_circle',
    showIcon: true,
  },
  fail: {
    bg: 'bg-tertiary/10',
    text: 'text-tertiary',
    label: 'Провалено',
    icon: 'cancel',
    showIcon: true,
  },
  pending: {
    bg: 'bg-secondary/10',
    text: 'text-secondary',
    label: 'В процессе',
    icon: 'pending',
    showIcon: false,
  },
  available: {
    bg: 'bg-outline-variant/10',
    text: 'text-on-surface-variant',
    label: 'Доступно',
    icon: '',
    showIcon: false,
  },
  not_started: {
    bg: 'bg-outline-variant/10',
    text: 'text-on-surface-variant',
    label: 'Доступно',
    icon: '',
    showIcon: false,
  },
};

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  const c = config[status] || config.available;
  return (
    <div className={`inline-flex items-center ${c.bg} px-2 py-1 rounded-sm`}>
      {c.showIcon && (
        <span
          className={`material-symbols-outlined text-xs ${c.text} mr-1`}
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          {c.icon}
        </span>
      )}
      <span className={`text-[9px] font-bold ${c.text} uppercase`}>{label || c.label}</span>
    </div>
  );
}
