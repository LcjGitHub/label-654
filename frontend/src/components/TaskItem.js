import React, { useState, useRef } from 'react';
import { attachmentApi } from '../services/api';

const REPEAT_OPTIONS = [
  { value: 'none', label: '不重复', icon: '' },
  { value: 'daily', label: '每天', icon: '🔁' },
  { value: 'weekly', label: '每周', icon: '📅' },
  { value: 'monthly', label: '每月', icon: '🗓️' },
  { value: 'yearly', label: '每年', icon: '📆' },
];

const REPEAT_ICONS = {
  daily: '🔁',
  weekly: '📅',
  monthly: '🗓️',
  yearly: '📆',
};

const REPEAT_LABELS = {
  daily: '每天',
  weekly: '每周',
  monthly: '每月',
  yearly: '每年',
};

const FILE_ICONS = {
  png: '🖼️',
  jpg: '🖼️',
  jpeg: '🖼️',
  gif: '🖼️',
  bmp: '🖼️',
  webp: '🖼️',
  pdf: '📕',
  doc: '📘',
  docx: '📘',
  xls: '📗',
  xlsx: '📗',
  ppt: '📙',
  pptx: '📙',
  txt: '📄',
  csv: '📊',
  zip: '📦',
  rar: '📦',
  md: '📝',
};

