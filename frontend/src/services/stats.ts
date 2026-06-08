import { httpClient } from './client';
import type { Stats } from './types';

export const statsApi = {
  async getStats(signal?: AbortSignal): Promise<Stats> {
    return httpClient.request<Stats>('/stats', {
      method: 'GET',
      signal,
    });
  },
};
