import json
import pytest


class TestCategoryCRUD:
    def test_create_category_success(self, client, auth_headers):
        resp = client.post(
            '/api/categories',
            data=json.dumps({'name': '工作', 'color': '#ff0000'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['name'] == '工作'
        assert data['color'] == '#ff0000'
        assert 'id' in data

    def test_create_category_default_color(self, client, auth_headers):
        resp = client.post(
            '/api/categories',
            data=json.dumps({'name': '默认颜色'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['color'] == '#667eea'

    def test_create_category_missing_name(self, client, auth_headers):
        resp = client.post(
            '/api/categories',
            data=json.dumps({'color': '#ff0000'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_create_category_empty_name(self, client, auth_headers):
        resp = client.post(
            '/api/categories',
            data=json.dumps({'name': ''}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_create_category_whitespace_name(self, client, auth_headers):
        resp = client.post(
            '/api/categories',
            data=json.dumps({'name': '   '}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_create_category_duplicate_name(self, client, auth_headers):
        client.post(
            '/api/categories',
            data=json.dumps({'name': '重复分类'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.post(
            '/api/categories',
            data=json.dumps({'name': '重复分类'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert '已存在' in data['error']

    def test_create_category_same_name_different_user(self, client, auth_headers, auth_headers_alt):
        client.post(
            '/api/categories',
            data=json.dumps({'name': '各自的分类'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.post(
            '/api/categories',
            data=json.dumps({'name': '各自的分类'}),
            content_type='application/json',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 201

    def test_get_categories_empty(self, client, auth_headers):
        resp = client.get(
            '/api/categories',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_categories_list(self, client, auth_headers, sample_category):
        resp = client.get(
            '/api/categories',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]['name'] == sample_category['name']

    def test_get_single_category(self, client, auth_headers, sample_category):
        resp = client.get(
            f'/api/categories/{sample_category["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['id'] == sample_category['id']

    def test_get_category_not_found(self, client, auth_headers):
        resp = client.get(
            '/api/categories/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_get_categories_user_isolation(self, client, auth_headers, auth_headers_alt, sample_category):
        resp = client.get(
            '/api/categories',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 0

    def test_update_category_name(self, client, auth_headers, sample_category):
        resp = client.put(
            f'/api/categories/{sample_category["id"]}',
            data=json.dumps({'name': '更新后的分类名'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['name'] == '更新后的分类名'

    def test_update_category_color(self, client, auth_headers, sample_category):
        resp = client.put(
            f'/api/categories/{sample_category["id"]}',
            data=json.dumps({'color': '#00ff00'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['color'] == '#00ff00'

    def test_update_category_duplicate_name(self, client, auth_headers):
        client.post(
            '/api/categories',
            data=json.dumps({'name': '分类A'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        cat_b = client.post(
            '/api/categories',
            data=json.dumps({'name': '分类B'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        cat_b_data = json.loads(cat_b.data)
        resp = client.put(
            f'/api/categories/{cat_b_data["id"]}',
            data=json.dumps({'name': '分类A'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_update_category_empty_name(self, client, auth_headers, sample_category):
        resp = client.put(
            f'/api/categories/{sample_category["id"]}',
            data=json.dumps({'name': ''}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_update_category_not_found(self, client, auth_headers):
        resp = client.put(
            '/api/categories/9999',
            data=json.dumps({'name': '不存在'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_delete_category_success(self, client, auth_headers, sample_category):
        resp = client.delete(
            f'/api/categories/{sample_category["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert '成功' in data['message']

        get_resp = client.get(
            f'/api/categories/{sample_category["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert get_resp.status_code == 404

    def test_delete_category_not_found(self, client, auth_headers):
        resp = client.delete(
            '/api/categories/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_delete_category_unassigns_tasks(self, client, auth_headers, sample_category, sample_task):
        client.delete(
            f'/api/categories/{sample_category["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.get(
            f'/api/tasks/{sample_task["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['category_id'] is None


class TestTagCRUD:
    def test_create_tag_success(self, client, auth_headers):
        resp = client.post(
            '/api/tags',
            data=json.dumps({'name': '重要', 'color': '#ff0000'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['name'] == '重要'
        assert data['color'] == '#ff0000'
        assert 'task_count' in data
        assert data['task_count'] == 0

    def test_create_tag_default_color(self, client, auth_headers):
        resp = client.post(
            '/api/tags',
            data=json.dumps({'name': '默认颜色标签'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['color'] == '#667eea'

    def test_create_tag_missing_name(self, client, auth_headers):
        resp = client.post(
            '/api/tags',
            data=json.dumps({'color': '#ff0000'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_create_tag_empty_name(self, client, auth_headers):
        resp = client.post(
            '/api/tags',
            data=json.dumps({'name': ''}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_create_tag_duplicate_name(self, client, auth_headers):
        client.post(
            '/api/tags',
            data=json.dumps({'name': '重复标签'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.post(
            '/api/tags',
            data=json.dumps({'name': '重复标签'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert '已存在' in data['error']

    def test_create_tag_same_name_different_user(self, client, auth_headers, auth_headers_alt):
        client.post(
            '/api/tags',
            data=json.dumps({'name': '各自的标签'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.post(
            '/api/tags',
            data=json.dumps({'name': '各自的标签'}),
            content_type='application/json',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 201

    def test_get_tags_empty(self, client, auth_headers):
        resp = client.get(
            '/api/tags',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_tags_list(self, client, auth_headers, sample_tag):
        resp = client.get(
            '/api/tags',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]['name'] == sample_tag['name']

    def test_get_single_tag(self, client, auth_headers, sample_tag):
        resp = client.get(
            f'/api/tags/{sample_tag["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['id'] == sample_tag['id']

    def test_get_tag_not_found(self, client, auth_headers):
        resp = client.get(
            '/api/tags/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_get_tags_user_isolation(self, client, auth_headers, auth_headers_alt, sample_tag):
        resp = client.get(
            '/api/tags',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 0

    def test_update_tag_name(self, client, auth_headers, sample_tag):
        resp = client.put(
            f'/api/tags/{sample_tag["id"]}',
            data=json.dumps({'name': '更新后的标签名'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['name'] == '更新后的标签名'

    def test_update_tag_color(self, client, auth_headers, sample_tag):
        resp = client.put(
            f'/api/tags/{sample_tag["id"]}',
            data=json.dumps({'color': '#0000ff'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['color'] == '#0000ff'

    def test_update_tag_duplicate_name(self, client, auth_headers):
        client.post(
            '/api/tags',
            data=json.dumps({'name': '标签A'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        tag_b = client.post(
            '/api/tags',
            data=json.dumps({'name': '标签B'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        tag_b_data = json.loads(tag_b.data)
        resp = client.put(
            f'/api/tags/{tag_b_data["id"]}',
            data=json.dumps({'name': '标签A'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_update_tag_empty_name(self, client, auth_headers, sample_tag):
        resp = client.put(
            f'/api/tags/{sample_tag["id"]}',
            data=json.dumps({'name': ''}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_update_tag_not_found(self, client, auth_headers):
        resp = client.put(
            '/api/tags/9999',
            data=json.dumps({'name': '不存在'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_delete_tag_success(self, client, auth_headers, sample_tag):
        resp = client.delete(
            f'/api/tags/{sample_tag["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert '成功' in data['message']

        get_resp = client.get(
            f'/api/tags/{sample_tag["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert get_resp.status_code == 404

    def test_delete_tag_not_found(self, client, auth_headers):
        resp = client.delete(
            '/api/tags/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_tag_task_count(self, client, auth_headers, sample_tag, sample_task):
        resp = client.get(
            '/api/tags',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        tag_data = next(t for t in data if t['id'] == sample_tag['id'])
        assert tag_data['task_count'] == 1


class TestTaskTags:
    def test_add_tag_to_task(self, client, auth_headers, sample_task):
        new_tag = client.post(
            '/api/tags',
            data=json.dumps({'name': '新标签'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        new_tag_data = json.loads(new_tag.data)

        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/tags',
            data=json.dumps({'tag_id': new_tag_data['id']}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        tag_ids = [t['id'] for t in data]
        assert new_tag_data['id'] in tag_ids

    def test_add_tag_to_task_not_found(self, client, auth_headers, sample_tag):
        resp = client.post(
            '/api/tasks/9999/tags',
            data=json.dumps({'tag_id': sample_tag['id']}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_add_invalid_tag_to_task(self, client, auth_headers, sample_task):
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/tags',
            data=json.dumps({'tag_id': 9999}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_remove_tag_from_task(self, client, auth_headers, sample_task, sample_tag):
        resp = client.delete(
            f'/api/tasks/{sample_task["id"]}/tags/{sample_tag["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        tag_ids = [t['id'] for t in data]
        assert sample_tag['id'] not in tag_ids

    def test_remove_tag_task_not_found(self, client, auth_headers, sample_tag):
        resp = client.delete(
            f'/api/tasks/9999/tags/{sample_tag["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_remove_tag_not_found(self, client, auth_headers, sample_task):
        resp = client.delete(
            f'/api/tasks/{sample_task["id"]}/tags/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404
