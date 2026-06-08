import { httpClient } from './client';
import type { TaskTemplate, TaskTemplateCreate, TaskTemplateUpdate, ApplyTemplateOptions, SaveAsTemplateRequest, Task } from './types';

export const templateApi = {
  async getAllTemplates(signal?: AbortSignal): Promise<TaskTemplate[]> {
    return httpClient.request<TaskTemplate[]>('/templates', {
      method: 'GET',
      signal,
    });
  },

  async getTemplate(id: number): Promise<TaskTemplate> {
    return httpClient.request<TaskTemplate>(`/templates/${id}`, {
      method: 'GET',
    });
  },

  async createTemplate(template: TaskTemplateCreate): Promise<TaskTemplate> {
    return httpClient.request<TaskTemplate>('/templates', {
      method: 'POST',
      body: JSON.stringify(template),
    });
  },

  async updateTemplate(id: number, template: TaskTemplateUpdate): Promise<TaskTemplate> {
    return httpClient.request<TaskTemplate>(`/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(template),
    });
  },

  async deleteTemplate(id: number): Promise<void> {
    return httpClient.request<void>(`/templates/${id}`, {
      method: 'DELETE',
    });
  },

  async applyTemplate(id: number, options?: ApplyTemplateOptions): Promise<Task> {
    return httpClient.request<Task>(`/templates/${id}/apply`, {
      method: 'POST',
      body: JSON.stringify(options || {}),
    });
  },

  async saveTaskAsTemplate(taskId: number, data: SaveAsTemplateRequest): Promise<TaskTemplate> {
    return httpClient.request<TaskTemplate>(`/tasks/${taskId}/save-as-template`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
