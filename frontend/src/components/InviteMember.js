import React, { useState } from 'react';
import { teamApi } from '../services/api';

function InviteMember({ teamId, onClose, onSuccess }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [invitationSent, setInvitationSent] = useState(false);
  const [inviteToken, setInviteToken] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;

    try {
      setLoading(true);
      setError('');
      const result = await teamApi.inviteMember(teamId, { email: email.trim() });
      setInviteToken(result.token);
      setInvitationSent(true);
      if (onSuccess) {
        setTimeout(() => onSuccess(), 2000);
      }
    } catch (err) {
      setError(err.message || '发送邀请失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="invite-member-form">
      {!invitationSent ? (
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>输入成员邮箱：</label>
            <input
              type="email"
              placeholder="example@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
            />
          </div>
          {error && (
            <div className="error-message" style={{ margin: '8px 0', padding: '6px 10px' }}>
              ⚠️ {error}
            </div>
          )}
          <div className="form-actions">
            <button
              type="button"
              className="btn-cancel btn-small"
              onClick={onClose}
            >
              取消
            </button>
            <button
              type="submit"
              className="btn-primary btn-small"
              disabled={!email.trim() || loading}
            >
              {loading ? '发送中...' : '发送邀请'}
            </button>
          </div>
        </form>
      ) : (
        <div className="invitation-success">
          <div className="success-icon">✉️</div>
          <h4>邀请已发送！</h4>
          <p>邀请邮件已发送至 {email}</p>
          <p className="invite-hint">
            您也可以将以下邀请链接分享给对方：
          </p>
          <div className="share-link-box small">
            <span className="share-link">
              {window.location.origin}/accept/{inviteToken}
            </span>
            <button
              type="button"
              className="btn-secondary btn-small"
              onClick={() => {
                navigator.clipboard.writeText(
                  `${window.location.origin}/accept/${inviteToken}`
                );
              }}
            >
              📋 复制
            </button>
          </div>
          <button
            type="button"
            className="btn-primary btn-small"
            onClick={() => {
              setInvitationSent(false);
              setEmail('');
              setInviteToken('');
            }}
            style={{ marginTop: '12px' }}
          >
            继续邀请
          </button>
        </div>
      )}
    </div>
  );
}

export default InviteMember;
