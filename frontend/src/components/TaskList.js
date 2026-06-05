import React from 'react';
import TaskItem from './TaskItem';

function TaskList({ tasks, onToggle, onDelete, onUpdate, filter }) {
  const filteredTasks = tasks.filter((task) => {
    if (filter === 'active') return !task.completed;
    if (filter === 'completed') return task.completed;
    return true;
  });

  if (filteredTasks.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">📋</div>
        <p>
          {filter === 'all'
            ? '暂无任务，添加一个吧！'
            : filter === 'active'
            ? '没有待完成的任务'
            : '没有已完成的任务'}
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
        />
      ))}
    </div>
  );
}

export default TaskList;
