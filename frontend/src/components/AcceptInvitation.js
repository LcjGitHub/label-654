import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { teamApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

function AcceptInvitation() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [invitationInfo, setInvitationInfo] = useState(null);
  const [accepted, setAccepted] = useState(false);

  useEffect(() => {
    const loadInvitation = async () => {
      try {
        setLoading(true);
        setError(null);
        const info = await teamApi.getInvitation(token);
        setInvitationInfo(info);
      } catch (err) {
        setError(err.message || '获取邀请信息失败');
      } finally {
        setLoading(false);
      }
    };
    loadInvitation();
  }, [token]);

  const handleAccept = async () => {
    try {
      setLoading(true);
      setError(null);
      await teamApi.acceptInvitation(token);
      setAccepted(true);
      setTimeout(() => {
        navigate('/', { replace: true });
      }, 2000);
    } catch (err) {
      setError(err.message || '接受邀请失败');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="app">
        <div className="container">
          <div className="invite-page">
            <div className="loading">加载中...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error && !invitationInfo) {
    return (
      <div className="app">
        <div className="container">
          <div className="invite-page">
            <div className="invite-card">
              <div className="invite-icon">⚠️</div>
              <h2>邀请无效</h2>
              <p className="invite-error">{error}</p>
              <p>该邀请链接可能已过期或已被使用。</p>
              <Link to="/" className="btn-primary">
                返回首页
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="container">
        <div className="invite-page">
          <div className="invite-card">
            {accepted ? (
              <>
                <div className="invite-icon">✅</div>
                <h2>已加入团队！</h2>
                <p>你已成功加入 <strong>{invitationInfo?.team_name}</strong> 团队。</p>
                <p>即将跳转到首页...</p>
              </>
            ) : (
              <>
                <div className="invite-icon">📨</div>
                <h2>团队邀请</h2>
                <p>
                  你被邀请加入 <strong>{invitationInfo?.team_name}</strong> 团队
                </p>
                {invitationInfo?.email && (
                  <p className="invite-email">
                    邀请邮箱：{invitationInfo.email}
                  </p>
                )}
                {!isAuthenticated ? (
                  <div className="invite-auth">
                    <p>请先登录或注册后再接受邀请。</p>
                    <div className="invite-actions">
                      <Link
                        to={`/login?redirect=/invite/${token}`}
                        className="btn-primary"
                      >
                        登录
                      </Link>
                      <Link
                        to={`/register?redirect=/invite/${token}`}
                        className="btn-secondary"
                      >
                        注册
                      </Link>
                    </div>
                  </div>
                ) : (
                  <div className="invite-actions">
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={handleAccept}
                      disabled={loading}
                    >
                      {loading ? '处理中...' : '接受邀请'}
                    </button>
                    <Link to="/" className="btn-secondary">
                      暂不接受
                    </Link>
                  </div>
                )}
                {error && <p className="invite-error">{error}</p>}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AcceptInvitation;
