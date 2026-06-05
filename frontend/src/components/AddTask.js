import React, { useState } from 'react';

function AddTask({ onAdd, categories }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [priority, setPriority] = useState('medium');
  const [dueDate, setDueDate] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || isSubmitting) return;
    
    setIsSubmitting(true);
    try {
      await onAdd({
        title: title.trim(),
        description: description.trim(),
        category_id: categoryId ? Number(categoryId) : null,
        priority: priority,
        due_date: dueDate || null,
      });
      
      setTitle('');
      setDescription('');
      setCategoryId('');
      setPriority('medium');
      setDueDate('');
      setIsExpanded(false);
    } catch (err) {
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="add-task">
      <form onSubmit={handleSubmit}>
      {!isExpanded ? (
        <div className="add-task-input">
          <span className="add-icon" onClick={() => setIsExpanded(true)}>
            +
          </span>
          <input
            type="text"
            placeholder="添加新任务..."
            value={title}
            onClick={() => setIsExpanded(true)}
            readOnly
          />
        </div>
      ) : (
        <div className="add-task-expanded">
          <input
            type="text"
            placeholder="任务标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />
          <textarea
            placeholder="任务描述（可选）"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows="3"
          />
          <div className="task-priority-select">
            <label htmlFor="priority">优先级：</label>
            <select
              id="priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="high">🔴 高优先级</option>
              <option value="medium">🟡 中优先级</option>
              <option value="low">🟢 低优先级</option>
            </select>
          </div>
          <div className="task-due-date">
            <label htmlFor="due-date">截止日期：</label>
            <input
              type="datetime-local"
              id="due-date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>
          {categories.length > 0 && (
            <div className="task-category-select">
              <label htmlFor="category">选择分类：</label>
              <select
                id="category"
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
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
          <div className="add-task-actions">
            <button type="button" className="btn-cancel" onClick={() => setIsExpanded(false)}>
              取消
            </button>
            <button type="submit" className="btn-add" disabled={!title.trim() || isSubmitting}>
              {isSubmitting ? '添加中...' : '添加任务'}
            </button>
          </div>
        </div>
        )}
      </form>
    </div>
  );
}

export default AddTask;
