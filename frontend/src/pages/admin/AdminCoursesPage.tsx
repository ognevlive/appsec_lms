import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api } from '../../api';
import Button from '../../components/Button';
import FormInput from '../../components/FormInput';
import type { AdminCourse } from '../../types';

export default function AdminCoursesPage() {
  const nav = useNavigate();
  const [courses, setCourses] = useState<AdminCourse[]>([]);
  const [creating, setCreating] = useState(false);
  const [newCourse, setNewCourse] = useState({ title: '', slug: '' });
  const [error, setError] = useState('');

  const load = () =>
    api.adminContent
      .listCourses()
      .then(setCourses)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  const toggleVisible = async (c: AdminCourse) => {
    try {
      await api.adminContent.patchCourse(c.id, { is_visible: !c.is_visible });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const onCreate = async () => {
    try {
      const c = await api.adminContent.createCourse(newCourse);
      nav(`/admin/courses/${c.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const onImport = async (file: File) => {
    try {
      await api.adminContent.importCourse(file, true);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold">Курсы</h2>
        <div className="flex-1" />
        <Button onClick={() => setCreating(true)}>Новый курс</Button>
        <label>
          <input
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onImport(e.target.files[0])}
          />
          <span className="px-3 py-2 bg-surface-container-low cursor-pointer">Импорт</span>
        </label>
      </div>

      {error && <div className="text-error">{error}</div>}

      {creating && (
        <div className="border p-4 flex gap-3 items-end">
          <FormInput
            label="Title"
            value={newCourse.title}
            onChange={(e) => setNewCourse({ ...newCourse, title: e.target.value })}
          />
          <FormInput
            label="Slug"
            value={newCourse.slug}
            onChange={(e) => setNewCourse({ ...newCourse, slug: e.target.value })}
          />
          <Button onClick={onCreate}>Создать</Button>
          <Button onClick={() => setCreating(false)} variant="secondary">
            Отмена
          </Button>
        </div>
      )}

      <table className="w-full">
        <thead>
          <tr>
            <th className="text-left">Title</th>
            <th>Slug</th>
            <th>Order</th>
            <th>Visible</th>
          </tr>
        </thead>
        <tbody>
          {courses.map((c) => (
            <tr key={c.id} className="hover:bg-surface-container-low">
              <td>
                <Link to={`/admin/courses/${c.id}`}>{c.title}</Link>
              </td>
              <td className="font-mono text-sm">{c.slug}</td>
              <td>{c.order}</td>
              <td>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={c.is_visible}
                    onChange={() => toggleVisible(c)}
                  />
                  {c.is_visible ? 'Visible' : 'Hidden'}
                </label>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
