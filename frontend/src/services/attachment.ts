import { httpClient, API_BASE_URL } from './client';
import { handleUnauthorized } from './auth';
import type { Attachment, AttachmentBlobResult } from './types';

export const attachmentApi = {
  async uploadAttachment(taskId: number, file: File): Promise<Attachment> {
    const formData = new FormData();
    formData.append('file', file);
    return httpClient.request<Attachment>(`/tasks/${taskId}/attachments`, {
      method: 'POST',
      includeContentType: false,
      body: formData,
    });
  },

  getAttachmentUrl(attachmentId: number): string {
    const token = localStorage.getItem('token');
    const url = `${API_BASE_URL}/tasks/attachments/${attachmentId}`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  getAttachmentDownloadUrl(attachmentId: number): string {
    const token = localStorage.getItem('token');
    const url = `${API_BASE_URL}/tasks/attachments/${attachmentId}/download`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  },

  async getAttachmentBlob(attachmentId: number): Promise<AttachmentBlobResult> {
    const response = await fetch(this.getAttachmentUrl(attachmentId));
    if (response.status === 401) {
      handleUnauthorized();
      throw new Error('未授权，请重新登录');
    }
    if (!response.ok) {
      try {
        const err = (await response.json()) as { error?: string };
        throw new Error(err.error || '获取文件失败');
      } catch (e) {
        if (e instanceof Error && (e.message === 'Failed to fetch' || e instanceof SyntaxError)) {
          throw new Error('获取文件失败');
        }
        throw e;
      }
    }
    const blob = await response.blob();
    const contentDisposition = response.headers.get('Content-Disposition') || '';
    let filename = `attachment-${attachmentId}`;
    const match = contentDisposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    if (match) {
      filename = decodeURIComponent(match[1].replace(/"/g, ''));
    }
    return { blob, filename };
  },

  async previewAttachment(attachmentId: number): Promise<void> {
    const { blob } = await this.getAttachmentBlob(attachmentId);
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  },

  async downloadAttachment(attachmentId: number): Promise<void> {
    const { blob, filename } = await this.getAttachmentBlob(attachmentId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },

  async deleteAttachment(attachmentId: number): Promise<void> {
    return httpClient.request<void>(`/tasks/attachments/${attachmentId}`, {
      method: 'DELETE',
    });
  },
};
