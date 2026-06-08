import React, { useState } from 'react';

function SaveAsTemplateModal({ task, onClose, onSave }) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || submitting) return;

    setSubmitting(true);
    setError('');
    try {
      await onSave(name.trim());
      onClose();
    } catch (err) {
      setError(err.message || '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content save-as-template-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>💾 另存为模板</h2>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="template-name">模板名称 *</label>
            <input
              type="text"
              id="template-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="请输入模板名称"
              autoFocus
            />
          </div>

          <div className="template-preview">
            <h4>模板预览内容：</h4>
            <div className="template-preview-item">
              <span className="preview-label">标题：</span>
              <span className="preview-value">{task.title}</span>
            </div>
            {task.description && (
              <div className="template-preview-item">
                <span className="preview-label">描述：</span>
                <span className="preview-value">{task.description}</span>
              </div>
            )}
            {task.priority && (
              <div className="template-preview-item">
                <span className="preview-label">优先级：</span>
                <span className="preview-value">
                  {task.priority === 'high' ? '🔴 高' : task.priority === 'low' ? '🟢 低' : '🟡 中'}
                </span>
              </div>
            )}
            {task.category && (
              <div className="template-preview-item">
                <span className="preview-label">分类：</span>
                <span className="preview-value">{task.category.name}</span>
              </div>
            )}
            {task.tags && task.tags.length > 0 && (
              <div className="template-preview-item">
                <span className="preview-label">标签：</span>
                <span className="preview-value">
                  {task.tags.map(t => t.name).join('、')}
                </span>
              </div>
            )}
          </div>

          {error && (
            <div style={{ marginTop: '8px', padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', borderRadius: '6px', fontSize: '0.85rem' }}>
              ❌ {error}
            </div>
          )}

          <div className="form-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              取消
            </button>
            <button type="submit" className="btn-save" disabled={!name.trim() || submitting}>
              {submitting ? '保存中...' : '保存模板'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SaveAsTemplateModal;
