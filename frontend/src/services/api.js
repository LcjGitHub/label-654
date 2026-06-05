const API_BASE_URL = 'http://localhost:5000/api';

export const taskApi = {
  async getAllTasks() {
    const response = await fetch(`${API_BASE_URL}/tasks`);
    if (!response.ok) throw new Error('获取任务列表失败');
    return response.json();
  },

  async getTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`);
    if (!response.ok) throw new Error('获取任务失败');
    return response.json();
  },

  async createTask(task) {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(task),
    });
    if (!response.ok) throw new Error('创建任务失败');
    return response.json();
  },

  async updateTask(id, task) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(task),
    });
    if (!response.ok) throw new Error('更新任务失败');
    return response.json();
  },

  async toggleTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}/toggle`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) throw new Error('切换任务状态失败');
    return response.json();
  },

  async deleteTask(id) {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('删除任务失败');
    return response.json();
  },
};
