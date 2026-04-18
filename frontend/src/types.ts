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

export type TaskKind = 'quiz' | 'ctf' | 'gitlab' | 'theory' | 'ssh_lab';

export interface UnitItem {
  id: number;
  task_id: number;
  task_slug: string;
  task_title: string;
  task_type: TaskKind;
  task_difficulty: string | null;
  content_kind: 'text' | 'video' | 'mixed' | null;
  unit_order: number;
  is_required: boolean;
  user_status: 'success' | 'fail' | 'pending' | null;
}

export interface ModuleItem {
  id: number;
  title: string;
  description: string;
  order: number;
  estimated_hours: number | null;
  learning_outcomes: string[];
  config: Record<string, any>;
  is_locked: boolean;
  unit_count: number;
  completed_unit_count: number;
  units: UnitItem[];
}

export interface CourseItem {
  id: number;
  slug: string;
  title: string;
  description: string;
  order: number;
  config: Record<string, any>;
  module_count: number;
  unit_count: number;
  completed_unit_count: number;
  progress_pct: number;
}

export interface CourseDetail extends CourseItem {
  modules: ModuleItem[];
}

export type TaskType = 'quiz' | 'ctf' | 'gitlab' | 'theory' | 'ssh_lab';

export interface AdminTask {
  id: number;
  slug: string;
  title: string;
  description: string;
  type: TaskType;
  order: number;
  config: Record<string, any>;
  author_id: number | null;
  updated_at: string;
  usage?: { course_id: number; course_slug: string; module_id: number; unit_id: number }[];
}

export interface AdminCourse {
  id: number;
  slug: string;
  title: string;
  description: string;
  order: number;
  config: Record<string, any>;
  is_visible: boolean;
}

export interface AdminModule {
  id: number;
  course_id: number;
  title: string;
  description: string;
  order: number;
  estimated_hours: number | null;
  learning_outcomes: string[];
  config: Record<string, any>;
}

export interface AdminUnit {
  id: number;
  module_id: number;
  task_id: number;
  unit_order: number;
  is_required: boolean;
}
