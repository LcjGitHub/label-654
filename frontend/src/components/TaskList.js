import React from 'react';
import TaskItem from './TaskItem';

function TaskList({ tasks, onToggle, onDelete, onUpdate, filter, categoryFilter, categories }) {
  const filteredTasks = tasks.filter((task) => {
    if (filter === 'active') return !task.completed;
    if (filter === 'completed') return task.completed;
    return true;
  }).filter((task) => {
    if (categoryFilter === 'all') return true;
    if (categoryFilter === 'none') return !task.category_id;
    return task.category_id === Number(categoryFilter);
  });

  if (filteredTasks.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📋</div>
        <p>
          {filter === 'all' && categoryFilter === 'all'
            ? '暂无任务，添加一个吧！'
            : filter === 'active'
            ? '没有待完成的任务'
            : filter === 'completed'
            ? '没有已完成的任务'
            : '该分类下没有任务'}
        </p>
      </div>
    );
  }

  return (
    <div className="task-list">
      {filteredTasks.map((task) => (
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
