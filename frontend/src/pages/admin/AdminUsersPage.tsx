import { useEffect, useState } from 'react';
import { api } from '../../api';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import FormSelect from '../../components/FormSelect';
import Pagination from '../../components/Pagination';
import Icon from '../../components/Icon';
import type { User } from '../../types';

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const perPage = 20;

  // Form state
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('student');
  const [formError, setFormError] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchUsers = async () => {
    try {
      const res = await api.listUsersPaginated({ page, per_page: perPage });
      if (res.items) {
        setUsers(res.items);
        setTotal(res.total);
      } else {
        // Fallback if backend returns plain array
        setUsers(Array.isArray(res) ? res : []);
        setTotal(Array.isArray(res) ? res.length : 0);
      }
    } catch {
      setUsers([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchUsers();
  }, [page]);

  const createUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setCreating(true);
    try {
      await api.createUser({ username, password, full_name: fullName, role });
      setUsername('');
      setPassword('');
      setFullName('');
      setRole('student');
      fetchUsers();
    } catch (err: any) {
      setFormError(err.message);
    }
    setCreating(false);
  };

  const deleteUser = async (userId: number) => {
    if (!confirm('Удалить пользователя?')) return;
    try {
      await api.deleteUser(userId);
      fetchUsers();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-10 flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-headline font-bold text-on-surface uppercase tracking-tight leading-none mb-2">
            99% <span className="text-primary">SECURE</span>
          </h1>
          <p className="text-on-surface-variant font-label text-xs uppercase tracking-[0.2em]">
            Управление доступом персонала
          </p>
        </div>
      </header>

      {/* Create User Form */}
      <section className="bg-surface-container-low mb-8 p-1">
        <form onSubmit={createUser} className="bg-surface-container border-l-2 border-primary p-6">
          <h2 className="text-xs font-bold text-primary uppercase tracking-widest mb-6 flex items-center gap-2">
            <Icon name="person_add" size="sm" />
            Регистрация нового субъекта
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <FormInput
              label="Логин"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="user_delta_9"
              required
            />
            <FormInput
              label="Пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
            <FormInput
              label="ФИО"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Иванов И.И."
            />
            <FormSelect
              label="Роль"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              options={[
                { value: 'student', label: 'Студент' },
                { value: 'admin', label: 'Админ' },
              ]}
            />
            <div className="flex items-end">
              <Button type="submit" disabled={creating} className="w-full h-10">
                {creating ? '...' : 'Создать'}
              </Button>
            </div>
          </div>
          {formError && (
            <div className="mt-3 text-error text-xs">{formError}</div>
          )}
        </form>
      </section>

      {/* Users Table */}
      <section className="bg-surface-container overflow-hidden border border-outline-variant/5">
        {loading ? (
          <div className="py-12 text-center text-primary animate-pulse">Загрузка...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface-container-highest">
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">ID</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Логин</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">ФИО</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Роль</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Дата создания</th>
                  <th className="text-left text-[10px] uppercase tracking-widest font-bold text-on-surface-variant px-6 py-4">Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u, idx) => (
                  <tr
                    key={u.id}
                    className={`${idx % 2 === 0 ? 'bg-[#1a1b26]' : 'bg-[#15161e]'} hover:bg-surface-bright transition-colors`}
                  >
                    <td className="px-6 py-3 text-xs font-mono text-on-surface-variant">{u.id}</td>
                    <td className="px-6 py-3 text-sm font-medium">{u.username}</td>
                    <td className="px-6 py-3 text-sm text-on-surface-variant">{u.full_name || '—'}</td>
                    <td className="px-6 py-3">
                      <span
                        className={`text-[9px] font-bold uppercase px-2 py-1 ${
                          u.role === 'admin'
                            ? 'bg-tertiary/10 text-tertiary'
                            : 'bg-secondary/10 text-secondary'
                        }`}
                      >
                        {u.role === 'admin' ? 'Админ' : 'Студент'}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-xs font-mono text-on-surface-variant">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString('ru-RU') : '—'}
                    </td>
                    <td className="px-6 py-3">
                      <button
                        onClick={() => deleteUser(u.id)}
                        className="text-on-surface-variant hover:text-error transition-colors"
                      >
                        <Icon name="delete" size="sm" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Summary */}
      <div className="flex items-center gap-6 mt-4 text-xs text-on-surface-variant">
        <span>Всего: <strong className="text-on-surface">{total}</strong></span>
        <span>Админов: <strong className="text-tertiary">{users.filter((u) => u.role === 'admin').length}</strong></span>
      </div>

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}
