import React, { useState, useEffect, useRef } from 'react';
import { templateApi, categoryApi, tagApi } from '../services/api';

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

const REPEAT_OPTIONS = [
  { value: 'none', label: '不重复', icon: '' },
  { value: 'daily', label: '每天', icon: '🔁' },
  { value: 'weekly', label: '每周', icon: '📅' },
  { value: 'monthly', label: '每月', icon: '🗓️' },
  { value: 'yearly', label: '每年', icon: '📆' },
];

function TemplateManager({ onClose }) {
  const [templates, setTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [formName, setFormName] = useState('');
  const [formTitle, setFormTitle] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formCategoryId, setFormCategoryId] = useState('');
  const [formPriority, setFormPriority] = useState('medium');
  const [formIsPinned, setFormIsPinned] = useState(false);
  const [formRepeatPattern, setFormRepeatPattern] = useState('none');
  const [formTagIds, setFormTagIds] = useState([]);
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const abortRef = useRef(null);

  useEffect(() => {
    loadData();
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      const [templatesData, categoriesData, tagsData] = await Promise.all([
        templateApi.getAllTemplates(),
        categoryApi.getAllCategories(),
        tagApi.getAllTags(),
      ]);
      setTemplates(templatesData);
      setCategories(categoriesData);
      setTags(tagsData);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || '加载失败');
      }
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormName('');
    setFormTitle('');
    setFormDescription('');
    setFormCategoryId('');
    setFormPriority('medium');
    setFormIsPinned(false);
    setFormRepeatPattern('none');
    setFormTagIds([]);
    setFormError('');
  };

  const openCreate = () => {
    resetForm();
    setEditingTemplate(null);
    setIsCreating(true);
  };

  const openEdit = (template) => {
    setEditingTemplate(template);
    setIsCreating(true);
    setFormName(template.name);
    setFormTitle(template.title);
    setFormDescription(template.description || '');
    setFormCategoryId(template.category_id || '');
    setFormPriority(template.priority || 'medium');
    setFormIsPinned(template.is_pinned || false);
    setFormRepeatPattern(template.repeat_pattern || 'none');
    setFormTagIds((template.tags || []).map(t => t.id));
    setFormError('');
  };

  const closeForm = () => {
    setIsCreating(false);
    setEditingTemplate(null);
    resetForm();
  };

  const handleTagToggle = (tagId) => {
    setFormTagIds(prev =>
      prev.includes(tagId)
        ? prev.filter(id => id !== tagId)
        : [...prev, tagId]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formName.trim() || !formTitle.trim() || submitting) return;

    setSubmitting(true);
    setFormError('');
    try {
      const payload = {
        name: formName.trim(),
        title: formTitle.trim(),
        description: formDescription.trim() || null,
        category_id: formCategoryId ? Number(formCategoryId) : null,
        priority: formPriority,
        is_pinned: formIsPinned,
        repeat_pattern: formRepeatPattern,
        tag_ids: formTagIds,
      };

      let result;
      if (editingTemplate) {
        result = await templateApi.updateTemplate(editingTemplate.id, payload);
        setTemplates(prev => prev.map(t => t.id === result.id ? result : t));
      } else {
        result = await templateApi.createTemplate(payload);
        setTemplates(prev => [result, ...prev]);
      }
      closeForm();
    } catch (err) {
      setFormError(err.message || '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (templateId) => {
    if (!window.confirm('确定要删除这个模板吗？')) return;
    try {
      await templateApi.deleteTemplate(templateId);
      setTemplates(prev => prev.filter(t => t.id !== templateId));
    } catch (err) {
      setError(err.message || '删除失败');
    }
  };

  const priorityLabel = (p) => {
    if (p === 'high') return '🔴 高';
    if (p === 'low') return '🟢 低';
    return '🟡 中';
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content template-manager" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📋 任务模板管理</h2>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        {error && (
          <div style={{ padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', borderRadius: '6px', marginBottom: '12px', fontSize: '0.85rem' }}>
            ⚠️ {error}
          </div>
        )}

        <div className="template-manager-actions">
          {!isCreating && (
            <button type="button" className="btn-add-template" onClick={openCreate}>
              + 新建模板
            </button>
          )}
        </div>

        {isCreating && (
          <div className="template-form-container">
            <h3>{editingTemplate ? '编辑模板' : '新建模板'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="template-name">模板名称 *</label>
                <input
                  type="text"
                  id="template-name"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="例如：每周例会任务"
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label htmlFor="template-title">任务标题 *</label>
                <input
                  type="text"
                  id="template-title"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="任务的默认标题"
                />
              </div>
              <div className="form-group">
                <label htmlFor="template-description">任务描述</label>
                <textarea
                  id="template-description"
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="任务的默认描述"
                  rows="3"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="template-priority">优先级</label>
                  <select
                    id="template-priority"
                    value={formPriority}
                    onChange={(e) => setFormPriority(e.target.value)}
                  >
                    <option value="high">🔴 高优先级</option>
                    <option value="medium">🟡 中优先级</option>
                    <option value="low">🟢 低优先级</option>
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="template-repeat">重复</label>
                  <select
                    id="template-repeat"
                    value={formRepeatPattern}
                    onChange={(e) => setFormRepeatPattern(e.target.value)}
                  >
                    {REPEAT_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.icon} {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              {categories.length > 0 && (
                <div className="form-group">
                  <label htmlFor="template-category">分类</label>
                  <select
                    id="template-category"
                    value={formCategoryId}
                    onChange={(e) => setFormCategoryId(e.target.value)}
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
              <div className="form-group">
                <label className="pin-toggle-label">
                  <input
                    type="checkbox"
                    checked={formIsPinned}
                    onChange={(e) => setFormIsPinned(e.target.checked)}
                  />
                  <span className="pin-toggle-icon">📌</span>
                  <span className="pin-toggle-text">{formIsPinned ? '已置顶' : '置顶任务'}</span>
                </label>
              </div>
              <div className="form-group">
                <label>标签</label>
                {tags.length > 0 && (
                  <div className="tag-checkboxes">
                    {tags.map((tag) => (
                      <label
                        key={tag.id}
                        className={`tag-checkbox ${formTagIds.includes(tag.id) ? 'selected' : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={formTagIds.includes(tag.id)}
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
                )}
                {tags.length === 0 && (
                  <span style={{ color: '#6b7280', fontSize: '0.85rem' }}>暂无标签</span>
                )}
              </div>
              {formError && (
                <div style={{ marginTop: '8px', padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', borderRadius: '6px', fontSize: '0.85rem' }}>
                  ❌ {formError}
                </div>
              )}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeForm}>
                  取消
                </button>
                <button type="submit" className="btn-save" disabled={!formName.trim() || !formTitle.trim() || submitting}>
                  {submitting ? '保存中...' : (editingTemplate ? '保存修改' : '创建模板')}
                </button>
              </div>
            </form>
          </div>
        )}

        {!isCreating && (
          <div className="template-list-section">
            {loading ? (
              <div className="loading">加载中...</div>
            ) : templates.length === 0 ? (
              <div className="empty-state">
                <p>📝 暂无模板</p>
                <p style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '8px' }}>
                  点击上方"新建模板"按钮创建第一个模板
                </p>
              </div>
            ) : (
              <div className="template-list">
                {templates.map((template) => (
                  <div key={template.id} className="template-card">
                    <div className="template-card-header">
                      <h4>{template.name}</h4>
                      <div className="template-card-actions">
                        <button
                          type="button"
                          className="template-action-btn"
                          onClick={() => openEdit(template)}
                          title="编辑"
                        >
                          ✏️
                        </button>
                        <button
                          type="button"
                          className="template-action-btn delete"
                          onClick={() => handleDelete(template.id)}
                          title="删除"
                        >
                          🗑️
                        </button>
                      </div>
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
        )}
      </div>
    </div>
  );
}

export default TemplateManager;
