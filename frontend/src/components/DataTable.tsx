import type { ReactNode } from 'react';

interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string | number;
}

export default function DataTable<T>({ columns, data, keyExtractor }: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-surface-container-highest">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-4 py-3 ${col.className || ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item, idx) => (
            <tr
              key={keyExtractor(item)}
              className={`${
                idx % 2 === 0 ? 'bg-[#1a1b26]' : 'bg-[#15161e]'
              } hover:bg-surface-bright transition-colors`}
            >
              {columns.map((col) => (
                <td key={col.key} className={`px-4 py-3 text-sm ${col.className || ''}`}>
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length === 0 && (
        <div className="text-center py-12 text-on-surface-variant text-sm">
          Нет данных
        </div>
      )}
    </div>
  );
}
