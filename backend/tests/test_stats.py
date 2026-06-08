import json
import pytest
from datetime import datetime, timedelta


class TestStats:
    def test_stats_empty(self, client, auth_headers):
        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['total_tasks'] == 0
        assert data['total_completed'] == 0
        assert data['active_tasks'] == 0
        assert data['overdue_tasks'] == 0
        assert data['today_completed'] == 0
        assert data['week_completed'] == 0
        assert data['completion_rate'] == 0.0
        assert data['avg_completion_minutes'] == 0.0
        assert isinstance(data['daily_trend'], list)
        assert len(data['daily_trend']) == 7

    def test_stats_total_tasks(self, client, auth_headers, sample_task):
        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['total_tasks'] == 1
        assert data['active_tasks'] == 1
        assert data['total_completed'] == 0

    def test_stats_completed_tasks(self, client, auth_headers, sample_task):
        client.put(
            f'/api/tasks/{sample_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )
        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['total_tasks'] == 1
        assert data['total_completed'] == 1
        assert data['active_tasks'] == 0
        assert data['today_completed'] == 1

    def test_stats_completion_rate(self, client, auth_headers):
        for i in range(4):
            resp = client.post(
                '/api/tasks',
                data=json.dumps({'title': f'任务{i}'}),
                content_type='application/json',
                headers={'Authorization': auth_headers['Authorization']}
            )
            task = json.loads(resp.data)
            if i < 2:
                client.put(
                    f'/api/tasks/{task["id"]}/toggle',
                    headers={'Authorization': auth_headers['Authorization']}
                )

        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['total_tasks'] == 4
        assert data['total_completed'] == 2
        assert data['completion_rate'] == 50.0

    def test_stats_overdue_tasks(self, client, auth_headers):
        overdue_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        client.post(
            '/api/tasks',
            data=json.dumps({'title': '过期任务', 'due_date': overdue_date}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )
        future_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        client.post(
            '/api/tasks',
            data=json.dumps({'title': '未来任务', 'due_date': future_date}),
            content_type='application/json',
            headers={'Authorization': auth_headers['Authorization']}
        )

        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['overdue_tasks'] == 1
        assert data['active_tasks'] == 2

    def test_stats_week_completed(self, client, auth_headers):
        for i in range(3):
            resp = client.post(
                '/api/tasks',
                data=json.dumps({'title': f'本周任务{i}'}),
                content_type='application/json',
                headers={'Authorization': auth_headers['Authorization']}
            )
            task = json.loads(resp.data)
            client.put(
                f'/api/tasks/{task["id"]}/toggle',
                headers={'Authorization': auth_headers['Authorization']}
            )

        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['week_completed'] == 3

    def test_stats_daily_trend_structure(self, client, auth_headers):
        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data['daily_trend']) == 7
        for day in data['daily_trend']:
            assert 'date' in day
            assert 'label' in day
            assert 'completed' in day
            assert 'created' in day
            assert isinstance(day['completed'], int)
            assert isinstance(day['created'], int)

    def test_stats_user_isolation(self, client, auth_headers, auth_headers_alt, sample_task):
        client.put(
            f'/api/tasks/{sample_task["id"]}/toggle',
            headers={'Authorization': auth_headers['Authorization']}
        )

        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['total_tasks'] == 0
        assert data['total_completed'] == 0

    def test_stats_unauthorized(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code == 401

    def test_stats_avg_completion_time(self, client, auth_headers):
        for i in range(2):
            resp = client.post(
                '/api/tasks',
                data=json.dumps({'title': f'完成时间任务{i}'}),
                content_type='application/json',
                headers={'Authorization': auth_headers['Authorization']}
            )
            task = json.loads(resp.data)
            client.put(
                f'/api/tasks/{task["id"]}/toggle',
                headers={'Authorization': auth_headers['Authorization']}
            )

        resp = client.get(
            '/api/stats',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert isinstance(data['avg_completion_minutes'], float)
        assert data['avg_completion_minutes'] >= 0
