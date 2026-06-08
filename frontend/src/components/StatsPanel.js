import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import { statsApi } from '../services/api';

function formatAvgTime(minutes) {
  if (!minutes || minutes <= 0) return '暂无数据';
  if (minutes < 60) {
    return `${Math.round(minutes)} 分钟`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  if (mins === 0) {
    return `${hours} 小时`;
  }
  return `${hours} 小时 ${mins} 分钟`;
}

function StatsPanel({ onClose }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chartType, setChartType] = useState('bar');

  const loadStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await statsApi.getStats();
      setStats(data);
    } catch (err) {
      setError(err.message || '加载统计数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  if (loading && !stats) {
    return (
      <div className="stats-overlay" onClick={handleOverlayClick}>
        <div className="stats-panel" onClick={(e) => e.stopPropagation()}>
          <div className="stats-header">
            <h2>📊 任务统计</h2>
            <button className="stats-close" onClick={onClose} aria-label="关闭">
              ✕
            </button>
          </div>
          <div className="stats-loading">
            <div className="spinner" />
            <span>正在加载统计数据...</span>
          </div>
        </div>
      </div>
    );
  }

  const statCards = stats
    ? [
        {
          label: '今日完成',
          value: stats.today_completed,
          icon: '✅',
          color: '#10b981',
          bg: '#ecfdf5',
        },
        {
          label: '本周完成',
          value: stats.week_completed,
          icon: '📅',
          color: '#6366f1',
          bg: '#eef2ff',
        },
        {
          label: '任务完成率',
          value: `${stats.completion_rate}%`,
          icon: '📈',
          color: '#f59e0b',
          bg: '#fffbeb',
        },
        {
          label: '平均完成时间',
          value: formatAvgTime(stats.avg_completion_minutes),
          icon: '⏱️',
          color: '#8b5cf6',
          bg: '#f5f3ff',
        },
        {
          label: '待完成任务',
          value: stats.active_tasks,
          icon: '📝',
          color: '#3b82f6',
          bg: '#eff6ff',
        },
        {
          label: '已过期任务',
          value: stats.overdue_tasks,
          icon: '⚠️',
          color: '#ef4444',
          bg: '#fef2f2',
        },
      ]
    : [];

  return (
    <div className="stats-overlay" onClick={handleOverlayClick}>
      <div className="stats-panel" onClick={(e) => e.stopPropagation()}>
        <div className="stats-header">
          <div>
            <h2>📊 任务统计</h2>
            <p className="stats-subtitle">查看你的任务完成情况和趋势</p>
          </div>
          <div className="stats-header-actions">
            <button
              className="stats-refresh"
              onClick={loadStats}
              disabled={loading}
              aria-label="刷新数据"
            >
              <span className={loading ? 'refresh-spinning' : ''}>🔄</span>
              刷新
            </button>
            <button className="stats-close" onClick={onClose} aria-label="关闭">
              ✕
            </button>
          </div>
        </div>

        {error && (
          <div className="stats-error">
            ⚠️ {error}
            <button onClick={loadStats} className="stats-retry">
              重试
            </button>
          </div>
        )}

        {stats && (
          <>
            <div className="stats-grid">
              {statCards.map((card) => (
                <div
                  key={card.label}
                  className="stat-card"
                  style={{ backgroundColor: card.bg }}
                >
                  <div className="stat-icon" style={{ color: card.color }}>
                    {card.icon}
                  </div>
                  <div className="stat-content">
                    <div className="stat-value" style={{ color: card.color }}>
                      {card.value}
                    </div>
                    <div className="stat-label">{card.label}</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="chart-section">
              <div className="chart-header">
                <h3>📈 最近 7 天任务趋势</h3>
                <div className="chart-type-toggle">
                  <button
                    className={chartType === 'bar' ? 'active' : ''}
                    onClick={() => setChartType('bar')}
                  >
                    柱状图
                  </button>
                  <button
                    className={chartType === 'line' ? 'active' : ''}
                    onClick={() => setChartType('line')}
                  >
                    折线图
                  </button>
                </div>
              </div>
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  {chartType === 'bar' ? (
                    <BarChart data={stats.daily_trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="#6b7280" />
                      <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" allowDecimals={false} />
                      <Tooltip
                        contentStyle={{
                          borderRadius: '8px',
                          border: '1px solid #e5e7eb',
                          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                        }}
                      />
                      <Legend />
                      <Bar
                        dataKey="created"
                        name="新增任务"
                        fill="#93c5fd"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey="completed"
                        name="完成任务"
                        fill="#667eea"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  ) : (
                    <LineChart data={stats.daily_trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="label" tick={{ fontSize: 12 }} stroke="#6b7280" />
                      <YAxis tick={{ fontSize: 12 }} stroke="#6b7280" allowDecimals={false} />
                      <Tooltip
                        contentStyle={{
                          borderRadius: '8px',
                          border: '1px solid #e5e7eb',
                          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                        }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="created"
                        name="新增任务"
                        stroke="#93c5fd"
                        strokeWidth={3}
                        dot={{ r: 4, fill: '#3b82f6' }}
                        activeDot={{ r: 6 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="completed"
                        name="完成任务"
                        stroke="#667eea"
                        strokeWidth={3}
                        dot={{ r: 4, fill: '#667eea' }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  )}
                </ResponsiveContainer>
              </div>
            </div>

            <div className="stats-summary">
              <div className="summary-item">
                <span className="summary-label">总任务数：</span>
                <span className="summary-value">{stats.total_tasks}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">已完成：</span>
                <span className="summary-value success">{stats.total_completed}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">待完成：</span>
                <span className="summary-value info">{stats.active_tasks}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">已过期：</span>
                <span className="summary-value danger">{stats.overdue_tasks}</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default StatsPanel;
