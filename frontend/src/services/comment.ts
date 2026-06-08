import { httpClient } from './client';
import type { TaskComment, TaskCommentCreate, TaskCommentUpdate, User } from './types';

export const commentApi = {
  async getTaskComments(taskId: number): Promise<TaskComment[]> {
    return httpClient.request<TaskComment[]>(`/tasks/${taskId}/comments`, {
      method: 'GET',
    });
  },

  async createTaskComment(taskId: number, data: TaskCommentCreate): Promise<TaskComment> {
    return httpClient.request<TaskComment>(`/tasks/${taskId}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateComment(commentId: number, data: TaskCommentUpdate): Promise<TaskComment> {
    return httpClient.request<TaskComment>(`/comments/${commentId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async deleteComment(commentId: number): Promise<void> {
    return httpClient.request<void>(`/comments/${commentId}`, {
      method: 'DELETE',
    });
  },

  async likeComment(commentId: number): Promise<{ like_count: number; is_liked: boolean }> {
    return httpClient.request<{ like_count: number; is_liked: boolean }>(
      `/comments/${commentId}/like`,
      {
        method: 'POST',
      },
    );
  },

  async unlikeComment(commentId: number): Promise<{ like_count: number; is_liked: boolean }> {
    return httpClient.request<{ like_count: number; is_liked: boolean }>(
      `/comments/${commentId}/like`,
      {
        method: 'DELETE',
      },
    );
  },

  async getMentionUsers(taskId: number): Promise<User[]> {
    return httpClient.request<User[]>(`/tasks/${taskId}/mention-users`, {
      method: 'GET',
    });
  },
};
