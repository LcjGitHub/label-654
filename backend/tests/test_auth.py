import json
import jwt
import pytest
from datetime import datetime, timedelta


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'newuser', 'password': 'password123'}),
            content_type='application/json'
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert 'token' in data
        assert 'user' in data
        assert data['user']['username'] == 'newuser'
        assert 'id' in data['user']

    def test_register_missing_fields(self, client):
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'error' in data

    def test_register_missing_username(self, client):
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({'password': 'password123'}),
            content_type='application/json'
        )
        assert resp.status_code == 400

    def test_register_missing_password(self, client):
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'testuser'}),
            content_type='application/json'
        )
        assert resp.status_code == 400

    def test_register_username_too_short(self, client):
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'ab', 'password': 'password123'}),
            content_type='application/json'
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert '至少需要 3 个字符' in data['error']

    def test_register_password_too_short(self, client):
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'validuser', 'password': '123'}),
            content_type='application/json'
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert '至少需要 6 个字符' in data['error']

    def test_register_duplicate_username(self, client):
        client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'sameuser', 'password': 'password123'}),
            content_type='application/json'
        )
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'sameuser', 'password': 'anotherpass'}),
            content_type='application/json'
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert '已存在' in data['error']


class TestLogin:
    def test_login_success(self, client):
        client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'loginuser', 'password': 'mypassword'}),
            content_type='application/json'
        )
        resp = client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'loginuser', 'password': 'mypassword'}),
            content_type='application/json'
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'token' in data
        assert 'user' in data
        assert data['user']['username'] == 'loginuser'

    def test_login_wrong_password(self, client):
        client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'loginuser2', 'password': 'correctpass'}),
            content_type='application/json'
        )
        resp = client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'loginuser2', 'password': 'wrongpass'}),
            content_type='application/json'
        )
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert '错误' in data['error']

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'nobody', 'password': 'somepass'}),
            content_type='application/json'
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post(
            '/api/auth/login',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert resp.status_code == 400


class TestTokenValidation:
    def test_token_required_no_token(self, client):
        resp = client.get('/api/tasks')
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert '令牌缺失' in data['error']

    def test_token_required_invalid_token(self, client):
        resp = client.get(
            '/api/tasks',
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert '令牌无效' in data['error']

    def test_token_required_expired_token(self, client, app):
        expired_token = jwt.encode(
            {'user_id': 1, 'exp': datetime.utcnow() - timedelta(hours=1)},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        resp = client.get(
            '/api/tasks',
            headers={'Authorization': f'Bearer {expired_token}'}
        )
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert '过期' in data['error']

    def test_token_via_query_param(self, client, auth_headers):
        resp = client.get(f'/api/tasks?token={auth_headers["token"]}')
        assert resp.status_code == 200

    def test_valid_token_access(self, client, auth_headers):
        resp = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200

    def test_token_contains_user_id(self, client, app):
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'tokenuser', 'password': 'password123'}),
            content_type='application/json'
        )
        data = json.loads(resp.data)
        token = data['token']
        decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        assert 'user_id' in decoded
        assert decoded['user_id'] == data['user']['id']

    def test_token_has_expiration(self, client, app):
        resp = client.post(
            '/api/auth/register',
            data=json.dumps({'username': 'expuser', 'password': 'password123'}),
            content_type='application/json'
        )
        data = json.loads(resp.data)
        token = data['token']
        decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        assert 'exp' in decoded
        exp_time = datetime.utcfromtimestamp(decoded['exp'])
        assert exp_time > datetime.utcnow()
