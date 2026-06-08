import React, { useState, useEffect, useMemo } from 'react';
import { teamApi, taskApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

function TeamBoard({ onClose }) {
  const { user } = useAuth();
  const userId = user?.id;
  const [teams, setTeams] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [teamUsers, setTeamUsers] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

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

  const loadTeamBoard = async (team) => {
    try {
      setLoading(true);
      setError('');
      const [users, teamTasks] = await Promise.all([
        teamApi.getTeamUsers(team.id),
        teamApi.getTeamTasks(team.id),
      ]);
      setTeamUsers(users);
      setTasks(teamTasks);
      setSelectedTeam(team);
    } catch (err) {
      setError(err.message || '加载团队看板失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTask = async (taskId) => {
    try {
      await taskApi.toggleTask(taskId);
      if (selectedTeam) {
        await loadTeamBoard(selectedTeam);
      }
    } catch (err) {
      setError(err.message || '更新任务状态失败');
    }
  };

  const filteredTasks = useMemo(() => {
    if (filterStatus === 'all') return tasks;
    if (filterStatus === 'active') return tasks.filter(t => !t.completed);
    return tasks.filter(t => t.completed);
  }, [tasks, filterStatus]);

  const tasksByUser = useMemo(() => {
    const grouped = {};

    filteredTasks.forEach(task => {
      const key = task.assignee_id ? `user_${task.assignee_id}` : 'unassigned';
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(task);
    });

    return grouped;
  }, [filteredTasks]);

  const getUserTasks = (uid) => tasksByUser[`user_${uid}`] || [];
  const unassignedTasks = tasksByUser['unassigned'] || [];

  const getStats = (userTasks) => {
    const total = userTasks.length;
    const completed = userTasks.filter(t => t.completed).length;
    const active = total - completed;
    return { total, completed, active };
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  const isOverdue = (dueDate) => {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date() && !tasks.find(t => t.due_date === dueDate)?.completed;
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      case 'low': return '#22c55e';
      default: return '#6b7280';
    }
  };

  const getTagColor = (tag) => {
    if (tag && tag.color) return tag.color;
    const colors = ['#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899', '#f43f5e', '#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6'];
    const idx = (tag?.id || 0) % colors.length;
    return colors[idx];
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={e => e.stopPropagation()} style={{ maxWidth: '1100px' }}>
        <div className="modal-header">
          <h2>👥 团队任务看板</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {error && (
          <div className="error-message" style={{ margin: '12px 16px' }}>
            ⚠️ {error}
          </div>
        )}

        <div className="modal-body">
          <div className="team-board">
            <div className="team-board-main">
              <div className="board-sidebar">
                <h3>选择团队</h3>
                <div className="board-team-list">
                  {loading && teams.length === 0 ? (
                    <div className="loading">加载中...</div>
                  ) : teams.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-state-icon">🏢</div>
                      <div className="empty-state-text">还没有团队</div>
                    </div>
                  ) : (
                    teams.map(team => (
                      <div
                        key={team.id}
                        className={`board-team-item ${selectedTeam?.id === team.id ? 'active' : ''}`}
                        onClick={() => loadTeamBoard(team)}
                      >
                        👥 {team.name}
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="board-content">
                {!selectedTeam ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">👈</div>
                    <div className="empty-state-text">请选择一个团队查看任务看板</div>
                  </div>
                ) : (
                  <>
                    <div className="board-filter">
                      <button
                        className={`board-filter-btn ${filterStatus === 'all' ? 'active' : ''}`}
                        onClick={() => setFilterStatus('all')}
                      >
                        全部 ({tasks.length})
                      </button>
                      <button
                        className={`board-filter-btn ${filterStatus === 'active' ? 'active' : ''}`}
                        onClick={() => setFilterStatus('active')}
                      >
                        进行中 ({tasks.filter(t => !t.completed).length})
                      </button>
                      <button
                        className={`board-filter-btn ${filterStatus === 'completed' ? 'active' : ''}`}
                        onClick={() => setFilterStatus('completed')}
                      >
                        已完成 ({tasks.filter(t => t.completed).length})
                      </button>
                    </div>

                    <div className="board-columns">
                      {teamUsers.map(boardUser => {
                        const userTasks = getUserTasks(boardUser.id);
                        const stats = getStats(userTasks);
                        return (
                          <div key={boardUser.id} className="board-column">
                            <div className="board-column-header">
                              <div className="board-column-avatar">
                                {boardUser.username.charAt(0).toUpperCase()}
                              </div>
                              <div className="board-column-title">
                                <div className="board-column-name">{boardUser.username}</div>
                                <div className="board-column-count">
                                  <span className={`role-badge ${boardUser.role}`} style={{ marginRight: '6px' }}>
                                    {boardUser.role === 'admin' ? '管理员' : '成员'}
                                  </span>
                                  进行中 {stats.active} / 共 {stats.total}
                                </div>
                              </div>
                            </div>
                            <div className="board-tasks">
                              {userTasks.length === 0 ? (
                                <div className="board-empty">暂无任务</div>
                              ) : (
                                userTasks.map(task => (
                                  <div
                                    key={task.id}
                                    className={`board-task-card priority-${task.priority || 'medium'} ${task.completed ? 'completed' : ''}`}
                                  >
                                    <div className="board-task-title">
                                      <input
                                        type="checkbox"
                                        checked={task.completed}
                                        onChange={() => handleToggleTask(task.id)}
                                        style={{ marginTop: '2px' }}
                                      />
                                      <span>{task.title}</span>
                                    </div>
                                    {task.description && (
                                      <div className="board-task-desc">{task.description}</div>
                                    )}
                                    <div className="board-task-meta">
                                      {task.due_date && (
                                        <span className={`board-task-due ${new Date(task.due_date) < new Date() && !task.completed ? 'overdue' : ''}`}>
                                          📅 {formatDate(task.due_date)}
                                        </span>
                                      )}
                                      {task.category && (
                                        <span className="board-task-category">
                                          📁 {task.category.name}
                                        </span>
                                      )}
                                      {task.creator && (
                                        <span className="board-task-creator">
                                          ✍️ {task.creator.username}
                                        </span>
                                      )}
                                    </div>
                                    {task.tags && task.tags.length > 0 && (
                                      <div className="board-task-tags">
                                        {task.tags.map(tag => (
                                          <span
                                            key={tag.id}
                                            className="board-task-tag"
                                            style={{ backgroundColor: getTagColor(tag) }}
                                          >
                                            {tag.name}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                ))
                              )}
                            </div>
                          </div>
                        );
                      })}

                      {unassignedTasks.length > 0 && (
                        <div className="board-column">
                          <div className="board-column-header">
                            <div className="board-column-avatar">📦</div>
                            <div className="board-column-title">
                              <div className="board-column-name">未分配</div>
                              <div className="board-column-count">
                                进行中 {getStats(unassignedTasks).active} / 共 {getStats(unassignedTasks).total}
                              </div>
                            </div>
                          </div>
                          <div className="board-tasks">
                            {unassignedTasks.map(task => (
                              <div
                                key={task.id}
                                className={`board-task-card priority-${task.priority || 'medium'} ${task.completed ? 'completed' : ''}`}
                              >
                                <div className="board-task-title">
                                  <input
                                    type="checkbox"
                                    checked={task.completed}
                                    onChange={() => handleToggleTask(task.id)}
                                    style={{ marginTop: '2px' }}
                                  />
                                  <span>{task.title}</span>
                                </div>
                                {task.description && (
                                  <div className="board-task-desc">{task.description}</div>
                                )}
                                <div className="board-task-meta">
                                  {task.due_date && (
                                    <span className={`board-task-due ${new Date(task.due_date) < new Date() && !task.completed ? 'overdue' : ''}`}>
                                      📅 {formatDate(task.due_date)}
                                    </span>
                                  )}
                                  {task.creator && (
                                    <span className="board-task-creator">
                                      ✍️ {task.creator.username}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TeamBoard;
