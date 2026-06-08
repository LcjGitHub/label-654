import json
import pytest
from datetime import datetime, timedelta


class TestCreateTask:
    def test_create_task_success(self, client, auth_headers):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'title': '新建任务', 'description': '任务描述'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['title'] == '新建任务'
        assert data['description'] == '任务描述'
        assert data['completed'] is False
        assert data['is_pinned'] is False
        assert data['priority'] == 'medium'
        assert 'id' in data

    def test_create_task_with_category(self, client, auth_headers, sample_category):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({
                'title': '带分类的任务',
                'category_id': sample_category['id']
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['category_id'] == sample_category['id']
        assert data['category']['name'] == sample_category['name']

    def test_create_task_with_tags(self, client, auth_headers, sample_tag):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({
                'title': '带标签的任务',
                'tag_ids': [sample_tag['id']]
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert len(data['tags']) == 1
        assert data['tags'][0]['id'] == sample_tag['id']

    def test_create_task_with_priority(self, client, auth_headers):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'title': '高优先级任务', 'priority': 'high'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['priority'] == 'high'

    def test_create_task_with_due_date(self, client, auth_headers):
        due_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'title': '有截止日期的任务', 'due_date': due_date}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['due_date'] is not None

    def test_create_task_pinned(self, client, auth_headers):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'title': '置顶任务', 'is_pinned': True}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['is_pinned'] is True

    def test_create_task_missing_title(self, client, auth_headers):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'description': '没有标题'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_create_task_invalid_category(self, client, auth_headers):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'title': '无效分类', 'category_id': 9999}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_create_task_invalid_tag(self, client, auth_headers):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'title': '无效标签', 'tag_ids': [9999]}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_create_task_invalid_priority_defaults(self, client, auth_headers):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'title': '无效优先级', 'priority': 'invalid'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['priority'] == 'medium'

    def test_create_task_unauthorized(self, client):
        resp = client.post(
            '/api/tasks',
            data=json.dumps({'title': '未授权任务'}),
            content_type='application/json'
        )
        assert resp.status_code == 401


class TestGetTasks:
    def test_get_tasks_empty(self, client, auth_headers):
        resp = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_tasks_list(self, client, auth_headers, sample_task):
        resp = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]['title'] == sample_task['title']

    def test_get_single_task(self, client, auth_headers, sample_task):
        resp = client.get(
            f'/api/tasks/{sample_task["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['id'] == sample_task['id']
        assert 'category' in data
        assert 'tags' in data
        assert 'attachments' in data

    def test_get_task_not_found(self, client, auth_headers):
        resp = client.get(
            '/api/tasks/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_get_tasks_filter_by_category(self, client, auth_headers, sample_category, sample_task):
        resp = client.get(
            f'/api/tasks?category_id={sample_category["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1

    def test_get_tasks_filter_no_category(self, client, auth_headers, sample_category, sample_task):
        client.post(
            '/api/tasks',
            data=json.dumps({'title': '无分类任务'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.get(
            '/api/tasks?category_id=none',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]['title'] == '无分类任务'

    def test_get_tasks_filter_by_tag(self, client, auth_headers, sample_tag, sample_task):
        resp = client.get(
            f'/api/tasks?tag_id={sample_tag["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1

    def test_get_tasks_search(self, client, auth_headers):
        client.post(
            '/api/tasks',
            data=json.dumps({'title': '独特的搜索词任务', 'description': '包含关键词'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        client.post(
            '/api/tasks',
            data=json.dumps({'title': '普通任务'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.get(
            '/api/tasks?search=独特的',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1

    def test_get_tasks_user_isolation(self, client, auth_headers, auth_headers_alt, sample_task):
        resp = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 0


class TestUpdateTask:
    def test_update_task_title(self, client, auth_headers, sample_task):
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}',
            data=json.dumps({'title': '更新后的标题'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['title'] == '更新后的标题'

    def test_update_task_completed(self, client, auth_headers, sample_task):
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}',
            data=json.dumps({'completed': True}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['completed'] is True
        assert data['completed_at'] is not None

    def test_update_task_uncomplete(self, client, auth_headers, sample_task):
        client.put(
            f'/api/tasks/{sample_task["id"]}',
            data=json.dumps({'completed': True}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}',
            data=json.dumps({'completed': False}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['completed'] is False
        assert data['completed_at'] is None

    def test_update_task_priority(self, client, auth_headers, sample_task):
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}',
            data=json.dumps({'priority': 'low'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['priority'] == 'low'

    def test_update_task_category(self, client, auth_headers, sample_task):
        new_cat = client.post(
            '/api/categories',
            data=json.dumps({'name': '新分类'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        new_cat_data = json.loads(new_cat.data)
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}',
            data=json.dumps({'category_id': new_cat_data['id']}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['category_id'] == new_cat_data['id']

    def test_update_task_not_found(self, client, auth_headers):
        resp = client.put(
            '/api/tasks/9999',
            data=json.dumps({'title': '不存在'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_update_task_invalid_category(self, client, auth_headers, sample_task):
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}',
            data=json.dumps({'category_id': 9999}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404


class TestToggleTask:
    def test_toggle_task_complete(self, client, auth_headers, sample_task):
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['completed'] is True

    def test_toggle_task_uncomplete(self, client, auth_headers, sample_task):
        client.put(
            f'/api/tasks/{sample_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['completed'] is False

    def test_toggle_task_not_found(self, client, auth_headers):
        resp = client.put(
            '/api/tasks/9999/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404


class TestPinTask:
    def test_pin_task(self, client, auth_headers, sample_task):
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}/pin',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['is_pinned'] is True

    def test_unpin_task(self, client, auth_headers, sample_task):
        client.put(
            f'/api/tasks/{sample_task["id"]}/pin',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}/pin',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['is_pinned'] is False

    def test_pin_task_not_found(self, client, auth_headers):
        resp = client.put(
            '/api/tasks/9999/pin',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404


class TestDeleteTask:
    def test_delete_task_success(self, client, auth_headers, sample_task):
        resp = client.delete(
            f'/api/tasks/{sample_task["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert '成功' in data['message']

        get_resp = client.get(
            f'/api/tasks/{sample_task["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert get_resp.status_code == 404

    def test_delete_task_not_found(self, client, auth_headers):
        resp = client.delete(
            '/api/tasks/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_delete_task_unauthorized(self, client, sample_task):
        resp = client.delete(f'/api/tasks/{sample_task["id"]}')
        assert resp.status_code == 401

    def test_delete_task_user_isolation(self, client, auth_headers, auth_headers_alt, sample_task):
        resp = client.delete(
            f'/api/tasks/{sample_task["id"]}',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 404
