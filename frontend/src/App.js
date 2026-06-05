import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { taskApi, categoryApi } from './services/api';
import { useAuth } from './context/AuthContext';
import AddTask from './components/AddTask';
import TaskList from './components/TaskList';
import AddCategory from './components/AddCategory';
import CategoryList from './components/CategoryList';
import Login from './components/Login';
import Register from './components/Register';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css';

function TodoApp() {
  const [tasks, setTasks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [filter, setFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [showCategoryManager, setShowCategoryManager] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    abortControllerRef.current = new AbortController();
    
    loadData(abortControllerRef.current.signal);

    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const loadData = async (signal) => {
    try {
      setLoading(true);
      setError(null);
      const [tasksData, categoriesData] = await Promise.all([
        taskApi.getAllTasks(signal),
        categoryApi.getAllCategories(signal),
      ]);
      if (!signal?.aborted) {
        setTasks(tasksData);
        setCategories(categoriesData);
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message);
      }
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  };

  const handleAddCategory = async (category) => {
    try {
      setError(null);
      const newCategory = await categoryApi.createCategory(category);
      setCategories(prevCategories => [...prevCategories, newCategory]);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdateCategory = async (id, categoryData) => {
    try {
      setError(null);
      const updatedCategory = await categoryApi.updateCategory(id, categoryData);
      setCategories(prevCategories =>
        prevCategories.map(cat => (cat.id === id ? updatedCategory : cat))
      );
      setTasks(prevTasks =>
        prevTasks.map(task =>
          task.category_id === id
            ? { ...task, category: updatedCategory }
            : task
        )
      );
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteCategory = async (id) => {
    try {
      setError(null);
      await categoryApi.deleteCategory(id);
      setCategories(prevCategories => prevCategories.filter(cat => cat.id !== id));
      setTasks(prevTasks =>
        prevTasks.map(task =>
          task.category_id === id
            ? { ...task, category_id: null, category: null }
            : task
        )
      );
      if (categoryFilter === String(id)) {
        setCategoryFilter('all');
      }
    } catch (err) {
      setError(err.message);
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
      await Promise.all(
        completedTasks.map((task) => taskApi.deleteTask(task.id))
      );
      setTasks(prevTasks => prevTasks.filter((task) => !task.completed));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const activeCount = tasks.filter((task) => !task.completed).length;
  const completedCount = tasks.filter((task) => task.completed).length;

  return (
    <div className="app">
      <div className="container">
        <header className="app-header">
          <div className="header-top">
            <div className="header-title">
              <h1>📝 待办事项</h1>
              <p className="subtitle">高效管理你的日常任务</p>
            </div>
            <div className="user-info">
              <span className="username">👤 {user?.username}</span>
              <button className="btn-logout" onClick={handleLogout}>
                退出登录
              </button>
            </div>
          </div>
        </header>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        <AddTask onAdd={handleAddTask} categories={categories} />

        <div className="category-toggle">
          <button
            type="button"
            className="category-toggle-btn"
            onClick={() => setShowCategoryManager(!showCategoryManager)}
          >
            {showCategoryManager ? '隐藏分类管理' : '管理分类'}
          </button>
        </div>

        {showCategoryManager && (
          <div className="category-manager">
            <AddCategory onAdd={handleAddCategory} />
            <CategoryList
              categories={categories}
              onUpdate={handleUpdateCategory}
              onDelete={handleDeleteCategory}
            />
          </div>
        )}

        <div className="filter-section">
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

          <div className="category-filter">
            <label htmlFor="category-filter">分类筛选：</label>
            <select
              id="category-filter"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="all">全部分类</option>
              <option value="none">无分类</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>
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
            categoryFilter={categoryFilter}
            categories={categories}
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
            {loading
              ? '正在加载任务列表...'
              : activeCount > 0
              ? `还有 ${activeCount} 个任务待完成`
              : '太棒了！所有任务都已完成 🎉'}
          </p>
        </footer>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <TodoApp />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
