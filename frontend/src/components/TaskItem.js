import React, { useState } from 'react';

function formatForDatetimeLocal(dateStr) {
  if (!dateStr) return '';
  const normalized = dateStr.replace(' ', 'T');
  return normalized.slice(0, 16);
}

function TaskItem({ task, onToggle, onTogglePin, onDelete, onUpdate, categories, tags, onAddTagToTask, onRemoveTagFromTask }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editDescription, setEditDescription] = useState(task.description);
  const [editCategoryId, setEditCategoryId] = useState(task.category_id || '');
  const [editPriority, setEditPriority] = useState(task.priority || 'medium');
  const [editDueDate, setEditDueDate] = useState(formatForDatetimeLocal(task.due_date));
  const [editTagIds, setEditTagIds] = useState((task.tags || []).map(t => t.id));

  const handleTagToggle = (tagId) => {
    setEditTagIds(prev =>
      prev.includes(tagId)
        ? prev.filter(id => id !== tagId)
        : [...prev, tagId]
    );
  };

  const handleSave = async () => {
    if (!editTitle.trim()) return;
    try {
      await onUpdate(task.id, {
        title: editTitle.trim(),
        description: editDescription.trim(),
        category_id: editCategoryId ? Number(editCategoryId) : null,
        priority: editPriority,
        due_date: editDueDate || null,
      });

      const currentTagIds = (task.tags || []).map(t => t.id);
      const tagsToAdd = editTagIds.filter(id => !currentTagIds.includes(id));
      const tagsToRemove = currentTagIds.filter(id => !editTagIds.includes(id));

      for (const tagId of tagsToAdd) {
        await onAddTagToTask(task.id, tagId);
      }
      for (const tagId of tagsToRemove) {
        await onRemoveTagFromTask(task.id, tagId);
      }
    } catch (err) {
    }
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
      setEditCategoryId(task.category_id || '');
      setEditPriority(task.priority || 'medium');
      setEditDueDate(formatForDatetimeLocal(task.due_date));
      setEditTagIds((task.tags || []).map(t => t.id));
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

  const isOverdue = () => {
    if (!task.due_date || task.completed) return false;
    return new Date(task.due_date) < new Date();
  };

  const getPriorityLabel = (priority) => {
    switch (priority) {
      case 'high': return '高';
      case 'low': return '低';
      default: return '中';
    }
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
        <div className="task-priority-select">
          <label htmlFor={`edit-priority-${task.id}`}>优先级：</label>
          <select
            id={`edit-priority-${task.id}`}
            value={editPriority}
            onChange={(e) => setEditPriority(e.target.value)}
          >
            <option value="high">🔴 高优先级</option>
            <option value="medium">🟡 中优先级</option>
            <option value="low">🟢 低优先级</option>
          </select>
        </div>
        <div className="task-due-date">
          <label htmlFor={`edit-due-date-${task.id}`}>截止日期：</label>
          <input
            type="datetime-local"
            id={`edit-due-date-${task.id}`}
            value={editDueDate}
            onChange={(e) => setEditDueDate(e.target.value)}
          />
        </div>
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

        {tags.length > 0 && (
          <div className="task-tags-select">
            <label>选择标签：</label>
            <div className="tag-checkboxes">
              {tags.map((tag) => (
                <label
                  key={tag.id}
                  className={`tag-checkbox ${editTagIds.includes(tag.id) ? 'selected' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={editTagIds.includes(tag.id)}
                    onChange={() => handleTagToggle(tag.id)}
                  />
                  <span
                    className="tag-checkbox-dot"
                    style={{ backgroundColor: tag.color }}
                  />
                  <span className="tag-checkbox-name">{tag.name}</span>
                </label>
              ))}
            </div>
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
              setEditPriority(task.priority || 'medium');
              setEditDueDate(formatForDatetimeLocal(task.due_date));
              setEditTagIds((task.tags || []).map(t => t.id));
            }}
          >
            取消
          </button>
        </div>
      </div>
    );
  }

  const overdue = isOverdue();

  return (
    <div className={`task-item ${task.completed ? 'completed' : ''} ${overdue ? 'overdue' : ''} ${task.is_pinned ? 'pinned' : ''}`}>
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
            {task.is_pinned && (
              <span className="pin-indicator" title="已置顶">📌</span>
            )}
            <span className={`task-priority-badge priority-${task.priority || 'medium'}`}>
              {getPriorityLabel(task.priority)}
            </span>
            {task.category && (
              <span
                className="task-category-badge"
                style={{ backgroundColor: task.category.color }}
                title={task.category.name}
              />
            )}
            {task.tags && task.tags.length > 0 && (
              <span className="task-tag-dots">
                {task.tags.map((tag) => (
                  <span
                    key={tag.id}
                    className="task-tag-dot"
                    style={{ backgroundColor: tag.color }}
                    title={tag.name}
                  />
                ))}
              </span>
            )}
            {task.title}
          </h3>
          {task.description && (
            <p className={task.completed ? 'completed-text' : ''}>{task.description}</p>
          )}
          <div className="task-meta">
            <span className="task-date">{formatDate(task.created_at)}</span>
            {task.due_date && (
              <span className={`task-due-date-tag ${overdue ? 'overdue' : ''}`}>
                📅 {formatDate(task.due_date)}
                {overdue && ' (已过期)'}
              </span>
            )}
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
        <button
          className={`btn-pin ${task.is_pinned ? 'pinned' : ''}`}
          onClick={() => onTogglePin(task.id)}
          title={task.is_pinned ? '取消置顶' : '置顶'}
        >
          📌
        </button>
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
