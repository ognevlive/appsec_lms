import type { AdminCourse, AdminModule, AdminTask, AdminUnit } from './types';

const API_BASE = '/api';

export function getToken(): string | null {
  return localStorage.getItem('token');
}

export function setToken(token: string) {
  localStorage.setItem('token', token);
}

export function clearToken() {
  localStorage.removeItem('token');
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401) {
    clearToken();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${resp.status}`);
  }

  if (resp.status === 204) return undefined as T;
  return resp.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  me: () => request<{ id: number; username: string; full_name: string; role: string }>('/auth/me'),

  // Tasks
  listTasks: () => request<any[]>('/tasks'),
  getTask: (id: number) => request<any>(`/tasks/${id}`),
  mySubmissions: (taskId: number) => request<any[]>(`/tasks/${taskId}/submissions`),

  // Quiz
  getQuestions: (taskId: number) => request<any[]>(`/quiz/${taskId}/questions`),
  submitQuiz: (taskId: number, answers: Record<string, string>) =>
    request<any>(`/quiz/${taskId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),

  // CTF
  startCtf: (taskId: number) =>
    request<any>(`/ctf/${taskId}/start`, { method: 'POST' }),
  stopCtf: (taskId: number) =>
    request<any>(`/ctf/${taskId}/stop`, { method: 'POST' }),
  ctfStatus: (taskId: number) => request<any | null>(`/ctf/${taskId}/status`),
  submitFlag: (taskId: number, flag: string) =>
    request<any>(`/ctf/${taskId}/flag`, {
      method: 'POST',
      body: JSON.stringify({ flag }),
    }),
  checkContainer: (taskId: number) =>
    request<any>(`/ctf/${taskId}/check`, { method: 'POST' }),

  // GitLab
  startGitlab: (taskId: number) =>
    request<any>(`/gitlab/${taskId}/start`, { method: 'POST' }),

  // Admin
  listUsers: () => request<any[]>('/admin/users'),
  createUser: (data: { username: string; password: string; full_name: string; role: string }) =>
    request<any>('/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteUser: (id: number) =>
    request<void>(`/admin/users/${id}`, { method: 'DELETE' }),
  listSubmissions: (params?: { task_id?: number; user_id?: number; status?: string; page?: number; per_page?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.task_id) searchParams.set('task_id', String(params.task_id));
    if (params?.user_id) searchParams.set('user_id', String(params.user_id));
    if (params?.status) searchParams.set('status', params.status);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.per_page) searchParams.set('per_page', String(params.per_page));
    const qs = searchParams.toString();
    return request<any>(`/admin/submissions${qs ? `?${qs}` : ''}`);
  },
  listContainers: () => request<any[]>('/admin/containers'),

  getTaskStatuses: () => request<Record<number, string>>('/tasks/my-statuses'),

  getProgress: () => request<any>('/me/progress'),

  // Courses
  listCourses: () => request<import('./types').CourseItem[]>('/courses'),
  getCourse: (slugOrId: string | number) =>
    request<import('./types').CourseDetail>(`/courses/${slugOrId}`),
  getModule: (id: number) =>
    request<import('./types').ModuleItem>(`/modules/${id}`),

  markViewed: (taskId: number) =>
    request<{ ok: boolean }>('/me/progress/viewed', {
      method: 'POST',
      body: JSON.stringify({ task_id: taskId }),
    }),

  listUsersPaginated: (params?: { page?: number; per_page?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.per_page) searchParams.set('per_page', String(params.per_page));
    const qs = searchParams.toString();
    return request<any>(`/admin/users${qs ? `?${qs}` : ''}`);
  },

  adminContent: {
    listCourses: () => request<AdminCourse[]>('/admin/content/courses'),
    createCourse: (body: Partial<AdminCourse>) =>
      request<AdminCourse>('/admin/content/courses',
        { method: 'POST', body: JSON.stringify(body) }),
    patchCourse: (id: number, body: Partial<AdminCourse>) =>
      request<AdminCourse>(`/admin/content/courses/${id}`,
        { method: 'PATCH', body: JSON.stringify(body) }),
    deleteCourse: (id: number) =>
      request<void>(`/admin/content/courses/${id}`, { method: 'DELETE' }),
    reorderModules: (course_id: number, items: {id: number; order: number}[]) =>
      request<{ok: true}>(`/admin/content/courses/${course_id}/reorder-modules`,
        { method: 'POST', body: JSON.stringify(items) }),

    createModule: (course_id: number, body: Partial<AdminModule>) =>
      request<AdminModule>(`/admin/content/courses/${course_id}/modules`,
        { method: 'POST', body: JSON.stringify(body) }),
    patchModule: (id: number, body: Partial<AdminModule>) =>
      request<AdminModule>(`/admin/content/modules/${id}`,
        { method: 'PATCH', body: JSON.stringify(body) }),
    deleteModule: (id: number) =>
      request<void>(`/admin/content/modules/${id}`, { method: 'DELETE' }),
    reorderUnits: (module_id: number, items: {id: number; order: number}[]) =>
      request<{ok: true}>(`/admin/content/modules/${module_id}/reorder-units`,
        { method: 'POST', body: JSON.stringify(items) }),

    createUnit: (module_id: number, body: Partial<AdminUnit>) =>
      request<AdminUnit>(`/admin/content/modules/${module_id}/units`,
        { method: 'POST', body: JSON.stringify(body) }),
    patchUnit: (id: number, body: Partial<AdminUnit>) =>
      request<AdminUnit>(`/admin/content/units/${id}`,
        { method: 'PATCH', body: JSON.stringify(body) }),
    deleteUnit: (id: number) =>
      request<void>(`/admin/content/units/${id}`, { method: 'DELETE' }),

    listTasks: (params: {type?: string; search?: string; unused?: boolean} = {}) => {
      const qs = new URLSearchParams();
      if (params.type) qs.set('type', params.type);
      if (params.search) qs.set('search', params.search);
      if (params.unused) qs.set('unused', 'true');
      const q = qs.toString();
      return request<AdminTask[]>(`/admin/content/tasks${q ? '?' + q : ''}`);
    },
    getTask: (id: number) => request<AdminTask>(`/admin/content/tasks/${id}`),
    createTask: (body: Partial<AdminTask>) =>
      request<AdminTask>('/admin/content/tasks',
        { method: 'POST', body: JSON.stringify(body) }),
    patchTask: (id: number, body: Partial<AdminTask>) =>
      request<AdminTask>(`/admin/content/tasks/${id}`,
        { method: 'PATCH', body: JSON.stringify(body) }),
    deleteTask: (id: number) =>
      request<void>(`/admin/content/tasks/${id}`, { method: 'DELETE' }),

    exportTask: (id: number) =>
      fetch(`${API_BASE}/admin/content/tasks/${id}/export`,
        { headers: { Authorization: `Bearer ${getToken()}` } }).then(r => r.blob()),
    exportCourse: (id: number, bundle: boolean) =>
      fetch(`${API_BASE}/admin/content/courses/${id}/export?bundle=${bundle}`,
        { headers: { Authorization: `Bearer ${getToken()}` } }).then(r => r.blob()),
    importTask: (file: File) => {
      const fd = new FormData();
      fd.append('file', file);
      return fetch(`${API_BASE}/admin/content/tasks/import`,
        { method: 'POST', body: fd,
          headers: { Authorization: `Bearer ${getToken()}` } })
        .then(r => r.json());
    },
    importCourse: (file: File, importTasks: boolean) => {
      const fd = new FormData();
      fd.append('file', file);
      return fetch(`${API_BASE}/admin/content/courses/import?import_tasks=${importTasks}`,
        { method: 'POST', body: fd,
          headers: { Authorization: `Bearer ${getToken()}` } })
        .then(r => r.json());
    },
  },
};
