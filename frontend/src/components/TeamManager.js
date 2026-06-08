import React, { useState, useEffect } from 'react';
import { teamApi } from '../services/api';
import InviteMember from './InviteMember';
import { useAuth } from '../context/AuthContext';

function TeamManager({ onClose }) {
  const { user } = useAuth();
  const userId = user?.id;
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [teamMembers, setTeamMembers] = useState([]);
  const [teamUsers, setTeamUsers] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamDesc, setNewTeamDesc] = useState('');
  const [editingTeam, setEditingTeam] = useState(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copiedToken, setCopiedToken] = useState(false);

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    try {
      setLoading(true);
      const data = await teamApi.getAllTeams();
      setTeams(data);
    } catch (err) {
      setError(err.message || '加载团队列表失败');
    } finally {
      setLoading(false);
    }
  };

  const loadTeamDetails = async (team) => {
    try {
      setLoading(true);
      const [members, users] = await Promise.all([
        teamApi.getTeamMembers(team.id),
        teamApi.getTeamUsers(team.id),
      ]);
      setTeamMembers(members);
      setTeamUsers(users);
      setSelectedTeam(team);
    } catch (err) {
      setError(err.message || '加载团队详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!newTeamName.trim()) return;

    try {
      setLoading(true);
      setError('');
      const newTeam = await teamApi.createTeam({
        name: newTeamName.trim(),
        description: newTeamDesc.trim() || undefined,
      });
      setTeams(prev => [newTeam, ...prev]);
      setNewTeamName('');
      setNewTeamDesc('');
      setShowCreateForm(false);
    } catch (err) {
      setError(err.message || '创建团队失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateTeam = async (e) => {
    e.preventDefault();
    if (!editingTeam || !editName.trim()) return;

    try {
      setLoading(true);
      setError('');
      const updated = await teamApi.updateTeam(editingTeam.id, {
        name: editName.trim(),
        description: editDesc.trim(),
      });
      setTeams(prev => prev.map(t => t.id === updated.id ? updated : t));
      setSelectedTeam(updated);
      setEditingTeam(null);
    } catch (err) {
      setError(err.message || '更新团队失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTeam = async (teamId) => {
    if (!window.confirm('确定要删除这个团队吗？此操作不可撤销。')) return;

    try {
      setLoading(true);
      setError('');
      await teamApi.deleteTeam(teamId);
      setTeams(prev => prev.filter(t => t.id !== teamId));
      if (selectedTeam && selectedTeam.id === teamId) {
        setSelectedTeam(null);
        setTeamMembers([]);
      }
    } catch (err) {
      setError(err.message || '删除团队失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (memberUserId, newRole) => {
    if (!selectedTeam) return;

    try {
      setLoading(true);
      setError('');
      const updated = await teamApi.updateMemberRole(selectedTeam.id, memberUserId, newRole);
      setTeamMembers(prev => prev.map(m => m.user_id === memberUserId ? updated : m));
      setTeamUsers(prev => prev.map(u => u.id === memberUserId ? { ...u, role: newRole } : u));
    } catch (err) {
      setError(err.message || '更新角色失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveMember = async (memberUserId) => {
    if (!selectedTeam) return;
    const isSelf = memberUserId === userId;
    const msg = isSelf
      ? '确定要退出这个团队吗？'
      : '确定要移除这个成员吗？';
    if (!window.confirm(msg)) return;

    try {
      setLoading(true);
      setError('');
      await teamApi.removeTeamMember(selectedTeam.id, memberUserId);
      setTeamMembers(prev => prev.filter(m => m.user_id !== memberUserId));
      setTeamUsers(prev => prev.filter(u => u.id !== memberUserId));
      if (isSelf) {
        setTeams(prev => prev.filter(t => t.id !== selectedTeam.id));
        setSelectedTeam(null);
      } else {
        setSelectedTeam(prev => prev ? { ...prev, member_count: prev.member_count - 1 } : null);
      }
    } catch (err) {
      setError(err.message || '移除成员失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateToken = async () => {
    if (!selectedTeam) return;
    if (!window.confirm('重新生成邀请链接将使旧链接失效，确定继续吗？')) return;

    try {
      setLoading(true);
      setError('');
      const updated = await teamApi.regenerateInviteToken(selectedTeam.id);
      setSelectedTeam(updated);
      setTeams(prev => prev.map(t => t.id === updated.id ? updated : t));
    } catch (err) {
      setError(err.message || '重新生成邀请链接失败');
    } finally {
      setLoading(false);
    }
  };

  const copyInviteLink = () => {
    if (!selectedTeam) return;
    const link = `${window.location.origin}/#/invite/${selectedTeam.invite_token}`;
    navigator.clipboard.writeText(link).then(() => {
      setCopiedToken(true);
      setTimeout(() => setCopiedToken(false), 2000);
    });
  };

  const isCurrentUserAdmin = teamUsers.find(u => u.id === userId)?.role === 'admin';

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🏢 团队管理</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {error && (
          <div className="error-message" style={{ margin: '12px 16px' }}>
            ⚠️ {error}
          </div>
        )}

        <div className="modal-body">
          <div className="team-manager">
            <div className="team-sidebar">
              <h3>我的团队</h3>
              {!showCreateForm && (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setShowCreateForm(true)}
                  style={{ marginBottom: '12px' }}
                >
                  + 创建团队
                </button>
              )}

              {showCreateForm && (
                <form className="create-team-form" onSubmit={handleCreateTeam}>
                  <h4>创建新团队</h4>
                  <input
                    type="text"
                    placeholder="团队名称"
                    value={newTeamName}
                    onChange={(e) => setNewTeamName(e.target.value)}
                    autoFocus
                    style={{ marginBottom: '8px', width: '100%' }}
                  />
                  <textarea
                    placeholder="团队描述（可选）"
                    value={newTeamDesc}
                    onChange={(e) => setNewTeamDesc(e.target.value)}
                    rows={2}
                    style={{ marginBottom: '8px', width: '100%' }}
                  />
                  <div className="form-actions" style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => {
                        setShowCreateForm(false);
                        setNewTeamName('');
                        setNewTeamDesc('');
                      }}
                    >
                      取消
                    </button>
                    <button
                      type="submit"
                      className="btn-primary"
                      disabled={!newTeamName.trim() || loading}
                    >
                      {loading ? '创建中...' : '创建'}
                    </button>
                  </div>
                </form>
              )}

              <div className="team-list">
                {loading && teams.length === 0 ? (
                  <div className="loading">加载中...</div>
                ) : teams.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">🏢</div>
                    <div className="empty-state-text">还没有团队，点击上方按钮创建</div>
                  </div>
                ) : (
                  teams.map(team => (
                    <div
                      key={team.id}
                      className={`team-item ${selectedTeam?.id === team.id ? 'active' : ''}`}
                      onClick={() => loadTeamDetails(team)}
                    >
                      <div className="team-item-name">👥 {team.name}</div>
                      {team.description && (
                        <div className="team-item-desc">{team.description}</div>
                      )}
                      <div className="team-item-count">{team.member_count} 位成员</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="team-content">
              {!selectedTeam ? (
                <div className="empty-state">
                  <div className="empty-state-icon">👈</div>
                  <div className="empty-state-text">请选择一个团队查看详情</div>
                </div>
              ) : (
                <>
                  <div className="team-detail-header">
                    {editingTeam ? (
                      <form onSubmit={handleUpdateTeam} style={{ flex: 1 }}>
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          autoFocus
                          style={{ marginBottom: '8px', width: '100%' }}
                        />
                        <textarea
                          value={editDesc}
                          onChange={(e) => setEditDesc(e.target.value)}
                          placeholder="团队描述"
                          rows={2}
                          style={{ marginBottom: '8px', width: '100%' }}
                        />
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => setEditingTeam(null)}
                          >
                            取消
                          </button>
                          <button
                            type="submit"
                            className="btn-primary"
                            disabled={!editName.trim() || loading}
                          >
                            保存
                          </button>
                        </div>
                      </form>
                    ) : (
                      <>
                        <div className="team-detail-title">
                          <h2>{selectedTeam.name}</h2>
                          {selectedTeam.description && <p>{selectedTeam.description}</p>}
                        </div>
                        {isCurrentUserAdmin && (
                          <div className="team-actions">
                            <button
                              type="button"
                              className="btn-secondary"
                              onClick={() => {
                                setEditingTeam(selectedTeam);
                                setEditName(selectedTeam.name);
                                setEditDesc(selectedTeam.description || '');
                              }}
                            >
                              ✏️ 编辑
                            </button>
                            <button
                              type="button"
                              className="btn-danger"
                              onClick={() => handleDeleteTeam(selectedTeam.id)}
                            >
                              🗑️ 删除
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {isCurrentUserAdmin && !editingTeam && (
                    <div className="team-section invite-section">
                      <div className="team-section-title">
                        <h3>📨 邀请成员</h3>
                      </div>
                      {!showInviteForm ? (
                        <>
                          <div className="invite-form">
                            <button
                              type="button"
                              className="btn-primary"
                              onClick={() => setShowInviteForm(true)}
                            >
                              📧 通过邮箱邀请
                            </button>
                          </div>
                          <div className="invite-link">
                            <span className="invite-link-url">
                              {window.location.origin}/#/invite/{selectedTeam.invite_token}
                            </span>
                            <button
                              type="button"
                              className="btn-secondary"
                              onClick={copyInviteLink}
                            >
                              {copiedToken ? '✓ 已复制' : '📋 复制'}
                            </button>
                            <button
                              type="button"
                              className="btn-secondary"
                              onClick={handleRegenerateToken}
                            >
                              🔄 重新生成
                            </button>
                          </div>
                        </>
                      ) : (
                        <InviteMember
                          teamId={selectedTeam.id}
                          onClose={() => setShowInviteForm(false)}
                          onSuccess={() => {
                            setShowInviteForm(false);
                            loadTeamDetails(selectedTeam);
                          }}
                        />
                      )}
                    </div>
                  )}

                  <div className="team-section">
                    <div className="team-section-title">
                      <h3>👥 团队成员 ({teamUsers.length})</h3>
                    </div>
                    <div className="member-list">
                      {teamUsers.map(memberUser => (
                        <div key={memberUser.id} className="member-item">
                          <div className="member-avatar">
                            {memberUser.username.charAt(0).toUpperCase()}
                          </div>
                          <div className="member-info">
                            <div className="member-name">
                              {memberUser.username}
                              <span className={`role-badge ${memberUser.role}`}>
                                {memberUser.role === 'admin' ? '管理员' : '成员'}
                              </span>
                            </div>
                            <div className="member-joined">
                              加入于 {new Date(teamMembers.find(m => m.user_id === memberUser.id)?.joined_at || '').toLocaleDateString('zh-CN')}
                            </div>
                          </div>
                          {isCurrentUserAdmin && memberUser.id !== userId && (
                            <select
                              value={memberUser.role}
                              onChange={(e) => handleRoleChange(memberUser.id, e.target.value)}
                              className="member-role-select"
                            >
                              <option value="admin">管理员</option>
                              <option value="member">普通成员</option>
                            </select>
                          )}
                          {(isCurrentUserAdmin || memberUser.id === userId) && (
                            <button
                              type="button"
                              className="member-remove-btn"
                              onClick={() => handleRemoveMember(memberUser.id)}
                              title={memberUser.id === userId ? '退出团队' : '移除成员'}
                            >
                              {memberUser.id === userId ? '🚪 退出' : '✕ 移除'}
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TeamManager;
