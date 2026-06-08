export interface User {
  id: number;
  username: string;
  created_at: string;
}

export interface Team {
  id: number;
  name: string;
  description: string | null;
  created_by: number;
  invite_token: string;
  created_at: string;
  member_count: number;
}

export interface TeamMember {
  id: number;
  team_id: number;
  user_id: number;
  username: string;
  role: 'admin' | 'member';
  joined_at: string;
}

export interface TeamUser {
  id: number;
  username: string;
  created_at: string;
  role: 'admin' | 'member';
}

export interface TaskShare {
  id: number;
  task_id: number;
  team_id: number | null;
  shared_with_user_id: number | null;
  shared_with_username?: string;
  team_name?: string;
  can_edit: boolean;
  created_at: string;
}

export interface TeamCreate {
  name: string;
  description?: string;
}

export interface TeamUpdate {
  name?: string;
  description?: string;
}

export interface InvitationCreate {
  email: string;
}

export interface InvitationInfo {
  team_id: number;
  team_name: string;
  email: string;
  expires_at: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface Task {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  completed: boolean;
  pinned: boolean;
  category_id: number | null;
  assignee_id: number | null;
  assignee?: User;
  creator?: User;
  due_date: string | null;
  repeat: 'none' | 'daily' | 'weekly' | 'monthly';
  created_at: string;
  updated_at: string;
  category: Category | null;
  tags: Tag[];
  attachments: Attachment[];
  is_pinned?: boolean;
  priority?: string;
  repeat_pattern?: string;
  repeat_parent_id?: number | null;
}

export interface TaskCreate {
  title: string;
  description?: string | null;
  category_id?: number | null;
  due_date?: string | null;
  repeat?: 'none' | 'daily' | 'weekly' | 'monthly';
  assignee_id?: number | null;
  share_team_id?: number | null;
  share_with_user_ids?: number[];
  share_can_edit?: boolean;
  priority?: string;
  is_pinned?: boolean;
  repeat_pattern?: string;
  tag_ids?: number[];
}

export interface TaskUpdate {
  title?: string;
  description?: string | null;
  completed?: boolean;
  pinned?: boolean;
  category_id?: number | null;
  due_date?: string | null;
  repeat?: 'none' | 'daily' | 'weekly' | 'monthly';
  assignee_id?: number | null;
  priority?: string;
  is_pinned?: boolean;
  repeat_pattern?: string;
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
