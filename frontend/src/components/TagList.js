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

function TagList({ tags, onUpdate, onDelete }) {
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('');

  const handleStartEdit = (tag) => {
    setEditingId(tag.id);
    setEditName(tag.name);
    setEditColor(tag.color);
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

  const handleDeleteClick = (tagId, tagName) => {
    if (window.confirm(`确定要删除标签「${tagName}」吗？`)) {
      onDelete(tagId);
    }
  };

  if (tags.length === 0) {
    return (
      <div className="tag-list">
        <h3 className="tag-list-title">标签管理</h3>
        <div className="tag-empty">
          <p>暂无标签，点击上方按钮创建第一个标签吧！</p>
        </div>
      </div>
    );
  }

  return (
    <div className="tag-list">
      <h3 className="tag-list-title">标签管理</h3>
      <div className="tag-grid">
        {tags.map((tag) => (
          <div key={tag.id} className="tag-card">
            {editingId === tag.id ? (
              <div className="tag-edit">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => handleKeyDown(e, tag.id)}
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
                <div className="tag-edit-actions">
                  <button className="btn-save" onClick={() => handleSave(tag.id)}>
                    保存
                  </button>
                  <button className="btn-cancel-edit" onClick={handleCancel}>
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="tag-info">
                  <span
                    className="tag-color-dot"
                    style={{ backgroundColor: tag.color }}
                  />
                  <span className="tag-name">{tag.name}</span>
                  <span className="tag-count">({tag.task_count || 0})</span>
                </div>
                <div className="tag-actions">
                  <button
                    className="btn-edit"
                    onClick={() => handleStartEdit(tag)}
                  >
                    编辑
                  </button>
                  <button
                    className="btn-delete"
                    onClick={() => handleDeleteClick(tag.id, tag.name)}
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

export default TagList;
