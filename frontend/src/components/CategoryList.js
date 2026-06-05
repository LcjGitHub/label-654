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

function CategoryList({ categories, onUpdate, onDelete }) {
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('');

  const handleStartEdit = (category) => {
    setEditingId(category.id);
    setEditName(category.name);
    setEditColor(category.color);
  };

  const handleSave = (id) => {
    if (!editName.trim()) return;
    onUpdate(id, {
      name: editName.trim(),
      color: editColor,
    });
    setEditingId(null);
    setEditName('');
    setEditColor('');
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditName('');
    setEditColor('');
  };

  const handleKeyDown = (e, id) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSave(id);
    }
    if (e.key === 'Escape') {
      handleCancel();
    }
  };

  if (categories.length === 0) {
    return null;
  }

  return (
    <div className="category-list">
      <h3 className="category-list-title">分类管理</h3>
      <div className="category-grid">
        {categories.map((category) => (
          <div key={category.id} className="category-card">
            {editingId === category.id ? (
              <div className="category-edit">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => handleKeyDown(e, category.id)}
                  autoFocus
                  className="edit-input"
                />
                <div className="color-options">
                  {PRESET_COLORS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      className={`color-option ${editColor === c ? 'selected' : ''}`}
                      style={{ backgroundColor: c }}
                      onClick={() => setEditColor(c)}
                      aria-label={`选择颜色 ${c}`}
                    />
                  ))}
                </div>
                <div className="category-edit-actions">
                  <button className="btn-save" onClick={() => handleSave(category.id)}>
                    保存
                  </button>
                  <button className="btn-cancel-edit" onClick={handleCancel}>
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="category-info">
                  <span
                    className="category-color-dot"
                    style={{ backgroundColor: category.color }}
                  />
                  <span className="category-name">{category.name}</span>
                </div>
                <div className="category-actions">
                  <button
                    className="btn-edit"
                    onClick={() => handleStartEdit(category)}
                  >
                    编辑
                  </button>
                  <button
                    className="btn-delete"
                    onClick={() => onDelete(category.id)}
                  >
                    删除
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default CategoryList;
