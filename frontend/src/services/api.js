const API_BASE_URL = 'http://localhost:5000/api';

function getToken() {
  return localStorage.getItem('token');
}

function getAuthHeaders() {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const authApi = {
  async login(username, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || '登录失败');
    }
    return response.json();
  },

  async register(username, password) {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || '注册失败');
    }
    return response.json();
  },
};

export const taskApi = {
  async getAllTasks(signal) {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      signal,
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('获取任务列表失败');
    return response.json();
  },

  async getTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('获取任务失败');
    return response.json();
  },

  async createTask(task) {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(task),
    });
    if (!response.ok) throw new Error('创建任务失败');
    return response.json();
  },

  async updateTask(id, task) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(task),
    });
    if (!response.ok) throw new Error('更新任务失败');
    return response.json();
  },

  async toggleTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}/toggle`, {
      method: 'PUT',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('切换任务状态失败');
    return response.json();
  },

  async deleteTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('删除任务失败');
    return response.json();
  },
};
