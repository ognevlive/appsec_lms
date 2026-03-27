import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Icon from '../components/Icon';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  if (isAuthenticated) {
    navigate(user?.role === 'admin' ? '/admin' : '/challenges', { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      // AuthContext will update, causing redirect above
    } catch (err: any) {
      setError(err.message || 'Ошибка авторизации');
    }
    setLoading(false);
  };

  return (
    <div className="w-full max-w-md">
      <div className="bg-surface-container-low border border-outline-variant/10 p-10">
        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div className="w-16 h-16 bg-primary/10 flex items-center justify-center mb-4">
            <Icon name="shield" className="text-primary text-4xl" filled />
          </div>
          <h1 className="text-2xl font-headline font-bold text-primary tracking-tighter uppercase">
            LMS AppSec
          </h1>
          <p className="text-[10px] text-on-surface-variant uppercase tracking-[0.3em] mt-2">
            Платформа обучения безопасной разработке
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold ml-1">
              Логин
            </label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">
                person
              </span>
              <input
                className="w-full h-11 bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none transition-colors placeholder:text-outline-variant pl-10 pr-3"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="username"
                required
                autoFocus
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] uppercase tracking-wider text-on-surface-variant font-bold ml-1">
              Пароль
            </label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">
                lock
              </span>
              <input
                className="w-full h-11 bg-surface-container-lowest border border-outline-variant/30 text-sm text-on-surface focus:border-primary focus:ring-0 focus:outline-none transition-colors placeholder:text-outline-variant pl-10 pr-3"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
          </div>

          {error && (
            <div className="bg-error/10 border border-error/20 px-4 py-2 text-error text-xs">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full h-12 bg-gradient-to-br from-primary to-primary-dim text-on-primary font-bold text-xs uppercase tracking-widest transition-all hover:brightness-110 active:scale-95 disabled:opacity-50"
          >
            {loading ? 'Авторизация...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  );
}
