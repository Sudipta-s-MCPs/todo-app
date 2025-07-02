import { api } from './api';
import type { Workspace, WorkspaceCreate, WorkspaceUpdate, WorkspacesResponse, WorkspaceMember } from '../types';

export const workspaceService = {
  async getWorkspaces(params?: {
    skip?: number;
    limit?: number;
    search?: string;
  }): Promise<WorkspacesResponse> {
    const response = await api.get<WorkspacesResponse>('/workspaces/', { params });
    return response.data;
  },

  async getWorkspace(id: string): Promise<Workspace> {
    const response = await api.get<Workspace>(`/workspaces/${id}`);
    return response.data;
  },

  async createWorkspace(data: WorkspaceCreate): Promise<Workspace> {
    const response = await api.post<Workspace>('/workspaces/', data);
    return response.data;
  },

  async updateWorkspace(id: string, data: WorkspaceUpdate): Promise<Workspace> {
    const response = await api.put<Workspace>(`/workspaces/${id}`, data);
    return response.data;
  },

  async deleteWorkspace(id: string): Promise<void> {
    await api.delete(`/workspaces/${id}`);
  },

  async getWorkspaceMembers(id: string): Promise<WorkspaceMember[]> {
    const response = await api.get<WorkspaceMember[]>(`/workspaces/${id}/members`);
    return response.data;
  },

  async addMember(workspaceId: string, userId: string, role: 'viewer' | 'member' | 'admin' = 'member'): Promise<WorkspaceMember> {
    const response = await api.post<WorkspaceMember>(`/workspaces/${workspaceId}/members`, {
      user_id: userId,
      role,
    });
    return response.data;
  },

  async updateMember(workspaceId: string, userId: string, role: 'viewer' | 'member' | 'admin'): Promise<WorkspaceMember> {
    const response = await api.put<WorkspaceMember>(`/workspaces/${workspaceId}/members/${userId}`, {
      role,
    });
    return response.data;
  },

  async removeMember(workspaceId: string, userId: string): Promise<void> {
    await api.delete(`/workspaces/${workspaceId}/members/${userId}`);
  },

  async inviteMember(workspaceId: string, email: string, role: 'viewer' | 'member' | 'admin' = 'member'): Promise<WorkspaceMember> {
    const response = await api.post<WorkspaceMember>(`/workspaces/${workspaceId}/members/invite`, {
      email,
      role,
    });
    return response.data;
  },

  async updateMemberRole(workspaceId: string, userId: string, role: 'viewer' | 'member' | 'admin'): Promise<WorkspaceMember> {
    return this.updateMember(workspaceId, userId, role);
  },

  async leaveWorkspace(workspaceId: string): Promise<void> {
    await api.post(`/workspaces/${workspaceId}/leave`);
  },
};