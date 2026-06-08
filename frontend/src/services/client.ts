import type { ApiErrorResponse, RequestConfig } from './types';

const API_BASE_URL = 'http://localhost:5000/api';

type RequestInterceptor = (config: RequestConfig) => RequestConfig | Promise<RequestConfig>;
type ResponseInterceptor = (response: Response) => Response | Promise<Response>;
type ErrorHandler = (error: unknown) => void;

class HttpClient {
  private baseURL: string;
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];
  private errorHandler: ErrorHandler | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  addResponseInterceptor(interceptor: ResponseInterceptor): void {
    this.responseInterceptors.push(interceptor);
  }

  setErrorHandler(handler: ErrorHandler): void {
    this.errorHandler = handler;
  }

  private buildUrl(path: string, params?: RequestConfig['params']): string {
    let url = `${this.baseURL}${path}`;
    if (params) {
      const queryParts: string[] = [];
      Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          queryParts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
        }
      });
      if (queryParts.length > 0) {
        url += `?${queryParts.join('&')}`;
      }
    }
    return url;
  }

  private async applyRequestInterceptors(config: RequestConfig): Promise<RequestConfig> {
    let result = config;
    for (const interceptor of this.requestInterceptors) {
      result = await interceptor(result);
    }
    return result;
  }

  private async applyResponseInterceptors(response: Response): Promise<Response> {
    let result = response;
    for (const interceptor of this.responseInterceptors) {
      result = await interceptor(result);
    }
    return result;
  }

  private async parseErrorResponse(response: Response): Promise<string> {
    try {
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const error = (await response.json()) as ApiErrorResponse;
        if (error && typeof error === 'object' && error.error) {
          return error.error;
        }
      }
    } catch {
    }
    return '请求失败，请稍后重试';
  }

  async request<T>(path: string, config: RequestConfig = { method: 'GET' }): Promise<T> {
    try {
      const processedConfig = await this.applyRequestInterceptors(config);
      const url = this.buildUrl(path, processedConfig.params);

      const fetchConfig: RequestInit = {
        method: processedConfig.method,
        headers: processedConfig.headers,
        body: processedConfig.body,
        signal: processedConfig.signal,
      };

      const response = await fetch(url, fetchConfig);
      const processedResponse = await this.applyResponseInterceptors(response);

      if (!processedResponse.ok) {
        const errorMsg = await this.parseErrorResponse(processedResponse);
        throw new Error(errorMsg);
      }

      try {
        return (await processedResponse.json()) as T;
      } catch {
        throw new Error('响应数据解析失败，请稍后重试');
      }
    } catch (error) {
      if (this.errorHandler) {
        this.errorHandler(error);
      }
      throw error;
    }
  }

  async requestBlob(path: string, config: RequestConfig = { method: 'GET' }): Promise<Response> {
    const processedConfig = await this.applyRequestInterceptors(config);
    const url = this.buildUrl(path, processedConfig.params);

    const fetchConfig: RequestInit = {
      method: processedConfig.method,
      headers: processedConfig.headers,
      body: processedConfig.body,
      signal: processedConfig.signal,
    };

    const response = await fetch(url, fetchConfig);
    return this.applyResponseInterceptors(response);
  }
}

export const httpClient = new HttpClient(API_BASE_URL);

httpClient.addRequestInterceptor((config) => {
  const requiresAuth = config.requiresAuth !== false;
  const includeContentType = config.includeContentType !== false;

  const token = localStorage.getItem('token');
  const headers: Record<string, string> = { ...(config.headers || {}) };

  if (includeContentType && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  if (requiresAuth && token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return { ...config, headers };
});

httpClient.addResponseInterceptor(async (response) => {
  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.dispatchEvent(new CustomEvent('auth:logout'));

    if (
      !window.location.pathname.startsWith('/login') &&
      !window.location.pathname.startsWith('/register')
    ) {
      window.location.href = '/login';
    }
  }
  return response;
});

httpClient.setErrorHandler((error) => {
  if (error instanceof Error) {
    console.error('[HTTP Error]:', error.message);
  }
});

export { API_BASE_URL };
