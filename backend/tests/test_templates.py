import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTemplates:
    """测试任务模板API"""

    def test_create_template(self, client, auth_headers, sample_category, sample_tag):
        """测试创建模板"""
        resp = client.post(
            '/api/templates',
            data=json.dumps({
                'name': '每日工作报告',
                'title': '今日工作报告',
                'description': '记录今日完成的工作、遇到的问题和明日计划',
                'priority': 'medium',
                'category_id': sample_category['id'],
                'tag_ids': [sample_tag['id']]
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['name'] == '每日工作报告'
        assert data['title'] == '今日工作报告'
        assert data['description'] is not None
        assert data['priority'] == 'medium'
        assert data['category_id'] == sample_category['id']
        assert 'id' in data
        return data

    def test_get_templates_empty(self, client, auth_headers):
        """测试获取空模板列表"""
        resp = client.get(
            '/api/templates',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_templates(self, client, auth_headers, sample_category, sample_tag):
        """测试获取模板列表"""
        self.test_create_template(client, auth_headers, sample_category, sample_tag)
        resp = client.get(
            '/api/templates',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_get_template(self, client, auth_headers, sample_category, sample_tag):
        """测试获取单个模板详情"""
        template = self.test_create_template(client, auth_headers, sample_category, sample_tag)
        resp = client.get(
            f'/api/templates/{template["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['id'] == template['id']
        assert data['name'] == template['name']
        assert 'tags' in data
        assert len(data['tags']) == 1
        assert data['category'] is not None

    def test_get_template_not_found(self, client, auth_headers):
        """测试获取不存在的模板"""
        resp = client.get(
            '/api/templates/99999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_update_template(self, client, auth_headers, sample_category, sample_tag):
        """测试更新模板"""
        template = self.test_create_template(client, auth_headers, sample_category, sample_tag)
        resp = client.put(
            f'/api/templates/{template["id"]}',
            data=json.dumps({
                'name': '每周工作报告',
                'title': '本周工作汇报',
                'description': '更新后的描述',
                'priority': 'high',
                'category_id': sample_category['id'],
                'tag_ids': [sample_tag['id']]
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['name'] == '每周工作报告'
        assert data['title'] == '本周工作汇报'
        assert data['priority'] == 'high'

    def test_update_template_not_found(self, client, auth_headers, sample_category, sample_tag):
        """测试更新不存在的模板"""
        resp = client.put(
            '/api/templates/99999',
            data=json.dumps({
                'name': '测试',
                'title': '测试',
                'priority': 'low',
                'category_id': sample_category['id'],
                'tag_ids': [sample_tag['id']]
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_delete_template(self, client, auth_headers, sample_category, sample_tag):
        """测试删除模板"""
        template = self.test_create_template(client, auth_headers, sample_category, sample_tag)
        resp = client.delete(
            f'/api/templates/{template["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 204

    def test_delete_template_not_found(self, client, auth_headers):
        """测试删除不存在的模板"""
        resp = client.delete(
            '/api/templates/99999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_template_user_isolation(self, client, auth_headers, auth_headers_alt, sample_category, sample_tag):
        """测试用户之间模板隔离"""
        template = self.test_create_template(client, auth_headers, sample_category, sample_tag)
        resp = client.get(
            f'/api/templates/{template["id"]}',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 404

    def test_apply_template(self, client, auth_headers, sample_category, sample_tag):
        """测试基于模板创建任务"""
        template = self.test_create_template(client, auth_headers, sample_category, sample_tag)
        resp = client.post(
            f'/api/templates/{template["id"]}/apply',
            data=json.dumps({
                'title': '今日工作报告 - 2024-01-01'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['title'] == '今日工作报告 - 2024-01-01'
        assert data['description'] is not None
        assert data['priority'] == 'medium'
        assert data['category_id'] == sample_category['id']

    def test_save_task_as_template(self, client, auth_headers, sample_task):
        """测试将任务另存为模板"""
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/save-as-template',
            data=json.dumps({
                'name': '常用任务模板'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['name'] == '常用任务模板'
        assert data['title'] == sample_task['title']
        assert data['description'] == sample_task['description']
        assert data['priority'] == sample_task['priority']

    def test_save_task_as_template_not_found(self, client, auth_headers):
        """测试将不存在的任务另存为模板"""
        resp = client.post(
            '/api/tasks/99999/save-as-template',
            data=json.dumps({
                'name': '测试模板'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_create_template_missing_name(self, client, auth_headers):
        """测试创建模板缺少必填字段"""
        resp = client.post(
            '/api/templates',
            data=json.dumps({
                'title': '只有标题',
                'priority': 'medium'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_create_template_missing_title(self, client, auth_headers):
        """测试创建模板缺少标题"""
        resp = client.post(
            '/api/templates',
            data=json.dumps({
                'name': '模板名称',
                'priority': 'medium'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_template_unauthorized(self, client):
        """测试未授权访问模板"""
        resp = client.get('/api/templates')
        assert resp.status_code == 401
