import { api } from './api';
import type { Task, TaskCreate, TaskUpdate, TaskAttachment } from '../types';

export const taskService = {
  async getListTasks(
    listId: string,
    params?: {
      status?: ('todo' | 'in_progress' | 'completed' | 'archived')[];
      priority?: ('low' | 'medium' | 'high')[];
      limit?: number;
      offset?: number;
    }
  ): Promise<Task[]> {
    const response = await api.get<Task[]>(`/lists/${listId}/tasks`, { params });
    return response.data;
  },

  async searchTasks(params?: {
    query?: string;
    workspace_id?: string;
    list_ids?: string[];
    status?: ('todo' | 'in_progress' | 'completed' | 'archived')[];
    priority?: ('low' | 'medium' | 'high')[];
    assigned_to?: string[];
    created_by?: string;
    due_before?: string;
    due_after?: string;
    created_before?: string;
    created_after?: string;
    has_attachments?: boolean;
    parent_task_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<Task[]> {
    const response = await api.post<Task[]>('/tasks/search', params || {});
    return response.data;
  },

  async getTask(id: string): Promise<Task> {
    const response = await api.get<Task>(`/tasks/${id}`);
    return response.data;
  },

  async createTask(data: TaskCreate & { list_id?: string; force_create?: boolean }): Promise<Task> {
    if (data.list_id) {
      const { list_id, force_create, ...taskData } = data;
      const url = force_create ? `/lists/${list_id}/tasks?force_create=true` : `/lists/${list_id}/tasks`;
      const response = await api.post<Task>(url, taskData);
      return response.data;
    }
    const response = await api.post<Task>('/tasks', data);
    return response.data;
  },

  async updateTask(id: string, data: TaskUpdate): Promise<Task> {
    const response = await api.put<Task>(`/tasks/${id}`, data);
    return response.data;
  },

  async deleteTask(id: string): Promise<void> {
    await api.delete(`/tasks/${id}`);
  },

  async assignTask(taskId: string, userId: string): Promise<Task> {
    const response = await api.post<Task>(`/tasks/${taskId}/assign/${userId}`);
    return response.data;
  },

  async unassignTask(taskId: string, userId: string): Promise<Task> {
    const response = await api.delete<Task>(`/tasks/${taskId}/assign/${userId}`);
    return response.data;
  },

  async searchSimilar(title: string, description?: string): Promise<Task[]> {
    const response = await api.post<Task[]>('/tasks/search/similar', {
      title,
      description,
    });
    return response.data;
  },

  // Attachment methods
  async uploadAttachment(
    taskId: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<TaskAttachment> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<TaskAttachment>(
      `/tasks/${taskId}/attachments`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        },
      }
    );
    return response.data;
  },

  async getAttachments(taskId: string): Promise<TaskAttachment[]> {
    const response = await api.get<TaskAttachment[]>(`/tasks/${taskId}/attachments`);
    return response.data;
  },

  async downloadAttachment(attachmentId: string): Promise<Blob> {
    const response = await api.get(`/attachments/${attachmentId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  async deleteAttachment(attachmentId: string): Promise<void> {
    await api.delete(`/attachments/${attachmentId}`);
  },
};