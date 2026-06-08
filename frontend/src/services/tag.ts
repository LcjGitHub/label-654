import { httpClient } from './client';
import type { Tag, TagCreate, TagUpdate } from './types';

export const tagApi = {
  async getAllTags(signal?: AbortSignal): Promise<Tag[]> {
    return httpClient.request<Tag[]>('/tags', {
      method: 'GET',
      signal,
    });
  },

  async getTag(id: number): Promise<Tag> {
    return httpClient.request<Tag>(`/tags/${id}`, {
      method: 'GET',
    });
  },

  async createTag(tag: TagCreate): Promise<Tag> {
    return httpClient.request<Tag>('/tags', {
      method: 'POST',
      body: JSON.stringify(tag),
    });
  },

  async updateTag(id: number, tag: TagUpdate): Promise<Tag> {
    return httpClient.request<Tag>(`/tags/${id}`, {
      method: 'PUT',
      body: JSON.stringify(tag),
    });
  },

  async deleteTag(id: number): Promise<void> {
    return httpClient.request<void>(`/tags/${id}`, {
      method: 'DELETE',
    });
  },

  async addTagToTask(taskId: number, tagId: number): Promise<Tag> {
    return httpClient.request<Tag>(`/tasks/${taskId}/tags`, {
      method: 'POST',
      body: JSON.stringify({ tag_id: tagId }),
    });
  },

  async removeTagFromTask(taskId: number, tagId: number): Promise<void> {
    return httpClient.request<void>(`/tasks/${taskId}/tags/${tagId}`, {
      method: 'DELETE',
    });
  },
};
