import React, { useState, useEffect } from 'react';
import { templateApi } from '../services/api';

const REPEAT_OPTIONS = [
  { value: 'none', label: '不重复', icon: '' },
  { value: 'daily', label: '每天', icon: '🔁' },
  { value: 'weekly', label: '每周', icon: '📅' },
  { value: 'monthly', label: '每月', icon: '🗓️' },
  { value: 'yearly', label: '每年', icon: '📆' },
];

function TemplateSelector({ onSelect, onClose, onManage }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await templateApi.getAllTemplates();
      setTemplates(data);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || '加载失败');
      }
    } finally {
      setLoading(false);
    }
  };

  const priorityLabel = (p) => {
    if (p === 'high') return '🔴 高';
    if (p === 'low') return '🟢 低';
    return '🟡 中';
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content template-selector" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📋 选择任务模板</h2>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="template-selector-actions">
          <button type="button" className="btn-manage-templates" onClick={() => { onClose(); onManage(); }}>
            ⚙️ 管理模板
          </button>
        </div>

        {error && (
          <div style={{ padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', borderRadius: '6px', marginBottom: '12px', fontSize: '0.85rem' }}>
            ⚠️ {error}
          </div>
        )}

        {loading ? (
          <div className="loading">加载中...</div>
        ) : templates.length === 0 ? (
          <div className="empty-state">
            <p>📝 暂无模板</p>
            <p style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '8px' }}>
              点击"管理模板"创建第一个模板
            </p>
          </div>
        ) : (
          <div className="template-list">
            {templates.map((template) => (
              <div
                key={template.id}
                className="template-card clickable"
                onClick={() => onSelect(template)}
              >
                <div className="template-card-header">
                  <h4>{template.name}</h4>
                  <span className="template-use-hint">点击使用 →</span>
                </div>
                <div className="template-card-body">
                  <div className="template-field">
                    <span className="template-field-label">标题：</span>
                    <span className="template-field-value">{template.title}</span>
                  </div>
                  {template.description && (
                    <div className="template-field">
                      <span className="template-field-label">描述：</span>
                      <span className="template-field-value">{template.description}</span>
                    </div>
                  )}
                  <div className="template-field">
                    <span className="template-field-label">优先级：</span>
                    <span className="template-field-value">{priorityLabel(template.priority)}</span>
                  </div>
                  {template.category && (
                    <div className="template-field">
                      <span className="template-field-label">分类：</span>
                      <span
                        className="template-field-value template-category-badge"
                        style={{ backgroundColor: template.category.color + '33', color: template.category.color }}
                      >
                        {template.category.name}
                      </span>
                    </div>
                  )}
                  {template.tags && template.tags.length > 0 && (
                    <div className="template-field">
                      <span className="template-field-label">标签：</span>
                      <div className="template-tags-inline">
                        {template.tags.map((tag) => (
                          <span
                            key={tag.id}
                            className="template-tag-badge"
                            style={{ backgroundColor: tag.color + '33', color: tag.color }}
                          >
                            {tag.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {template.is_pinned && (
                    <div className="template-field">
                      <span className="template-field-value">📌 置顶</span>
                    </div>
                  )}
                  {template.repeat_pattern && template.repeat_pattern !== 'none' && (
                    <div className="template-field">
                      <span className="template-field-label">重复：</span>
                      <span className="template-field-value">
                        {REPEAT_OPTIONS.find(o => o.value === template.repeat_pattern)?.label || template.repeat_pattern}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default TemplateSelector;
