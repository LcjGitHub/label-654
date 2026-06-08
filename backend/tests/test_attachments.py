import json
import os
import io
import pytest
import tempfile


class TestUploadAttachment:
    def test_upload_attachment_success(self, client, auth_headers, sample_task, app):
        data = {
            'file': (io.BytesIO(b'test file content'), 'test.txt')
        }
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert 'attachment' in data
        assert 'attachments' in data
        assert data['attachment']['original_filename'] == 'test.txt'
        assert data['attachment']['task_id'] == sample_task['id']
        assert data['attachment']['file_size'] > 0

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], data['attachment']['filename'])
        assert os.path.exists(file_path)

    def test_upload_image_attachment(self, client, auth_headers, sample_task):
        image_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        data = {
            'file': (io.BytesIO(image_content), 'image.png')
        }
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201
        result = json.loads(resp.data)
        assert result['attachment']['original_filename'] == 'image.png'

    def test_upload_pdf_attachment(self, client, auth_headers, sample_task):
        pdf_content = b'%PDF-1.4 test pdf content'
        data = {
            'file': (io.BytesIO(pdf_content), 'document.pdf')
        }
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 201

    def test_upload_no_file(self, client, auth_headers, sample_task):
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data={},
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert '未找到文件' in data['error']

    def test_upload_empty_filename(self, client, auth_headers, sample_task):
        data = {
            'file': (io.BytesIO(b'content'), '')
        }
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert '未选择文件' in data['error']

    def test_upload_invalid_file_type(self, client, auth_headers, sample_task):
        data = {
            'file': (io.BytesIO(b'malicious code'), 'script.exe')
        }
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert '不支持' in data['error']

    def test_upload_invalid_file_extension(self, client, auth_headers, sample_task):
        data = {
            'file': (io.BytesIO(b'some content'), 'badfile.xyz123')
        }
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 400

    def test_upload_task_not_found(self, client, auth_headers):
        data = {
            'file': (io.BytesIO(b'content'), 'test.txt')
        }
        resp = client.post(
            '/api/tasks/9999/attachments',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_upload_unauthorized(self, client, sample_task):
        data = {
            'file': (io.BytesIO(b'content'), 'test.txt')
        }
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=data,
            content_type='multipart/form-data'
        )
        assert resp.status_code == 401

    def test_upload_user_isolation(self, client, auth_headers, auth_headers_alt, sample_task):
        data = {
            'file': (io.BytesIO(b'content'), 'test.txt')
        }
        resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 404


class TestDownloadAttachment:
    def test_download_attachment(self, client, auth_headers, sample_task):
        upload_data = {
            'file': (io.BytesIO(b'download test content'), 'download.txt')
        }
        upload_resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=upload_data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        attachment = json.loads(upload_resp.data)['attachment']

        resp = client.get(
            f'/api/tasks/attachments/{attachment["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        assert resp.data == b'download test content'

    def test_download_attachment_as_file(self, client, auth_headers, sample_task):
        upload_data = {
            'file': (io.BytesIO(b'download as file content'), 'asfile.txt')
        }
        upload_resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=upload_data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        attachment = json.loads(upload_resp.data)['attachment']

        resp = client.get(
            f'/api/tasks/attachments/{attachment["id"]}/download',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        assert resp.data == b'download as file content'

    def test_download_attachment_not_found(self, client, auth_headers):
        resp = client.get(
            '/api/tasks/attachments/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_download_attachment_unauthorized(self, client, auth_headers, sample_task):
        upload_data = {
            'file': (io.BytesIO(b'content'), 'test.txt')
        }
        upload_resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=upload_data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        attachment = json.loads(upload_resp.data)['attachment']

        resp = client.get(f'/api/tasks/attachments/{attachment["id"]}')
        assert resp.status_code == 401

    def test_download_attachment_user_isolation(self, client, auth_headers, auth_headers_alt, sample_task):
        upload_data = {
            'file': (io.BytesIO(b'content'), 'test.txt')
        }
        upload_resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=upload_data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        attachment = json.loads(upload_resp.data)['attachment']

        resp = client.get(
            f'/api/tasks/attachments/{attachment["id"]}',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 404


class TestDeleteAttachment:
    def test_delete_attachment_success(self, client, auth_headers, sample_task, app):
        upload_data = {
            'file': (io.BytesIO(b'content to delete'), 'delete.txt')
        }
        upload_resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=upload_data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        attachment = json.loads(upload_resp.data)['attachment']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['filename'])
        assert os.path.exists(file_path)

        resp = client.delete(
            f'/api/tasks/attachments/{attachment["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert '成功' in data['message']
        assert not os.path.exists(file_path)

    def test_delete_attachment_not_found(self, client, auth_headers):
        resp = client.delete(
            '/api/tasks/attachments/9999',
            headers={'Authorization': auth_headers['Authorization']}
        )
        assert resp.status_code == 404

    def test_delete_attachment_unauthorized(self, client, auth_headers, sample_task):
        upload_data = {
            'file': (io.BytesIO(b'content'), 'test.txt')
        }
        upload_resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=upload_data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        attachment = json.loads(upload_resp.data)['attachment']

        resp = client.delete(f'/api/tasks/attachments/{attachment["id"]}')
        assert resp.status_code == 401

    def test_delete_attachment_user_isolation(self, client, auth_headers, auth_headers_alt, sample_task):
        upload_data = {
            'file': (io.BytesIO(b'content'), 'test.txt')
        }
        upload_resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=upload_data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        attachment = json.loads(upload_resp.data)['attachment']

        resp = client.delete(
            f'/api/tasks/attachments/{attachment["id"]}',
            headers={'Authorization': auth_headers_alt['Authorization']}
        )
        assert resp.status_code == 404

    def test_delete_task_removes_attachments(self, client, auth_headers, sample_task, app):
        upload_data = {
            'file': (io.BytesIO(b'content'), 'cascade.txt')
        }
        upload_resp = client.post(
            f'/api/tasks/{sample_task["id"]}/attachments',
            data=upload_data,
            content_type='multipart/form-data',
            headers={'Authorization': auth_headers['Authorization']}
        )
        attachment = json.loads(upload_resp.data)['attachment']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['filename'])

        client.delete(
            f'/api/tasks/{sample_task["id"]}',
            headers={'Authorization': auth_headers['Authorization']}
        )

        assert not os.path.exists(file_path)


class TestAllowedFile:
    def test_allowed_file_types(self):
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import app as todo_app

        allowed_exts = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'pdf',
                        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt',
                        'csv', 'zip', 'rar', 'md']
        for ext in allowed_exts:
            assert todo_app.allowed_file(f'file.{ext}') is True

    def test_disallowed_file_types(self):
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import app as todo_app

        disallowed_exts = ['exe', 'bat', 'sh', 'php', 'js', 'py', 'html']
        for ext in disallowed_exts:
            assert todo_app.allowed_file(f'file.{ext}') is False

    def test_no_extension_disallowed(self):
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import app as todo_app

        assert todo_app.allowed_file('noextension') is False
