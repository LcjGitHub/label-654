import React, { useState } from 'react';

function TaskItem({ task, onToggle, onDelete, onUpdate, categories }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editDescription, setEditDescription] = useState(task.description);
  const [editCategoryId, setEditCategoryId] = useState(task.category_id || '');

  const handleSave = () => {
    if (!editTitle.trim()) return;
    onUpdate(task.id, {
      title: editTitle.trim(),
      description: editDescription.trim(),
      category_id: editCategoryId ? Number(editCategoryId) : null,
    });
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    }
    if (e.key === 'Escape') {
      setIsEditing(false);
      setEditTitle(task.title);
      setEditDescription(task.description);
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isEditing) {
    return (
      <div className="task-item editing">
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          className="edit-input"
        />
        <textarea
          value={editDescription}
          onChange={(e) => setEditDescription(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="添加描述..."
          className="edit-textarea"
        />
        {categories.length > 0 && (
          <div className="task-category-select">
            <label htmlFor={`edit-category-${task.id}`}>选择分类：</label>
            <select
              id={`edit-category-${task.id}`}
              value={editCategoryId}
              onChange={(e) => setEditCategoryId(e.target.value)}
            >
              <option value="">无分类</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="edit-actions">
          <button className="btn-save" onClick={handleSave}>
            保存
          </button>
          <button
            className="btn-cancel-edit"
            onClick={() => {
              setIsEditing(false);
              setEditTitle(task.title);
              setEditDescription(task.description);
              setEditCategoryId(task.category_id || '');
            }}
          >
            取消
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`task-item ${task.completed ? 'completed' : ''}`}>
      <div className="task-header">
        <label className="task-checkbox">
          <input
            type="checkbox"
            checked={task.completed}
            onChange={() => onToggle(task.id)}
            aria-label={`标记任务"${task.title}"为${task.completed ? '未完成' : '已完成'}`}
          />
          <span className={`checkbox ${task.completed ? 'checked' : ''}`}>
            {task.completed && <span className="checkmark">✓</span>}
          </span>
        </label>
        <div className="task-content" onDoubleClick={() => setIsEditing(true)}>
          <h3 className={task.completed ? 'completed-text' : ''}>
            {task.category && (
              <span
                className="task-category-badge"
                style={{ backgroundColor: task.category.color }}
                title={task.category.name}
              />
            )}
            {task.title}
          </h3>
          {task.description && (
            <p className={task.completed ? 'completed-text' : ''}>{task.description}</p>
          )}
          <div className="task-meta">
            <span className="task-date">{formatDate(task.created_at)}</span>
            {task.category && (
              <span
                className="task-category-tag"
                style={{
                  backgroundColor: task.category.color + '20',
                  color: task.category.color,
                  borderColor: task.category.color,
                }}
              >
                {task.category.name}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="task-actions">
        <button className="btn-edit" onClick={() => setIsEditing(true)}>
          编辑
        </button>
        <button className="btn-delete" onClick={() => onDelete(task.id)}>
          删除
        </button>
      </div>
    </div>
  );
}

export default TaskItem;
