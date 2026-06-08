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

function getAuthHeadersWithoutContentType() {
  const token = getToken();
  const headers = {};
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
  async getAllTasks(signal, categoryId = null, tagId = null, search = null) {
    let url = `${API_BASE_URL}/tasks`;
    const params = [];
    if (categoryId !== null) {
      params.push(`category_id=${encodeURIComponent(categoryId)}`);
    }
    if (tagId !== null) {
      params.push(`tag_id=${encodeURIComponent(tagId)}`);
    }
    if (search !== null && search.trim() !== '') {
      params.push(`search=${encodeURIComponent(search.trim())}`);
    }
    if (params.length > 0) {
      url += '?' + params.join('&');
    }
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

  async togglePinTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}/pin`, {
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

  async checkRepeatTasks() {
    const response = await fetch(`${API_BASE_URL}/tasks/check-repeat`, {
      method: 'POST',
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

export const tagApi = {
  async getAllTags(signal) {
    const response = await fetch(`${API_BASE_URL}/tags`, {
      signal,
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getTag(id) {
    const response = await fetch(`${API_BASE_URL}/tags/${id}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async createTag(tag) {
    const response = await fetch(`${API_BASE_URL}/tags`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(tag),
    });
    return handleResponse(response);
  },

  async updateTag(id, tag) {
    const response = await fetch(`${API_BASE_URL}/tags/${id}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(tag),
    });
    return handleResponse(response);
  },

  async deleteTag(id) {
    const response = await fetch(`${API_BASE_URL}/tags/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async addTagToTask(taskId, tagId) {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/tags`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ tag_id: tagId }),
    });
    return handleResponse(response);
  },

  async removeTagFromTask(taskId, tagId) {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/tags/${tagId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

export const attachmentApi = {
  async uploadAttachment(taskId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/attachments`, {
      method: 'POST',
      headers: getAuthHeadersWithoutContentType(),
      body: formData,
    });
    return handleResponse(response);
  },

  getAttachmentUrl(attachmentId) {
    const token = getToken();
    const url = `${API_BASE_URL}/tasks/attachments/${attachmentId}`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  getAttachmentDownloadUrl(attachmentId) {
    const token = getToken();
    const url = `${API_BASE_URL}/tasks/attachments/${attachmentId}/download`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  async getAttachmentBlob(attachmentId) {
    const response = await fetch(this.getAttachmentUrl(attachmentId));
    if (response.status === 401) {
      handleUnauthorized();
      throw new Error('未授权，请重新登录');
    }
    if (!response.ok) {
      try {
        const err = await response.json();
        throw new Error(err.error || '获取文件失败');
      } catch (e) {
        if (e.message === 'Failed to fetch' || e instanceof SyntaxError) {
          throw new Error('获取文件失败');
        }
        throw e;
      }
    }
    const blob = await response.blob();
    const contentDisposition = response.headers.get('Content-Disposition') || '';
    let filename = `attachment-${attachmentId}`;
    const match = contentDisposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    if (match) {
      filename = decodeURIComponent(match[1].replace(/"/g, ''));
    }
    return { blob, filename };
  },

  async previewAttachment(attachmentId) {
    const { blob } = await this.getAttachmentBlob(attachmentId);
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  },

  async downloadAttachment(attachmentId) {
    const { blob, filename } = await this.getAttachmentBlob(attachmentId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },

  async deleteAttachment(attachmentId) {
    const response = await fetch(`${API_BASE_URL}/tasks/attachments/${attachmentId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

export { clearAuth, handleUnauthorized };
