const API_BASE_URL = 'http://localhost:5000/api';

function getToken() {
  return localStorage.getItem('token');
}

function clearAuth() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.dispatchEvent(new CustomEvent('auth:logout'));
}

function handleUnauthorized() {
  clearAuth();
  if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
    window.location.href = '/login';
  }
}

async function handleResponse(response) {
  if (response.status === 401) {
    handleUnauthorized();
    const error = await response.json();
    throw new Error(error.error || '未授权，请重新登录');
  }
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || '请求失败');
  }
  return response.json();
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

  async verifyToken() {
    const token = getToken();
    if (!token) {
      return false;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'GET',
        headers: getAuthHeaders(),
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

export const taskApi = {
  async getAllTasks(signal, categoryId = null) {
    const url = categoryId 
      ? `${API_BASE_URL}/tasks?category_id=${categoryId}` 
      : `${API_BASE_URL}/tasks`;
    const response = await fetch(url, {
      signal,
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async createTask(task) {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(task),
    });
    return handleResponse(response);
  },

  async updateTask(id, task) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(task),
    });
    return handleResponse(response);
  },

  async toggleTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}/toggle`, {
      method: 'PUT',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async deleteTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

export const categoryApi = {
  async getAllCategories(signal) {
    const response = await fetch(`${API_BASE_URL}/categories`, {
      signal,
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getCategory(id) {
    const response = await fetch(`${API_BASE_URL}/categories/${id}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async createCategory(category) {
    const response = await fetch(`${API_BASE_URL}/categories`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(category),
    });
    return handleResponse(response);
  },

  async updateCategory(id, category) {
    const response = await fetch(`${API_BASE_URL}/categories/${id}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(category),
    });
    return handleResponse(response);
  },

  async deleteCategory(id) {
    const response = await fetch(`${API_BASE_URL}/categories/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

export { clearAuth, handleUnauthorized };
