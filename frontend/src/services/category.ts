import { httpClient } from './client';
import type { Category, CategoryCreate, CategoryUpdate } from './types';

export const categoryApi = {
  async getAllCategories(signal?: AbortSignal): Promise<Category[]> {
    return httpClient.request<Category[]>('/categories', {
      method: 'GET',
      signal,
    });
  },

  async getCategory(id: number): Promise<Category> {
    return httpClient.request<Category>(`/categories/${id}`, {
      method: 'GET',
    });
  },

  async createCategory(category: CategoryCreate): Promise<Category> {
    return httpClient.request<Category>('/categories', {
      method: 'POST',
      body: JSON.stringify(category),
    });
  },

  async updateCategory(id: number, category: CategoryUpdate): Promise<Category> {
    return httpClient.request<Category>(`/categories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(category),
    });
  },

  async deleteCategory(id: number): Promise<void> {
    return httpClient.request<void>(`/categories/${id}`, {
      method: 'DELETE',
    });
  },
};
