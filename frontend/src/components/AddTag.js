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

function AddTag({ onAdd }) {
  const [name, setName] = useState('');
  const [color, setColor] = useState(PRESET_COLORS[0]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onAdd({
        name: name.trim(),
        color: color,
      });

      setName('');
      setColor(PRESET_COLORS[0]);
      setIsExpanded(false);
    } catch (err) {
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="add-tag">
      {!isExpanded ? (
        <button
          type="button"
          className="add-tag-trigger"
          onClick={() => setIsExpanded(true)}
        >
          <span className="add-icon">+</span>
          <span>添加新标签</span>
        </button>
      ) : (
        <form className="add-tag-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <input
              type="text"
              placeholder="标签名称"
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
          <div className="add-tag-actions">
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
            <button type="submit" className="btn-add" disabled={!name.trim() || isSubmitting}>
              {isSubmitting ? '创建中...' : '创建标签'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default AddTag;
