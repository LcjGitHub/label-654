import React, { useState } from 'react';

function AddTask({ onAdd }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    
    onAdd({
      title: title.trim(),
      description: description.trim(),
    });
    
    setTitle('');
    setDescription('');
    setIsExpanded(false);
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
          <div className="add-task-actions">
            <button type="button" className="btn-cancel" onClick={() => setIsExpanded(false)}>
              取消
            </button>
            <button type="submit" className="btn-add" disabled={!title.trim()}>
              添加任务
            </button>
          </div>
        </div>
        )}
      </form>
    </div>
  );
}

export default AddTask;
