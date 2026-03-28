export interface User {
  id: number;
  username: string;
  full_name: string;
  role: 'student' | 'admin';
  created_at?: string;
}

export interface TheoryRef {
  id: number;
  title: string;
}

export interface TaskCatalogItem {
  id: number;
  title: string;
  description: string;
  type: 'quiz' | 'ctf' | 'gitlab' | 'theory' | 'ssh_lab';
  order: number;
  difficulty: string | null;
  tags: string[];
  max_points: number | null;
}

export interface TaskDetail extends TaskCatalogItem {
  config: Record<string, any>;
  theory_refs: TheoryRef[];
}

export interface Submission {
  id: number;
  user_id: number;
  task_id: number;
  status: 'pending' | 'success' | 'fail';
  details: Record<string, any>;
  submitted_at: string;
}

export interface ContainerInfo {
  container_id: string;
  domain: string;
  expires_at: string;
  status: 'running' | 'stopped' | 'expired';
}

export interface QuizQuestion {
  id: number;
  text: string;
  options: string[];
}

export interface QuizResult {
  score: number;
  total: number;
  correct: number[];
  wrong: number[];
}

export interface CheckResultItem {
  name: string;
  passed: boolean;
  message: string;
}

export interface CheckResponse {
  all_passed: boolean;
  results: CheckResultItem[];
}

export interface GitLabTaskInfo {
  repo_url: string;
  username: string;
  password: string;
}

export interface SpecializationItem {
  name: string;
  pct: number;
}

export interface ActivityLogItem {
  date: string;
  task_title: string;
  points: number;
  status: string;
}

export interface ProgressData {
  completed_tasks: number;
  total_tasks: number;
  progress_pct: number;
  total_xp: number;
  rank: number;
  total_users: number;
  specializations: SpecializationItem[];
  activity_log: ActivityLogItem[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export type TaskStatuses = Record<number, string>;

export interface TrackStepItem {
  id: number;
  task_id: number;
  step_order: number;
  task_title: string;
  task_type: 'quiz' | 'ctf' | 'gitlab' | 'theory' | 'ssh_lab';
  task_difficulty: string | null;
  user_status: string | null;
}

export interface TrackItem {
  id: number;
  title: string;
  slug: string;
  description: string;
  order: number;
  config: Record<string, any>;
  step_count: number;
  completed_count: number;
}

export interface TrackDetail extends TrackItem {
  steps: TrackStepItem[];
}