function formatForDatetimeLocal(dateStr) {
  if (!dateStr) return '';
  const normalized = dateStr.replace(' ', 'T');
  return normalized.slice(0, 16);
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  return FILE_ICONS[ext] || '📄';
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function TaskItem({ task, onToggle, onTogglePin, onDelete, onUpdate, categories, tags, onAddTagToTask, onRemoveTagFromTask, onUploadAttachment, onDeleteAttachment }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editDescription, setEditDescription] = useState(task.description);
  const [editCategoryId, setEditCategoryId] = useState(task.category_id || '');
  const [editPriority, setEditPriority] = useState(task.priority || 'medium');
  const [editDueDate, setEditDueDate] = useState(formatForDatetimeLocal(task.due_date));
  const [editRepeatPattern, setEditRepeatPattern] = useState(task.repeat_pattern || 'none');
  const [editTagIds, setEditTagIds] = useState((task.tags || []).map(t => t.id));
  const [pendingFiles, setPendingFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleTagToggle = (tagId) => {
    setEditTagIds(prev =>
      prev.includes(tagId)
        ? prev.filter(id => id !== tagId)
        : [...prev, tagId]
    );
  };

  const handleEditFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setPendingFiles(prev => [...prev, ...files]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removePendingFile = (index) => {
    setPendingFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadPendingFiles = async () => {
    if (pendingFiles.length === 0) return;
    setUploading(true);
    try {
      for (const file of pendingFiles) {
        try {
          await onUploadAttachment(task.id, file);
        } catch (err) {
          console.error('上传附件失败:', err);
        }
      }
      setPendingFiles([]);
    } finally {
      setUploading(false);
    }
  };

  const handleSave = async () => {
    if (!editTitle.trim()) return;
    try {
      await onUpdate(task.id, {
        title: editTitle.trim(),
        description: editDescription.trim(),
        category_id: editCategoryId ? Number(editCategoryId) : null,
        priority: editPriority,
        due_date: editDueDate || null,
        repeat_pattern: editRepeatPattern,
      });

      const currentTagIds = (task.tags || []).map(t => t.id);
      const tagsToAdd = editTagIds.filter(id => !currentTagIds.includes(id));
      const tagsToRemove = currentTagIds.filter(id => !editTagIds.includes(id));

      for (const tagId of tagsToAdd) {
        await onAddTagToTask(task.id, tagId);
      }
      for (const tagId of tagsToRemove) {
        await onRemoveTagFromTask(task.id, tagId);
      }

      await uploadPendingFiles();
    } catch (err) {
    }
    setIsEditing(false);
    setPendingFiles([]);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    }
    if (e.key === 'Escape') {
      setIsEditing(false);
      setEditTitle(task.title);
      setEditDescription(task.description);
      setEditCategoryId(task.category_id || '');
      setEditPriority(task.priority || 'medium');
      setEditDueDate(formatForDatetimeLocal(task.due_date));
      setEditRepeatPattern(task.repeat_pattern || 'none');
      setEditTagIds((task.tags || []).map(t => t.id));
      setPendingFiles([]);
    }
  };

  const isOverdue = () => {
    if (!task.due_date || task.completed) return false;
    return new Date(task.due_date) < new Date();
  };

  const getPriorityLabel = (priority) => {
    switch (priority) {
      case 'high': return '高';
      case 'low': return '低';
      default: return '中';
    }
  };

  const handlePreviewAttachment = (attachment) => {
    const url = attachmentApi.getAttachmentUrl(attachment.id);
    window.open(url, '_blank');
  };

  const handleDownloadAttachment = (attachment) => {
    const url = attachmentApi.getAttachmentDownloadUrl(attachment.id);
    const a = document.createElement('a');
    a.href = url;
    a.download = attachment.original_filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleDeleteAttachmentClick = async (attachmentId) => {
    if (window.confirm('确定要删除这个附件吗？')) {
      try {
        await onDeleteAttachment(task.id, attachmentId);
      } catch (err) {
      }
    }
  };

  const isImageFile = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    return ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(ext);
  };

  if (isEditing) {
    return (
      <div className="task-item editing">
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
          className="edit-input"
        />
        <textarea
          value={editDescription}
          onChange={(e) => setEditDescription(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="添加描述..."
          className="edit-textarea"
        />
        <div className="task-priority-select">
          <label htmlFor={`edit-priority-${task.id}`}>优先级：</label>
          <select
            id={`edit-priority-${task.id}`}
            value={editPriority}
            onChange={(e) => setEditPriority(e.target.value)}
          >
            <option value="high">🔴 高优先级</option>
            <option value="medium">🟡 中优先级</option>
            <option value="low">🟢 低优先级</option>
          </select>
        </div>
        <div className="task-due-date">
          <label htmlFor={`edit-due-date-${task.id}`}>截止日期：</label>
          <input
            type="datetime-local"
            id={`edit-due-date-${task.id}`}
            value={editDueDate}
            onChange={(e) => setEditDueDate(e.target.value)}
          />
        </div>
        <div className="task-repeat-select">
          <label htmlFor={`edit-repeat-${task.id}`}>重复：</label>
          <select
            id={`edit-repeat-${task.id}`}
            value={editRepeatPattern}
            onChange={(e) => setEditRepeatPattern(e.target.value)}
          >
            {REPEAT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.icon} {opt.label}
              </option>
            ))}
          </select>
        </div>
        {categories.length > 0 && (
          <div className="task-category-select">
            <label htmlFor={`edit-category-${task.id}`}>选择分类：</label>
            <select
              id={`edit-category-${task.id}`}
              value={editCategoryId}
              onChange={(e) => setEditCategoryId(e.target.value)}
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

        {tags.length > 0 && (
          <div className="task-tags-select">
            <label>选择标签：</label>
            <div className="tag-checkboxes">
              {tags.map((tag) => (
                <label
                  key={tag.id}
                  className={`tag-checkbox ${editTagIds.includes(tag.id) ? 'selected' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={editTagIds.includes(tag.id)}
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
          </div>
        )}

        <div className="task-attachments-upload">
          <label>附件：</label>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleEditFileSelect}
            style={{ display: 'none' }}
            accept=".png,.jpg,.jpeg,.gif,.bmp,.webp,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.rar,.md"
          />
          <button
            type="button"
            className="btn-upload-attachments"
            onClick={() => fileInputRef.current?.click()}
          >
            📎 添加附件
          </button>
          {task.attachments && task.attachments.length > 0 && (
            <div className="attachments-list">
              {task.attachments.map((att) => (
                <div key={att.id} className="attachment-item">
                  <span className="attachment-icon">{getFileIcon(att.original_filename)}</span>
                  <span className="attachment-name" title={att.original_filename}>{att.original_filename}</span>
                  <span className="attachment-size">{formatFileSize(att.file_size)}</span>
                  <button
                    type="button"
                    className="attachment-action-btn"
                    onClick={() => handlePreviewAttachment(att)}
                    title="预览"
                  >
                    👁️
                  </button>
                  <button
                    type="button"
                    className="attachment-action-btn"
                    onClick={() => handleDownloadAttachment(att)}
                    title="下载"
                  >
                    ⬇️
                  </button>
                  <button
                    type="button"
                    className="attachment-action-btn remove"
                    onClick={() => handleDeleteAttachmentClick(att.id)}
                    title="删除"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
          {pendingFiles.length > 0 && (
            <div className="attachments-list pending">
              <div className="pending-attachments-title">待上传：</div>
              {pendingFiles.map((file, index) => (
                <div key={index} className="attachment-item pending">
                  <span className="attachment-icon">{getFileIcon(file.name)}</span>
                  <span className="attachment-name" title={file.name}>{file.name}</span>
                  <span className="attachment-size">{formatFileSize(file.size)}</span>
                  <button
                    type="button"
                    className="attachment-action-btn remove"
                    onClick={() => removePendingFile(index)}
                    title="移除"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="edit-actions">
          <button className="btn-save" onClick={handleSave} disabled={uploading}>
            {uploading ? '上传中...' : '保存'}
          </button>
          <button
            className="btn-cancel-edit"
            onClick={() => {
              setIsEditing(false);
              setEditTitle(task.title);
              setEditDescription(task.description);
              setEditCategoryId(task.category_id || '');
              setEditPriority(task.priority || 'medium');
              setEditDueDate(formatForDatetimeLocal(task.due_date));
              setEditRepeatPattern(task.repeat_pattern || 'none');
              setEditTagIds((task.tags || []).map(t => t.id));
              setPendingFiles([]);
            }}
          >
            取消
          </button>
        </div>
      </div>
    );
  }

  const overdue = isOverdue();
  const hasAttachments = task.attachments && task.attachments.length > 0;

  return (
    <div className={`task-item ${task.completed ? 'completed' : ''} ${overdue ? 'overdue' : ''} ${task.is_pinned ? 'pinned' : ''}`}>
      <div className="task-header">
        <label className="task-checkbox">
          <input
            type="checkbox"
            checked={task.completed}
            onChange={() => onToggle(task.id)}
            aria-label={`标记任务"${task.title}"为${task.completed ? '未完成' : '已完成'}`}
          />
          <span className={`checkbox ${task.completed ? 'checked' : ''}`}>
            {task.completed && <span className="checkmark">✓</span>}
          </span>
        </label>
        <div className="task-content" onDoubleClick={() => setIsEditing(true)}>
          <h3 className={task.completed ? 'completed-text' : ''}>
            {task.is_pinned && (
              <span className="pin-indicator" title="已置顶">📌</span>
            )}
            <span className={`task-priority-badge priority-${task.priority || 'medium'}`}>
              {getPriorityLabel(task.priority)}
            </span>
            {task.category && (
              <span
                className="task-category-badge"
                style={{ backgroundColor: task.category.color }}
                title={task.category.name}
              />
            )}
            {task.tags && task.tags.length > 0 && (
              <span className="task-tag-dots">
                {task.tags.map((tag) => (
                  <span
                    key={tag.id}
                    className="task-tag-dot"
                    style={{ backgroundColor: tag.color }}
                    title={tag.name}
                  />
                ))}
              </span>
            )}
            {task.repeat_pattern && task.repeat_pattern !== 'none' && (
              <span className="repeat-indicator" title={`重复：${REPEAT_LABELS[task.repeat_pattern]}`}>
                {REPEAT_ICONS[task.repeat_pattern]}
              </span>
            )}
            {hasAttachments && (
              <span className="attachment-indicator" title={`包含 ${task.attachments.length} 个附件`}>
                📎
              </span>
            )}
            {task.title}
          </h3>
          {task.description && (
            <p className={task.completed ? 'completed-text' : ''}>{task.description}</p>
          )}
          <div className="task-meta">
            <span className="task-date">{formatDate(task.created_at)}</span>
            {task.due_date && (
              <span className={`task-due-date-tag ${overdue ? 'overdue' : ''}`}>
                📅 {formatDate(task.due_date)}
                {overdue && ' (已过期)'}
              </span>
            )}
            {task.repeat_pattern && task.repeat_pattern !== 'none' && (
              <span className="task-repeat-tag">
                {REPEAT_ICONS[task.repeat_pattern]} {REPEAT_LABELS[task.repeat_pattern]}
              </span>
            )}
            {task.category && (
              <span
                className="task-category-tag"
                style={{
                  backgroundColor: task.category.color + '20',
                  color: task.category.color,
                  borderColor: task.category.color,
                }}
              >
                {task.category.name}
              </span>
            )}
          </div>
          {hasAttachments && (
            <div className="task-attachments-preview">
              {task.attachments.map((att) => (
                <div
                  key={att.id}
                  className="attachment-preview-item"
                  onClick={() => handlePreviewAttachment(att)}
                  title={`点击预览：${att.original_filename}`}
                >
                  {isImageFile(att.original_filename) ? (
                    <img
                      src={attachmentApi.getAttachmentUrl(att.id)}
                      alt={att.original_filename}
                      className="attachment-thumbnail"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                  ) : null}
                  <div className={`attachment-placeholder ${isImageFile(att.original_filename) ? 'hidden' : ''}`}>
                    <span className="attachment-preview-icon">{getFileIcon(att.original_filename)}</span>
                  </div>
                  <div className="attachment-preview-info">
                    <span className="attachment-preview-name" title={att.original_filename}>
                      {att.original_filename}
                    </span>
                    <span className="attachment-preview-size">{formatFileSize(att.file_size)}</span>
                  </div>
                  <button
                    className="attachment-download-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDownloadAttachment(att);
                    }}
                    title="下载"
                  >
                    ⬇️
                  </button>
                  <button
                    className="attachment-delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteAttachmentClick(att.id);
                    }}
                    title="删除附件"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="task-actions">
        <button
          className={`btn-pin ${task.is_pinned ? 'pinned' : ''}`}
          onClick={() => onTogglePin(task.id)}
          title={task.is_pinned ? '取消置顶' : '置顶'}
        >
          📌
        </button>
        <button className="btn-edit" onClick={() => setIsEditing(true)}>
          编辑
        </button>
        <button className="btn-delete" onClick={() => onDelete(task.id)}>
          删除
        </button>
      </div>
    </div>
  );
}

export default TaskItem;
