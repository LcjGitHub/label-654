import React, { useState, useEffect } from 'react';
import TaskItem from './TaskItem';

function TaskList({ tasks, onToggle, onTogglePin, onDelete, onUpdate, filter, categoryFilter, categories, tags, onStatsChange, onAddTagToTask, onRemoveTagFromTask, onUploadAttachment, onDeleteAttachment, tagFilter, searchQuery, loading }) {
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');
  const priorityOrder = { high: 0, medium: 1, low: 2 };

  const categoryFilteredTasks = tasks.filter((task) => {
    if (categoryFilter === 'all') return true;
    if (categoryFilter === 'none') return !task.category_id;
    return task.category_id === Number(categoryFilter);
  }).filter((task) => {
    if (tagFilter === 'all' || tagFilter === null) return true;
    if (tagFilter === 'none') return !task.tags || task.tags.length === 0;
    return task.tags && task.tags.some(t => t.id === Number(tagFilter));
  }).filter((task) => {
    if (priorityFilter === 'all') return true;
    return task.priority === priorityFilter;
  });

  const statusFilteredTasks = categoryFilteredTasks.filter((task) => {
    if (filter === 'active') return !task.completed;
    if (filter === 'completed') return task.completed;
    return true;
  });

  const sortedTasks = [...statusFilteredTasks].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) {
      return b.is_pinned ? 1 : -1;
    }
    return new Date(b.created_at) - new Date(a.created_at);
  });

  useEffect(() => {
    if (onStatsChange) {
      onStatsChange({
        total: categoryFilteredTasks.length,
        active: categoryFilteredTasks.filter((t) => !t.completed).length,
        completed: categoryFilteredTasks.filter((t) => t.completed).length,
        priorityFilter,
        categoryFilter,
        tagFilter,
      });
    }
  }, [categoryFilteredTasks, priorityFilter, categoryFilter, tagFilter, onStatsChange]);

  const hasActiveSearch = searchQuery && searchQuery.trim() !== '';

  const getEmptyMessage = () => {
    if (hasActiveSearch) {
      return '未找到匹配的任务';
    }
    if (tagFilter && tagFilter !== 'all' && tagFilter !== 'none') {
      const selectedTag = tags ? tags.find(t => t.id === Number(tagFilter)) : null;
      return selectedTag
        ? `标签 "${selectedTag.name}" 下暂无任务`
        : '该标签下暂无任务';
    }
    if (tagFilter === 'none') {
      return '暂无无标签的任务';
    }
    if (filter === 'all' && categoryFilter === 'all' && priorityFilter === 'all') {
      return '暂无任务，添加一个吧！';
    }
    if (filter === 'active') return '没有待完成的任务';
    if (filter === 'completed') return '没有已完成的任务';
    return '没有符合条件的任务';
  };

  const searchResultInfo = hasActiveSearch && !loading ? (
    <div className="search-result-info">
      找到 <strong>{sortedTasks.length}</strong> 个匹配 "{searchQuery.trim()}" 的任务
    </div>
  ) : null;

  const filterControls = (
    <div className="list-filter-controls">
      <div className="priority-filter">
        <label htmlFor="priority-filter">优先级：</label>
        <select
          id="priority-filter"
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
        >
          <option value="all">全部优先级</option>
          <option value="high">🔴 高优先级</option>
          <option value="medium">🟡 中优先级</option>
          <option value="low">🟢 低优先级</option>
        </select>
      </div>

      <div className="sort-control">
        <label htmlFor="sort-by">排序：</label>
        <select
          id="sort-by"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="created_at">按创建时间</option>
          <option value="due_date_asc">截止日期（升序）</option>
          <option value="due_date_desc">截止日期（降序）</option>
          <option value="priority">按优先级</option>
        </select>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="task-list-section">
        {filterControls}
        {searchResultInfo}
        <div className="task-list-loading">
          <div className="spinner"></div>
          <span>搜索中...</span>
        </div>
      </div>
    );
  }

  if (sortedTasks.length === 0) {
    return (
      <div className="task-list-section">
        {filterControls}
        {searchResultInfo}
        <div className="empty-state">
          <div className="empty-icon">{hasActiveSearch ? '🔍' : '📋'}</div>
          <p>{getEmptyMessage()}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="task-list-section">
      {filterControls}
      {searchResultInfo}
      <div className="task-list">
        {sortedTasks.map((task) => (
          <TaskItem
            key={task.id}
            task={task}
            onToggle={onToggle}
            onTogglePin={onTogglePin}
            onDelete={onDelete}
            onUpdate={onUpdate}
            categories={categories}
            tags={tags}
            onAddTagToTask={onAddTagToTask}
            onRemoveTagFromTask={onRemoveTagFromTask}
            onUploadAttachment={onUploadAttachment}
            onDeleteAttachment={onDeleteAttachment}
          />
        ))}
      </div>
    </div>
  );
}

export default TaskList;
