import { api } from './api';
import type { Task, TaskCreate, TaskUpdate } from '../types';

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

  async createTask(data: TaskCreate & { list_id?: string }): Promise<Task> {
    if (data.list_id) {
      const { list_id, ...taskData } = data;
      const response = await api.post<Task>(`/lists/${list_id}/tasks`, taskData);
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
};