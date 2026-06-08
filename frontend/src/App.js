import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { taskApi, categoryApi, tagApi, attachmentApi, teamApi } from './services/api';
import { useAuth } from './context/AuthContext';
import AddTask from './components/AddTask';
import TaskList from './components/TaskList';
import AddCategory from './components/AddCategory';
import CategoryList from './components/CategoryList';
import AddTag from './components/AddTag';
import TagList from './components/TagList';
import TagCloud from './components/TagCloud';
import SearchBar from './components/SearchBar';
import StatsPanel from './components/StatsPanel';
import Login from './components/Login';
import Register from './components/Register';
import ProtectedRoute from './components/ProtectedRoute';
import TeamManager from './components/TeamManager';
import TeamBoard from './components/TeamBoard';
import AcceptInvitation from './components/AcceptInvitation';
import TemplateManager from './components/TemplateManager';
import './App.css';

function TodoApp() {
  const [tasks, setTasks] = useState([]);
  const [assignedTasks, setAssignedTasks] = useState([]);
  const [sharedTasks, setSharedTasks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [tags, setTags] = useState([]);
  const [filter, setFilter] = useState('all');
  const [taskView, setTaskView] = useState('mine');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [tagFilter, setTagFilter] = useState(null);
  const [showCategoryManager, setShowCategoryManager] = useState(false);
  const [showTagManager, setShowTagManager] = useState(false);
  const [showTeamManager, setShowTeamManager] = useState(false);
  const [showTeamBoard, setShowTeamBoard] = useState(false);
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({ total: 0, active: 0, completed: 0, priorityFilter: 'all', categoryFilter: 'all' });
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [showStats, setShowStats] = useState(false);
  const tasksAbortControllerRef = useRef(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const resolveCategoryIdForApi = () => {
    if (categoryFilter === 'all') return null;
    if (categoryFilter === 'none') return 'none';
    return Number(categoryFilter);
  };

  const resolveTagIdForApi = () => {
    if (tagFilter === null || tagFilter === 'all') return null;
    if (tagFilter === 'none') return 'none';
    return Number(tagFilter);
  };

  const fetchTasks = useCallback(async (signal) => {
    const search = debouncedSearch.trim() !== '' ? debouncedSearch : null;
    const categoryId = resolveCategoryIdForApi();
    const tagId = resolveTagIdForApi();
    return taskApi.getAllTasks(signal, categoryId, tagId, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, categoryFilter, tagFilter]);

  const fetchAssignedTasks = useCallback(async (signal) => {
    return teamApi.getAssignedTasks(signal);
  }, []);

  const fetchSharedTasks = useCallback(async (signal) => {
    return teamApi.getSharedTasks(signal);
  }, []);

  const refreshAssignedAndShared = useCallback(async () => {
    try {
      const [assigned, shared] = await Promise.all([
        fetchAssignedTasks(),
        fetchSharedTasks(),
      ]);
      setAssignedTasks(assigned || []);
      setSharedTasks(shared || []);
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('获取分配/共享任务失败:', err);
      }
    }
  }, [fetchAssignedTasks, fetchSharedTasks]);

  const refreshTasks = useCallback(async () => {
    tasksAbortControllerRef.current?.abort();
    tasksAbortControllerRef.current = new AbortController();
    try {
      setTasksLoading(true);
      const [tasksData] = await Promise.all([
        fetchTasks(tasksAbortControllerRef.current.signal),
        refreshAssignedAndShared(),
      ]);
      if (!tasksAbortControllerRef.current.signal?.aborted) {
        setTasks(tasksData);
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message);
      }
    } finally {
      if (!tasksAbortControllerRef.current.signal?.aborted) {
        setTasksLoading(false);
      }
    }
  }, [fetchTasks, refreshAssignedAndShared]);

  const checkAndCreateRepeatTasks = useCallback(async () => {
    try {
      const result = await taskApi.checkRepeatTasks();
      if (result.created_count > 0) {
        await refreshTasks();
      }
    } catch (err) {
      setError('检查重复任务失败：' + (err.message || '未知错误'));
      setTimeout(() => setError(null), 5000);
    }
  }, [refreshTasks]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    const initialController = new AbortController();
    tasksAbortControllerRef.current = initialController;

    const initData = async () => {
      try {
        setInitialLoading(true);
        setError(null);
        const [tasksData, categoriesData, tagsData, assignedData, sharedData] = await Promise.all([
          fetchTasks(initialController.signal),
          categoryApi.getAllCategories(initialController.signal),
          tagApi.getAllTags(initialController.signal),
          fetchAssignedTasks(initialController.signal).catch(() => []),
          fetchSharedTasks(initialController.signal).catch(() => []),
        ]);
        if (!initialController.signal?.aborted) {
          setTasks(tasksData);
          setCategories(categoriesData);
          setTags(tagsData);
          setAssignedTasks(assignedData || []);
          setSharedTasks(sharedData || []);
        }
        if (!initialController.signal?.aborted) {
          await checkAndCreateRepeatTasks();
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message);
        }
      } finally {
        if (!initialController.signal?.aborted) {
          setInitialLoading(false);
        }
      }
    };

    initData();

    return () => {
      initialController.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      checkAndCreateRepeatTasks();
    }, 24 * 60 * 60 * 1000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (initialLoading) return;
    refreshTasks();
  }, [debouncedSearch, categoryFilter, tagFilter, initialLoading, refreshTasks]);

  const handleAddCategory = async (category) => {
    try {
      setError(null);
      const newCategory = await categoryApi.createCategory(category);
      setCategories(prevCategories => [...prevCategories, newCategory]);
    } catch (err) {
      setError(err.message);
      throw err;
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

  const handleAddTag = async (tag) => {
    try {
      setError(null);
      const newTag = await tagApi.createTag(tag);
      setTags(prevTags => [...prevTags, newTag]);
      return newTag;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const handleUpdateTag = async (id, tagData) => {
    try {
      setError(null);
      const updatedTag = await tagApi.updateTag(id, tagData);
      setTags(prevTags =>
        prevTags.map(tag => (tag.id === id ? updatedTag : tag))
      );
      setTasks(prevTasks =>
        prevTasks.map(task => ({
          ...task,
          tags: task.tags?.map(tag =>
            tag.id === id ? updatedTag : tag
          )
        }))
      );
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteTag = async (id) => {
    try {
      setError(null);
      await tagApi.deleteTag(id);
      setTags(prevTags => prevTags.filter(tag => tag.id !== id));
      setTasks(prevTasks =>
        prevTasks.map(task => ({
          ...task,
          tags: task.tags?.filter(tag => tag.id !== id)
        }))
      );
      if (tagFilter === id) {
        setTagFilter(null);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAddTagToTask = async (taskId, tagId) => {
    try {
      setError(null);
      const updatedTags = await tagApi.addTagToTask(taskId, tagId);
      setTasks(prevTasks =>
        prevTasks.map(task =>
          task.id === taskId
            ? { ...task, tags: updatedTags }
            : task
        )
      );
      const tag = tags.find(t => t.id === tagId);
      if (tag) {
        setTags(prevTags =>
          prevTags.map(t =>
            t.id === tagId
              ? { ...t, task_count: (t.task_count || 0) + 1 }
              : t
          )
        );
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRemoveTagFromTask = async (taskId, tagId) => {
    try {
      setError(null);
      const updatedTags = await tagApi.removeTagFromTask(taskId, tagId);
      setTasks(prevTasks =>
        prevTasks.map(task =>
          task.id === taskId
            ? { ...task, tags: updatedTags }
            : task
        )
      );
      const tag = tags.find(t => t.id === tagId);
      if (tag) {
        setTags(prevTags =>
          prevTags.map(t =>
            t.id === tagId
              ? { ...t, task_count: Math.max(0, (t.task_count || 0) - 1) }
              : t
          )
        );
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTagFilterClick = (tagId) => {
    setTagFilter(tagId);
  };

  const handleAddTask = async (task, selectedFiles = []) => {
    try {
      setError(null);
      const createdTask = await taskApi.createTask(task);
      const failedFiles = [];
      if (selectedFiles && selectedFiles.length > 0) {
        for (const file of selectedFiles) {
          try {
            await attachmentApi.uploadAttachment(createdTask.id, file);
          } catch (err) {
            console.error('上传附件失败:', file.name, err);
            failedFiles.push({ file, error: err.message });
          }
        }
      }
      await refreshTasks();
      return { task: createdTask, failedFiles };
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const handleUploadAttachment = async (taskId, file) => {
    try {
      setError(null);
      const result = await attachmentApi.uploadAttachment(taskId, file);
      setTasks(prevTasks =>
        prevTasks.map(task =>
          task.id === taskId
            ? { ...task, attachments: result.attachments }
            : task
        )
      );
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const handleDeleteAttachment = async (taskId, attachmentId) => {
    try {
      setError(null);
      const result = await attachmentApi.deleteAttachment(attachmentId);
      setTasks(prevTasks =>
        prevTasks.map(task =>
          task.id === taskId
            ? { ...task, attachments: result.attachments }
            : task
        )
      );
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const handleToggleTask = async (id) => {
    try {
      setError(null);
      await taskApi.toggleTask(id);
      await refreshTasks();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTogglePinTask = async (id) => {
    try {
      setError(null);
      await taskApi.togglePinTask(id);
      await refreshTasks();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteTask = async (id) => {
    try {
      setError(null);
      await taskApi.deleteTask(id);
      await refreshTasks();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdateTask = async (id, taskData) => {
    try {
      setError(null);
      await taskApi.updateTask(id, taskData);
      await refreshTasks();
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
      await refreshTasks();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const handleStatsChange = (newStats) => {
    setStats(newStats);
  };

  const totalCount = stats.total;
  const activeCount = stats.active;
  const completedCount = stats.completed;

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
              <button
                type="button"
                className="btn-team-board"
                onClick={() => setShowTeamBoard(true)}
                title="团队任务看板"
              >
                👥 团队看板
              </button>
              <button
                type="button"
                className="btn-team-manager"
                onClick={() => setShowTeamManager(true)}
                title="团队管理"
              >
                🏢 团队管理
              </button>
              <button
                type="button"
                className="btn-stats"
                onClick={() => setShowStats(true)}
                title="查看任务统计"
              >
                📊 统计
              </button>
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

        <SearchBar
          value={searchQuery}
          onChange={setSearchQuery}
        />

        <AddTask
          onAdd={handleAddTask}
          categories={categories}
          tags={tags}
          onCreateTag={handleAddTag}
          onOpenTemplateManager={() => setShowTemplateManager(true)}
        />

        <div className="manager-toggles">
          <button
            type="button"
            className="category-toggle-btn"
            onClick={() => setShowCategoryManager(!showCategoryManager)}
          >
            {showCategoryManager ? '隐藏分类管理' : '管理分类'}
          </button>
          <button
            type="button"
            className="tag-toggle-btn"
            onClick={() => setShowTagManager(!showTagManager)}
          >
            {showTagManager ? '隐藏标签管理' : '管理标签'}
          </button>
          <button
            type="button"
            className="template-toggle-btn"
            onClick={() => setShowTemplateManager(true)}
          >
            📋 管理模板
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

        {showTagManager && (
          <div className="tag-manager">
            <AddTag onAdd={handleAddTag} />
            <TagList
              tags={tags}
              onUpdate={handleUpdateTag}
              onDelete={handleDeleteTag}
            />
          </div>
        )}

        <TagCloud
          tags={tags}
          selectedTagId={tagFilter}
          onTagClick={handleTagFilterClick}
        />

        <div className="filter-section">
          <div className="task-view-tabs">
            <button
              className={`task-view-btn ${taskView === 'mine' ? 'active' : ''}`}
              onClick={() => setTaskView('mine')}
            >
              📋 我的任务
            </button>
            <button
              className={`task-view-btn ${taskView === 'assigned' ? 'active' : ''}`}
              onClick={() => setTaskView('assigned')}
            >
              📨 分配给我 ({assignedTasks.length})
            </button>
            <button
              className={`task-view-btn ${taskView === 'shared' ? 'active' : ''}`}
              onClick={() => setTaskView('shared')}
            >
              🤝 共享给我 ({sharedTasks.length})
            </button>
          </div>

          <div className="filter-tabs">
            <button
              className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              全部 ({totalCount})
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

          <div className="filter-controls">
            <div className="category-filter">
              <label htmlFor="category-filter">分类：</label>
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
        </div>

        {initialLoading ? (
          <div className="loading">加载中...</div>
        ) : (
          <TaskList
            tasks={taskView === 'assigned' ? assignedTasks : taskView === 'shared' ? sharedTasks : tasks}
            onToggle={handleToggleTask}
            onTogglePin={handleTogglePinTask}
            onDelete={handleDeleteTask}
            onUpdate={handleUpdateTask}
            filter={filter}
            categoryFilter={categoryFilter}
            categories={categories}
            tags={tags}
            onStatsChange={handleStatsChange}
            onAddTagToTask={handleAddTagToTask}
            onRemoveTagFromTask={handleRemoveTagFromTask}
            onUploadAttachment={handleUploadAttachment}
            onDeleteAttachment={handleDeleteAttachment}
            tagFilter={tagFilter}
            searchQuery={searchQuery}
            loading={tasksLoading}
          />
        )}

        {completedCount > 0 && !initialLoading && taskView === 'mine' && (
          <div className="footer-actions">
            <button className="btn-clear-completed" onClick={handleClearCompleted}>
              清除已完成任务
            </button>
          </div>
        )}

        <footer className="app-footer">
          <p>
            {initialLoading
              ? '正在加载任务列表...'
              : (() => {
                const currentTasks = taskView === 'assigned' ? assignedTasks : taskView === 'shared' ? sharedTasks : tasks;
                const currentTotal = currentTasks.length;
                const currentActive = currentTasks.filter(t => !t.completed).length;
                if (taskView === 'assigned') {
                  return currentTotal === 0 ? '暂无分配给你的任务' : `还有 ${currentActive} 个分配给你的任务待完成`;
                }
                if (taskView === 'shared') {
                  return currentTotal === 0 ? '暂无共享给你的任务' : `有 ${currentTotal} 个共享任务`;
                }
                const selectedTag = (stats.tagFilter && stats.tagFilter !== 'all' && stats.tagFilter !== 'none')
                  ? tags.find(t => t.id === Number(stats.tagFilter))
                  : null;
                if (totalCount === 0) {
                  if (selectedTag) {
                    return `标签 "${selectedTag.name}" 下暂无任务`;
                  }
                  if (stats.tagFilter === 'none') {
                    return '暂无无标签的任务';
                  }
                  if (stats.priorityFilter !== 'all') {
                    return '该优先级下暂无任务';
                  }
                  if (stats.categoryFilter !== 'all') {
                    return '该分类下暂无任务';
                  }
                  return '暂无任务';
                }
                if (activeCount > 0) {
                  if (selectedTag) {
                    return `标签 "${selectedTag.name}" 下还有 ${activeCount} 个任务待完成`;
                  }
                  if (stats.tagFilter === 'none') {
                    return `无标签任务中还有 ${activeCount} 个待完成`;
                  }
                  return `还有 ${activeCount} 个任务待完成`;
                }
                if (selectedTag) {
                  return `太棒了！标签 "${selectedTag.name}" 下所有任务都已完成 🎉`;
                }
                if (stats.tagFilter === 'none') {
                  return '太棒了！无标签的任务都已完成 🎉';
                }
                if (stats.priorityFilter !== 'all') {
                  return '太棒了！该优先级下所有任务都已完成 🎉';
                }
                if (stats.categoryFilter !== 'all') {
                  return '太棒了！该分类下所有任务都已完成 🎉';
                }
                return '太棒了！所有任务都已完成 🎉';
              })()}
          </p>
        </footer>

        {showStats && <StatsPanel onClose={() => setShowStats(false)} />}

        {showTeamManager && (
          <TeamManager
            onClose={() => { setShowTeamManager(false); }}
          />
        )}

        {showTeamBoard && (
          <TeamBoard
            onClose={() => { setShowTeamBoard(false); }}
            allTags={tags}
          />
        )}

        {showTemplateManager && (
          <TemplateManager
            onClose={() => { setShowTemplateManager(false); }}
          />
        )}
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
        <Route path="/invite/:token" element={<AcceptInvitation />} />
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
