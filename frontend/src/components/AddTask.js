import React, { useState, useRef } from 'react';
import { attachmentApi } from '../services/api';

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

function AddTask({ onAdd, categories, tags, onCreateTag }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [priority, setPriority] = useState('medium');
  const [dueDate, setDueDate] = useState('');
  const [isPinned, setIsPinned] = useState(false);
  const [repeatPattern, setRepeatPattern] = useState('none');
  const [selectedTagIds, setSelectedTagIds] = useState([]);
  const [showNewTagForm, setShowNewTagForm] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [newTagColor, setNewTagColor] = useState(PRESET_COLORS[0]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCreatingTag, setIsCreatingTag] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef(null);

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setCategoryId('');
    setPriority('medium');
    setDueDate('');
    setIsPinned(false);
    setRepeatPattern('none');
    setSelectedTagIds([]);
    setShowNewTagForm(false);
    setNewTagName('');
    setNewTagColor(PRESET_COLORS[0]);
    setSelectedFiles([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const removeSelectedFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFilesForTask = async (taskId) => {
    for (const file of selectedFiles) {
      try {
        await attachmentApi.uploadAttachment(taskId, file);
      } catch (err) {
        console.error('上传附件失败:', err);
      }
    }
  };

  const handleTagToggle = (tagId) => {
    setSelectedTagIds(prev =>
      prev.includes(tagId)
        ? prev.filter(id => id !== tagId)
        : [...prev, tagId]
    );
  };

  const handleCreateTag = async () => {
    if (!newTagName.trim() || isCreatingTag) return;

    setIsCreatingTag(true);
    try {
      const newTag = await onCreateTag({
        name: newTagName.trim(),
        color: newTagColor,
      });
      setSelectedTagIds(prev => [...prev, newTag.id]);
      setNewTagName('');
      setNewTagColor(PRESET_COLORS[0]);
      setShowNewTagForm(false);
    } catch (err) {
    } finally {
      setIsCreatingTag(false);
    }
  };

  const handleCreateTagKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      e.stopPropagation();
      handleCreateTag();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || isSubmitting) return;
    
    setIsSubmitting(true);
    try {
      const createdTask = await onAdd({
        title: title.trim(),
        description: description.trim(),
        category_id: categoryId ? Number(categoryId) : null,
        priority: priority,
        due_date: dueDate || null,
        is_pinned: isPinned,
        repeat_pattern: repeatPattern,
        tag_ids: selectedTagIds,
      }, selectedFiles);
      
      resetForm();
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
          <div className="task-repeat-select">
            <label htmlFor="repeat-pattern">重复：</label>
            <select
              id="repeat-pattern"
              value={repeatPattern}
              onChange={(e) => setRepeatPattern(e.target.value)}
            >
              {REPEAT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.icon} {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="task-pin-select">
            <label className="pin-toggle-label">
              <input
                type="checkbox"
                checked={isPinned}
                onChange={(e) => setIsPinned(e.target.checked)}
              />
              <span className="pin-toggle-icon">📌</span>
              <span className="pin-toggle-text">{isPinned ? '已置顶' : '置顶任务'}</span>
            </label>
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

          <div className="task-tags-select">
            <label>选择标签：</label>
            {tags.length > 0 && (
              <div className="tag-checkboxes">
                {tags.map((tag) => (
                  <label
                    key={tag.id}
                    className={`tag-checkbox ${selectedTagIds.includes(tag.id) ? 'selected' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedTagIds.includes(tag.id)}
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
            {!showNewTagForm ? (
              <button
                type="button"
                className="btn-add-inline-tag"
                onClick={() => setShowNewTagForm(true)}
              >
                + 创建新标签
              </button>
            ) : (
              <div className="inline-tag-form">
                <input
                  type="text"
                  placeholder="新标签名称"
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                  onKeyDown={handleCreateTagKeyDown}
                  autoFocus
                />
                <div className="color-options">
                  {PRESET_COLORS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      className={`color-option ${newTagColor === c ? 'selected' : ''}`}
                      style={{ backgroundColor: c }}
                      onClick={() => setNewTagColor(c)}
                    />
                  ))}
                </div>
                <div className="inline-tag-actions">
                  <button
                    type="button"
                    className="btn-cancel-inline"
                    onClick={() => {
                      setShowNewTagForm(false);
                      setNewTagName('');
                      setNewTagColor(PRESET_COLORS[0]);
                    }}
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    className="btn-add-inline"
                    disabled={!newTagName.trim() || isCreatingTag}
                    onClick={handleCreateTag}
                  >
                    {isCreatingTag ? '创建中...' : '创建'}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="task-attachments-upload">
            <label>附件：</label>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={handleFileSelect}
              style={{ display: 'none' }}
              accept=".png,.jpg,.jpeg,.gif,.bmp,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.rar,.md"
            />
            <button
              type="button"
              className="btn-upload-attachments"
              onClick={() => fileInputRef.current?.click()}
            >
              📎 选择文件
            </button>
            {selectedFiles.length > 0 && (
              <div className="selected-files-list">
                {selectedFiles.map((file, index) => (
                  <div key={index} className="selected-file-item">
                    <span className="file-icon">📄</span>
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{formatFileSize(file.size)}</span>
                    <button
                      type="button"
                      className="remove-file-btn"
                      onClick={() => removeSelectedFile(index)}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="add-task-actions">
            <button type="button" className="btn-cancel" onClick={() => { resetForm(); setIsExpanded(false); }}>
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
