import { api } from './api';

interface AttachmentResponse {
  id: string;
  task_id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  uploaded_by: string;
  uploaded_at: string;
  uploader_name?: string;
  download_url?: string;
  description?: string;
  url?: string; // For backwards compatibility
}

interface AttachmentMetadata {
  description?: string;
  [key: string]: any;
}

class AttachmentService {
  async uploadAttachment(
    taskId: string,
    file: File,
    metadata?: AttachmentMetadata
  ): Promise<AttachmentResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (metadata?.description) {
      formData.append('description', metadata.description);
    }

    const response = await api.post(
      `/tasks/${taskId}/attachments`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  async getAttachments(taskId: string): Promise<AttachmentResponse[]> {
    const response = await api.get(`/tasks/${taskId}/attachments`);
    return response.data;
  }

  async deleteAttachment(taskId: string, attachmentId: string): Promise<void> {
    await api.delete(`/tasks/${taskId}/attachments/${attachmentId}`);
  }

  async downloadAttachment(taskId: string, attachmentId: string): Promise<Blob> {
    const response = await api.get(
      `/tasks/${taskId}/attachments/${attachmentId}/download`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  }
}

export const attachmentService = new AttachmentService();