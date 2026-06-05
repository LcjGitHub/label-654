import React, { useState } from 'react';

const PRESET_COLORS = [
  '#667eea',
  '#764ba2',
  '#f093fb',
  '#f5576c',
  '#4facfe',
  '#00f2fe',
  '#43e97b',
  '#fa709a',
  '#fee140',
  '#30cfd0',
  '#a8edea',
  '#ff9a9e',
];

function AddCategory({ onAdd }) {
  const [name, setName] = useState('');
  const [color, setColor] = useState(PRESET_COLORS[0]);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    onAdd({
      name: name.trim(),
      color: color,
    });

    setName('');
    setColor(PRESET_COLORS[0]);
    setIsExpanded(false);
  };

  return (
    <div className="add-category">
      {!isExpanded ? (
        <button
          type="button"
          className="add-category-trigger"
          onClick={() => setIsExpanded(true)}
        >
          <span className="add-icon">+</span>
          <span>添加新分类</span>
        </button>
      ) : (
        <form className="add-category-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <input
              type="text"
              placeholder="分类名称"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="color-picker">
            <span className="color-label">选择颜色：</span>
            <div className="color-options">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`color-option ${color === c ? 'selected' : ''}`}
                  style={{ backgroundColor: c }}
                  onClick={() => setColor(c)}
                  aria-label={`选择颜色 ${c}`}
                />
              ))}
            </div>
          </div>
          <div className="add-category-actions">
            <button
              type="button"
              className="btn-cancel"
              onClick={() => {
                setIsExpanded(false);
                setName('');
                setColor(PRESET_COLORS[0]);
              }}
            >
              取消
            </button>
            <button type="submit" className="btn-add" disabled={!name.trim()}>
              创建分类
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default AddCategory;
