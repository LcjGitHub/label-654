import { httpClient } from './client';
import type { Task, TaskCreate, TaskUpdate } from './types';

export const taskApi = {
  async getAllTasks(
    signal?: AbortSignal,
    categoryId: number | null = null,
    tagId: number | null = null,
    search: string | null = null,
  ): Promise<Task[]> {
    const params: Record<string, number | string | null> = {};
    if (categoryId !== null) {
      params.category_id = categoryId;
    }
    if (tagId !== null) {
      params.tag_id = tagId;
    }
    if (search !== null && search.trim() !== '') {
      params.search = search.trim();
    }
    return httpClient.request<Task[]>('/tasks', {
      method: 'GET',
      signal,
      params,
    });
  },

  async getTask(id: number): Promise<Task> {
    return httpClient.request<Task>(`/tasks/${id}`, {
      method: 'GET',
    });
  },

  async createTask(task: TaskCreate): Promise<Task> {
    return httpClient.request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify(task),
    });
  },

  async updateTask(id: number, task: TaskUpdate): Promise<Task> {
    return httpClient.request<Task>(`/tasks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(task),
    });
  },

  async toggleTask(id: number): Promise<Task> {
    return httpClient.request<Task>(`/tasks/${id}/toggle`, {
      method: 'PUT',
    });
  },

  async togglePinTask(id: number): Promise<Task> {
    return httpClient.request<Task>(`/tasks/${id}/pin`, {
      method: 'PUT',
    });
  },

  async deleteTask(id: number): Promise<void> {
    return httpClient.request<void>(`/tasks/${id}`, {
      method: 'DELETE',
    });
  },

  async checkRepeatTasks(): Promise<{ created: number }> {
    return httpClient.request<{ created: number }>('/tasks/check-repeat', {
      method: 'POST',
    });
  },
};
