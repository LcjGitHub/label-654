import json
import pytest
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as todo_app


class TestDateCalculation:
    def test_calculate_next_repeat_date_daily(self):
        base = '2025-01-15 10:00:00'
        result = todo_app.calculate_next_repeat_date(base, 'daily')
        assert result == '2025-01-16 10:00:00'

    def test_calculate_next_repeat_date_weekly(self):
        base = '2025-01-15 10:00:00'
        result = todo_app.calculate_next_repeat_date(base, 'weekly')
        assert result == '2025-01-22 10:00:00'

    def test_calculate_next_repeat_date_monthly(self):
        base = '2025-01-15 10:00:00'
        result = todo_app.calculate_next_repeat_date(base, 'monthly')
        assert result == '2025-02-15 10:00:00'

    def test_calculate_next_repeat_date_monthly_year_boundary(self):
        base = '2025-12-31 10:00:00'
        result = todo_app.calculate_next_repeat_date(base, 'monthly')
        assert result == '2026-01-31 10:00:00'

    def test_calculate_next_repeat_date_monthly_end_of_month(self):
        base = '2025-01-31 10:00:00'
        result = todo_app.calculate_next_repeat_date(base, 'monthly')
        assert result == '2025-02-28 10:00:00'

    def test_calculate_next_repeat_date_yearly(self):
        base = '2025-06-15 10:00:00'
        result = todo_app.calculate_next_repeat_date(base, 'yearly')
        assert result == '2026-06-15 10:00:00'

    def test_calculate_next_repeat_date_yearly_leap_day(self):
        base = '2024-02-29 10:00:00'
        result = todo_app.calculate_next_repeat_date(base, 'yearly')
        assert result == '2025-02-28 10:00:00'

    def test_calculate_next_repeat_date_none_pattern(self):
        base = '2025-01-15 10:00:00'
        result = todo_app.calculate_next_repeat_date(base, 'none')
        assert result is None

    def test_calculate_next_repeat_date_none_date(self):
        result = todo_app.calculate_next_repeat_date(None, 'daily')
        assert result is not None

    def test_validate_repeat_pattern_valid(self):
        assert todo_app.validate_repeat_pattern('daily') == 'daily'
        assert todo_app.validate_repeat_pattern('weekly') == 'weekly'
        assert todo_app.validate_repeat_pattern('monthly') == 'monthly'
        assert todo_app.validate_repeat_pattern('yearly') == 'yearly'
        assert todo_app.validate_repeat_pattern('none') == 'none'

    def test_validate_repeat_pattern_invalid(self):
        assert todo_app.validate_repeat_pattern('invalid') == 'none'

    def test_validate_repeat_pattern_empty(self):
        assert todo_app.validate_repeat_pattern(None) == 'none'
        assert todo_app.validate_repeat_pattern('') == 'none'


class TestRepeatTaskCreation:
    def test_create_task_with_repeat_pattern(self, client, auth_headers):
        due_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        resp = client.post(
            '/api/tasks',
            data=json.dumps({
                'title': '每日重复任务',
                'due_date': due_date,
                'repeat_pattern': 'daily'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data['repeat_pattern'] == 'daily'

    def test_completing_repeat_task_creates_next(self, client, auth_headers):
        due_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        create_resp = client.post(
            '/api/tasks',
            data=json.dumps({
                'title': '每日任务',
                'due_date': due_date,
                'repeat_pattern': 'daily'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        original_task = json.loads(create_resp.data)

        client.put(
            f'/api/tasks/{original_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )

        list_resp = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers['Authorization']}
        )
        all_tasks = json.loads(list_resp.data)
        assert len(all_tasks) >= 2

        repeat_tasks = [t for t in all_tasks if t['repeat_parent_id'] is not None]
        assert len(repeat_tasks) >= 1

    def test_completing_none_repeat_no_next(self, client, auth_headers):
        create_resp = client.post(
            '/api/tasks',
            data=json.dumps({
                'title': '普通任务',
                'repeat_pattern': 'none'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        original_task = json.loads(create_resp.data)

        client.put(
            f'/api/tasks/{original_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )

        list_resp = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers['Authorization']}
        )
        all_tasks = json.loads(list_resp.data)
        assert len(all_tasks) == 1

    def test_update_task_repeat_pattern(self, client, auth_headers, sample_task):
        resp = client.put(
            f'/api/tasks/{sample_task["id"]}',
            data=json.dumps({'repeat_pattern': 'weekly'}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['repeat_pattern'] == 'weekly'

    def test_check_repeat_endpoint(self, client, auth_headers):
        due_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        client.post(
            '/api/tasks',
            data=json.dumps({
                'title': '要重复的任务',
                'due_date': due_date,
                'repeat_pattern': 'daily',
                'completed': True
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )

        resp = client.post(
            '/api/tasks/check-repeat',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'created_count' in data
        assert isinstance(data['created_count'], int)

    def test_repeat_task_preserves_fields(self, client, auth_headers, sample_category, sample_tag):
        due_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        create_resp = client.post(
            '/api/tasks',
            data=json.dumps({
                'title': '继承字段的任务',
                'description': '描述内容',
                'category_id': sample_category['id'],
                'priority': 'high',
                'due_date': due_date,
                'is_pinned': True,
                'repeat_pattern': 'daily',
                'tag_ids': [sample_tag['id']]
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        original_task = json.loads(create_resp.data)

        client.put(
            f'/api/tasks/{original_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )

        list_resp = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers['Authorization']}
        )
        all_tasks = json.loads(list_resp.data)

        next_task = None
        for t in all_tasks:
            if t['repeat_parent_id'] == original_task['id'] or (
                t['repeat_parent_id'] is not None and t['id'] != original_task['id']
            ):
                next_task = t
                break

        assert next_task is not None
        assert next_task['title'] == '继承字段的任务'
        assert next_task['description'] == '描述内容'
        assert next_task['category_id'] == sample_category['id']
        assert next_task['priority'] == 'high'
        assert next_task['is_pinned'] is True
        assert next_task['repeat_pattern'] == 'daily'
        assert len(next_task['tags']) == 1
        assert next_task['tags'][0]['id'] == sample_tag['id']
        assert next_task['due_date'] is not None

    def test_not_create_duplicate_next_when_active_exists(self, client, auth_headers):
        due_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        create_resp = client.post(
            '/api/tasks',
            data=json.dumps({
                'title': '每日任务',
                'due_date': due_date,
                'repeat_pattern': 'daily'
            }),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        original_task = json.loads(create_resp.data)

        client.put(
            f'/api/tasks/{original_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )

        list_resp_1 = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers['Authorization']}
        )
        count_after_first = len(json.loads(list_resp_1.data))

        client.put(
            f'/api/tasks/{original_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )

        list_resp_2 = client.get(
            '/api/tasks',
            headers={'Authorization': auth_headers['Authorization']}
        )
        count_after_second = len(json.loads(list_resp_2.data))

        assert count_after_second == count_after_first
