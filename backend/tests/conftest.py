import os
import sys
import tempfile
import shutil
import json
import pytest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['DB_TYPE'] = 'sqlite'
os.environ['SECRET_KEY'] = 'test-secret-key-for-unit-tests'

import app as todo_app


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    todo_app.DATABASE = db_path
    todo_app.DB_TYPE = 'sqlite'

    upload_dir = tempfile.mkdtemp(prefix='test_uploads_')
    todo_app.UPLOAD_FOLDER = upload_dir
    todo_app.app.config['UPLOAD_FOLDER'] = upload_dir

    todo_app.app.config['TESTING'] = True
    todo_app.app.config['SECRET_KEY'] = 'test-secret-key-for-unit-tests'

    todo_app.init_db()

    yield todo_app.app

    if os.path.exists(db_path):
        os.unlink(db_path)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def auth_headers(client):
    resp = client.post(
        '/api/auth/register',
        data=json.dumps({'username': 'testuser', 'password': 'testpass123'}),
        content_type='application/json'
    )
    assert resp.status_code == 201
    data = json.loads(resp.data)
    token = data['token']
    user = data['user']
    return {
        'Authorization': f'Bearer {token}',
        'token': token,
        'user_id': user['id'],
        'username': user['username']
    }


@pytest.fixture
def auth_headers_alt(client):
    resp = client.post(
        '/api/auth/register',
        data=json.dumps({'username': 'anotheruser', 'password': 'anotherpass123'}),
        content_type='application/json'
    )
    assert resp.status_code == 201
    data = json.loads(resp.data)
    token = data['token']
    user = data['user']
    return {
        'Authorization': f'Bearer {token}',
        'token': token,
        'user_id': user['id'],
        'username': user['username']
    }


@pytest.fixture
def sample_category(client, auth_headers):
    resp = client.post(
        '/api/categories',
        data=json.dumps({'name': '工作', 'color': '#ff0000'}),
        content_type='application/json',
        headers={'Authorization': auth_headers['Authorization']}
    )
    assert resp.status_code == 201
    return json.loads(resp.data)


@pytest.fixture
def sample_tag(client, auth_headers):
    resp = client.post(
        '/api/tags',
        data=json.dumps({'name': '重要', 'color': '#00ff00'}),
        content_type='application/json',
        headers={'Authorization': auth_headers['Authorization']}
    )
    assert resp.status_code == 201
    return json.loads(resp.data)


@pytest.fixture
def sample_task(client, auth_headers, sample_category, sample_tag):
    resp = client.post(
        '/api/tasks',
        data=json.dumps({
            'title': '测试任务',
            'description': '这是一个测试任务',
            'category_id': sample_category['id'],
            'priority': 'high',
            'tag_ids': [sample_tag['id']]
        }),
        content_type='application/json',
        headers={'Authorization': auth_headers['Authorization']}
    )
    assert resp.status_code == 201
    return json.loads(resp.data)
