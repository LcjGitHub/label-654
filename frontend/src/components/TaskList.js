import React from 'react';
import TaskItem from './TaskItem';

function TaskList({ tasks, onToggle, onDelete, onUpdate, filter, categoryFilter, priorityFilter, sortBy, categories }) {
  const priorityOrder = { high: 0, medium: 1, low: 2 };

  let filteredTasks = tasks.filter((task) => {
    if (filter === 'active') return !task.completed;
    if (filter === 'completed') return task.completed;
    return true;
  }).filter((task) => {
    if (categoryFilter === 'all') return true;
    if (categoryFilter === 'none') return !task.category_id;
    return task.category_id === Number(categoryFilter);
  }).filter((task) => {
    if (priorityFilter === 'all') return true;
    return task.priority === priorityFilter;
  });

  const sortedTasks = [...filteredTasks].sort((a, b) => {
    switch (sortBy) {
      case 'due_date_asc':
        if (!a.due_date && !b.due_date) return 0;
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return new Date(a.due_date) - new Date(b.due_date);
      case 'due_date_desc':
        if (!a.due_date && !b.due_date) return 0;
        if (!a.due_date) return 1;
        if (!b.due_date) return -1;
        return new Date(b.due_date) - new Date(a.due_date);
      case 'priority':
        return priorityOrder[a.priority || 'medium'] - priorityOrder[b.priority || 'medium'];
      case 'created_at':
      default:
        return new Date(b.created_at) - new Date(a.created_at);
    }
  });

  if (sortedTasks.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📋</div>
        <p>
          {filter === 'all' && categoryFilter === 'all' && priorityFilter === 'all'
            ? '暂无任务，添加一个吧！'
            : filter === 'active'
            ? '没有待完成的任务'
            : filter === 'completed'
            ? '没有已完成的任务'
            : '没有符合条件的任务'}
        </p>
      </div>
    );
  }

  return (
    <div className="task-list">
      {sortedTasks.map((task) => (
        <TaskItem
          key={task.id}
          task={task}
          onToggle={onToggle}
          onDelete={onDelete}
          onUpdate={onUpdate}
          categories={categories}
        />
      ))}
    </div>
  );
}

export default TaskList;
