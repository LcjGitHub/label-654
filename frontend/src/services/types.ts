export interface User {
  id: number;
  username: string;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  completed: boolean;
  pinned: boolean;
  category_id: number | null;
  user_id: number;
  due_date: string | null;
  repeat: 'none' | 'daily' | 'weekly' | 'monthly';
  created_at: string;
  updated_at: string;
  category: Category | null;
  tags: Tag[];
  attachments: Attachment[];
}

export interface TaskCreate {
  title: string;
  description?: string | null;
  category_id?: number | null;
  due_date?: string | null;
  repeat?: 'none' | 'daily' | 'weekly' | 'monthly';
}

export interface TaskUpdate {
  title?: string;
  description?: string | null;
  completed?: boolean;
  pinned?: boolean;
  category_id?: number | null;
  due_date?: string | null;
  repeat?: 'none' | 'daily' | 'weekly' | 'monthly';
}

export interface Category {
  id: number;
  name: string;
  color: string;
  user_id: number;
  created_at: string;
}

export interface CategoryCreate {
  name: string;
  color?: string;
}

export interface CategoryUpdate {
  name?: string;
  color?: string;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
  user_id: number;
  created_at: string;
}

export interface TagCreate {
  name: string;
  color?: string;
}

export interface TagUpdate {
  name?: string;
  color?: string;
}

export interface Attachment {
  id: number;
  filename: string;
  original_filename: string;
  content_type: string;
  size: number;
  task_id: number;
  user_id: number;
  created_at: string;
}

export interface AttachmentBlobResult {
  blob: Blob;
  filename: string;
}

export interface Stats {
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  completion_rate: number;
  tasks_by_category: Array<{
    category_id: number | null;
    category_name: string | null;
    count: number;
  }>;
  tasks_by_tag: Array<{
    tag_id: number;
    tag_name: string;
    count: number;
  }>;
}

export interface GetAllTasksParams {
  categoryId?: number | null;
  tagId?: number | null;
  search?: string | null;
}

export interface ApiErrorResponse {
  error: string;
}

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

export interface RequestConfig {
  method: HttpMethod;
  headers?: Record<string, string>;
  body?: BodyInit | null;
  signal?: AbortSignal;
  requiresAuth?: boolean;
  includeContentType?: boolean;
  params?: Record<string, string | number | boolean | null | undefined>;
}
