import { httpClient } from './client';
import type { AuthResponse } from './types';

export const authApi = {
  async login(username: string, password: string): Promise<AuthResponse> {
    return httpClient.request<AuthResponse>('/auth/login', {
      method: 'POST',
      requiresAuth: false,
      body: JSON.stringify({ username, password }),
    });
  },

  async register(username: string, password: string): Promise<AuthResponse> {
    return httpClient.request<AuthResponse>('/auth/register', {
      method: 'POST',
      requiresAuth: false,
      body: JSON.stringify({ username, password }),
    });
  },

  async verifyToken(): Promise<boolean> {
    const token = localStorage.getItem('token');
    if (!token) {
      return false;
    }
    try {
      const response = await httpClient.requestBlob('/tasks', {
        method: 'GET',
        requiresAuth: true,
      });
      if (response.status === 401) {
        return false;
      }
      return response.ok;
    } catch {
      return false;
    }
  },
};

export function clearAuth(): void {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.dispatchEvent(new CustomEvent('auth:logout'));
}

export function handleUnauthorized(): void {
  clearAuth();
  if (
    !window.location.pathname.startsWith('/login') &&
    !window.location.pathname.startsWith('/register')
  ) {
    window.location.href = '/login';
  }
}
