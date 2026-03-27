const API_BASE = '/api';

function getToken(): string | null {
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

  // Tracks
  listTracks: () => request<any[]>('/tracks'),
  getTrack: (id: number) => request<any>(`/tracks/${id}`),

  listUsersPaginated: (params?: { page?: number; per_page?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.per_page) searchParams.set('per_page', String(params.per_page));
    const qs = searchParams.toString();
    return request<any>(`/admin/users${qs ? `?${qs}` : ''}`);
  },
};
