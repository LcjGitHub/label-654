import React, { useState, useEffect, useRef } from 'react';
import { commentApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

const AVATAR_COLORS = [
  '#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe',
  '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#ff9a9e',
];

function getAvatarColor(username) {
  if (!username) return AVATAR_COLORS[0];
  let hash = 0;
  for (let i = 0; i < username.length; i++) {
    hash = username.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function getAvatarInitial(username) {
  if (!username) return '?';
  return username.charAt(0).toUpperCase();
}

function formatCommentDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes} 分钟前`;
  if (hours < 24) return `${hours} 小时前`;
  if (days < 7) return `${days} 天前`;
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function renderContentWithMentions(content) {
  if (!content) return null;
  const parts = content.split(/(@[\u4e00-\u9fa5\w]+)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('@')) {
      return (
        <span key={idx} className="mention-tag">
          {part}
        </span>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}

function CommentItem({
  comment,
  onEdit,
  onDelete,
  onLike,
  onReply,
  onUpdateComment,
  currentUserId,
  depth = 0,
}) {
  const { user } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);
  const [editingError, setEditingError] = useState('');
  const textareaRef = useRef(null);

  const isOwner = currentUserId === comment.user_id;

  const handleStartEdit = () => {
    setEditContent(comment.content);
    setIsEditing(true);
    setEditingError('');
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditContent(comment.content);
    setEditingError('');
  };

  const handleSaveEdit = async () => {
    if (!editContent.trim()) {
      setEditingError('评论内容不能为空');
      return;
    }
    try {
      const updated = await commentApi.updateComment(comment.id, { content: editContent.trim() });
      onUpdateComment(updated);
      setIsEditing(false);
      setEditingError('');
    } catch (err) {
      setEditingError(err.message || '保存失败');
    }
  };

  const handleDelete = () => {
    if (window.confirm('确定要删除这条评论吗？')) {
      onDelete(comment.id);
    }
  };

  const handleLikeToggle = () => {
    onLike(comment.id, comment.is_liked);
  };

  const handleReply = () => {
    onReply(comment);
  };

  return (
    <div className={`comment-item ${depth > 0 ? 'nested' : ''}`} style={{ marginLeft: depth > 0 ? `${depth * 32}px` : 0 }}>
      <div className="comment-avatar" style={{ backgroundColor: getAvatarColor(comment.user?.username) }}>
        {getAvatarInitial(comment.user?.username)}
      </div>
      <div className="comment-body">
        <div className="comment-header">
          <span className="comment-username">{comment.user?.username || '未知用户'}</span>
          {comment.reply_user && (
            <span className="comment-reply-to">
              回复 <span className="mention-tag">@{comment.reply_user.username}</span>
            </span>
          )}
          <span className="comment-date">{formatCommentDate(comment.created_at)}</span>
          {comment.updated_at !== comment.created_at && (
            <span className="comment-edited">(已编辑)</span>
          )}
        </div>

        {isEditing ? (
          <div className="comment-edit-box">
            <textarea
              ref={textareaRef}
              className="comment-edit-textarea"
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={3}
              maxLength={2000}
            />
            {editingError && <div className="comment-error">{editingError}</div>}
            <div className="comment-edit-actions">
              <button className="btn-comment-save" onClick={handleSaveEdit}>保存</button>
              <button className="btn-comment-cancel" onClick={handleCancelEdit}>取消</button>
            </div>
          </div>
        ) : (
          <div className="comment-content">{renderContentWithMentions(comment.content)}</div>
        )}

        <div className="comment-actions">
          <button
            className={`comment-action-btn like-btn ${comment.is_liked ? 'liked' : ''}`}
            onClick={handleLikeToggle}
          >
            {comment.is_liked ? '❤️' : '🤍'} {comment.like_count > 0 && <span>{comment.like_count}</span>}
          </button>
          <button className="comment-action-btn" onClick={handleReply}>
            💬 回复
          </button>
          {isOwner && !isEditing && (
            <>
              <button className="comment-action-btn" onClick={handleStartEdit}>
                ✏️ 编辑
              </button>
              <button className="comment-action-btn delete-btn" onClick={handleDelete}>
                🗑️ 删除
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function CommentInput({
  taskId,
  onCommentCreated,
  replyTo,
  onCancelReply,
  placeholder = '写下你的评论...',
}) {
  const { user } = useAuth();
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showMentionList, setShowMentionList] = useState(false);
  const [mentionUsers, setMentionUsers] = useState([]);
  const [mentionSearch, setMentionSearch] = useState('');
  const [mentionStartIdx, setMentionStartIdx] = useState(-1);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (replyTo) {
      setContent(`@${replyTo.user?.username || ''} `);
      setTimeout(() => textareaRef.current?.focus(), 0);
    }
  }, [replyTo]);

  const loadMentionUsers = async () => {
    try {
      const users = await commentApi.getMentionUsers(taskId);
      setMentionUsers(users);
    } catch (err) {
      console.error('加载提及用户失败:', err);
    }
  };

  useEffect(() => {
    loadMentionUsers();
  }, [taskId]);

  const filteredUsers = mentionUsers.filter((u) =>
    u.username.toLowerCase().includes(mentionSearch.toLowerCase())
  ).filter((u) => u.id !== user?.id);

  const handleTextChange = (e) => {
    const value = e.target.value;
    setContent(value);

    const cursorPos = e.target.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPos);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');

    if (lastAtIndex !== -1) {
      const charBefore = lastAtIndex === 0 ? ' ' : textBeforeCursor[lastAtIndex - 1];
      if (charBefore === ' ' || charBefore === '\n' || lastAtIndex === 0) {
        const searchStr = textBeforeCursor.slice(lastAtIndex + 1);
        if (!searchStr.includes(' ')) {
          setMentionSearch(searchStr);
          setMentionStartIdx(lastAtIndex);
          setShowMentionList(true);
          return;
        }
      }
    }
    setShowMentionList(false);
  };

  const handleSelectMention = (mentionUser) => {
    if (textareaRef.current && mentionStartIdx !== -1) {
      const before = content.slice(0, mentionStartIdx);
      const after = content.slice(mentionStartIdx + mentionSearch.length + 1);
      const newValue = `${before}@${mentionUser.username} ${after}`;
      setContent(newValue);
      setShowMentionList(false);
      setMentionSearch('');
      setTimeout(() => {
        const pos = before.length + mentionUser.username.length + 2;
        textareaRef.current.focus();
        textareaRef.current.setSelectionRange(pos, pos);
      }, 0);
    }
  };

  const handleSubmit = async () => {
    if (!content.trim()) {
      setError('评论内容不能为空');
      return;
    }
    setIsSubmitting(true);
    setError('');
    try {
      const newComment = await commentApi.createTaskComment(taskId, {
        content: content.trim(),
        parent_id: replyTo?.id || null,
      });
      onCommentCreated(newComment);
      setContent('');
      if (onCancelReply) onCancelReply();
    } catch (err) {
      setError(err.message || '发布评论失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === 'Escape' && showMentionList) {
      setShowMentionList(false);
    }
  };

  return (
    <div className="comment-input-wrapper">
      {replyTo && (
        <div className="reply-indicator">
          <span>回复 <strong>@{replyTo.user?.username}</strong>：</span>
          <button className="btn-cancel-reply" onClick={onCancelReply}>✕</button>
        </div>
      )}
      <div className="comment-input-container">
        <div className="comment-avatar small" style={{ backgroundColor: getAvatarColor(user?.username) }}>
          {getAvatarInitial(user?.username)}
        </div>
        <div className="comment-input-main">
          <textarea
            ref={textareaRef}
            className="comment-input"
            placeholder={placeholder}
            value={content}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            rows={2}
            maxLength={2000}
          />
          {showMentionList && filteredUsers.length > 0 && (
            <div className="mention-dropdown">
              {filteredUsers.map((u) => (
                <div
                  key={u.id}
                  className="mention-dropdown-item"
                  onClick={() => handleSelectMention(u)}
                >
                  <span
                    className="mention-avatar"
                    style={{ backgroundColor: getAvatarColor(u.username) }}
                  >
                    {getAvatarInitial(u.username)}
                  </span>
                  <span className="mention-username">{u.username}</span>
                </div>
              ))}
            </div>
          )}
          {error && <div className="comment-error">{error}</div>}
          <div className="comment-input-footer">
            <span className="comment-hint">按 Ctrl/⌘ + Enter 发送，输入 @ 提及团队成员</span>
            <button
              className="btn-send-comment"
              onClick={handleSubmit}
              disabled={isSubmitting || !content.trim()}
            >
              {isSubmitting ? '发送中...' : '发送'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function TaskComments({ taskId }) {
  const { user } = useAuth();
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [replyTo, setReplyTo] = useState(null);

  const loadComments = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await commentApi.getTaskComments(taskId);
      setComments(data);
    } catch (err) {
      setError(err.message || '加载评论失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (taskId) {
      loadComments();
    }
  }, [taskId]);

  const handleCommentCreated = (newComment) => {
    setComments((prev) => [...prev, newComment]);
  };

  const handleUpdateComment = (updated) => {
    setComments((prev) =>
      prev.map((c) => (c.id === updated.id ? updated : c))
    );
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await commentApi.deleteComment(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId && c.parent_id !== commentId));
    } catch (err) {
      setError(err.message || '删除评论失败');
    }
  };

  const handleLikeComment = async (commentId, isLiked) => {
    try {
      const result = isLiked
        ? await commentApi.unlikeComment(commentId)
        : await commentApi.likeComment(commentId);
      setComments((prev) =>
        prev.map((c) =>
          c.id === commentId
            ? { ...c, like_count: result.like_count, is_liked: result.is_liked }
            : c
        )
      );
    } catch (err) {
      console.error('点赞操作失败:', err);
    }
  };

  const handleReply = (comment) => {
    setReplyTo(comment);
  };

  const handleCancelReply = () => {
    setReplyTo(null);
  };

  const buildCommentTree = (flatComments) => {
    const map = {};
    const roots = [];
    flatComments.forEach((c) => {
      map[c.id] = { ...c, children: [] };
    });
    flatComments.forEach((c) => {
      if (c.parent_id && map[c.parent_id]) {
        map[c.parent_id].children.push(map[c.id]);
      } else {
        roots.push(map[c.id]);
      }
    });
    return roots;
  };

  const renderCommentTree = (commentList, depth = 0) => {
    return commentList.map((comment) => (
      <div key={comment.id}>
        <CommentItem
          comment={comment}
          onEdit={() => {}}
          onDelete={handleDeleteComment}
          onLike={handleLikeComment}
          onReply={handleReply}
          onUpdateComment={handleUpdateComment}
          currentUserId={user?.id}
          depth={depth}
        />
        {comment.children && comment.children.length > 0 && (
          renderCommentTree(comment.children, depth + 1)
        )}
      </div>
    ));
  };

  const commentTree = buildCommentTree(comments);

  return (
    <div className="task-comments">
      <div className="comments-header">
        <h4>💬 评论讨论 ({comments.length})</h4>
      </div>

      {error && <div className="comment-error">{error}</div>}

      <CommentInput
        taskId={taskId}
        onCommentCreated={handleCommentCreated}
        replyTo={replyTo}
        onCancelReply={handleCancelReply}
      />

      <div className="comments-list">
        {loading ? (
          <div className="comments-loading">加载评论中...</div>
        ) : commentTree.length === 0 ? (
          <div className="comments-empty">暂无评论，快来发表第一条评论吧！</div>
        ) : (
          renderCommentTree(commentTree)
        )}
      </div>
    </div>
  );
}

export default TaskComments;
