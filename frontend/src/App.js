import React, { useState, useEffect } from 'react';
import { taskApi } from './services/api';
import AddTask from './components/AddTask';
import TaskList from './components/TaskList';
import './App.css';

function App() {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await taskApi.getAllTasks();
      setTasks(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTask = async (task) => {
    try {
      setError(null);
      const newTask = await taskApi.createTask(task);
      setTasks(prevTasks => [newTask, ...prevTasks]);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleTask = async (id) => {
    try {
      setError(null);
      const updatedTask = await taskApi.toggleTask(id);
      setTasks(prevTasks => prevTasks.map((task) => (task.id === id ? updatedTask : task)));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteTask = async (id) => {
    try {
      setError(null);
      await taskApi.deleteTask(id);
      setTasks(prevTasks => prevTasks.filter((task) => task.id !== id));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdateTask = async (id, taskData) => {
    try {
      setError(null);
      const updatedTask = await taskApi.updateTask(id, taskData);
      setTasks(prevTasks => prevTasks.map((task) => (task.id === id ? updatedTask : task)));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleClearCompleted = async () => {
    try {
      setError(null);
      const completedTasks = tasks.filter((task) => task.completed);
      for (const task of completedTasks) {
        await taskApi.deleteTask(task.id);
      }
      setTasks(tasks.filter((task) => !task.completed));
    } catch (err) {
      setError(err.message);
    }
  };

  const activeCount = tasks.filter((task) => !task.completed).length;
  const completedCount = tasks.filter((task) => task.completed).length;

  return (
    <div className="app">
      <div className="container">
        <header className="app-header">
          <h1>📝 待办事项</h1>
          <p className="subtitle">高效管理你的日常任务</p>
        </header>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        <AddTask onAdd={handleAddTask} />

        <div className="filter-tabs">
          <button
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            全部 ({tasks.length})
          </button>
          <button
            className={`filter-btn ${filter === 'active' ? 'active' : ''}`}
            onClick={() => setFilter('active')}
          >
            待完成 ({activeCount})
          </button>
          <button
            className={`filter-btn ${filter === 'completed' ? 'active' : ''}`}
            onClick={() => setFilter('completed')}
          >
            已完成 ({completedCount})
          </button>
        </div>

        {loading ? (
          <div className="loading">加载中...</div>
        ) : (
          <TaskList
            tasks={tasks}
            onToggle={handleToggleTask}
            onDelete={handleDeleteTask}
            onUpdate={handleUpdateTask}
            filter={filter}
          />
        )}

        {completedCount > 0 && (
          <div className="footer-actions">
            <button className="btn-clear-completed" onClick={handleClearCompleted}>
              清除已完成任务
            </button>
          </div>
        )}

        <footer className="app-footer">
          <p>
            {activeCount > 0
              ? `还有 ${activeCount} 个任务待完成`
              : '太棒了！所有任务都已完成 🎉'}
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
