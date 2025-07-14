import { api } from './api';
import type { List, ListCreate, ListUpdate } from '../types';

export const listService = {
  async getListsByWorkspace(workspaceId: string): Promise<List[]> {
    const response = await api.get<List[]>(`/workspaces/${workspaceId}/lists`);
    return response.data;
  },

  // Note: Individual list fetch endpoint not implemented in backend
  // Use getListsByWorkspace and filter client-side if needed
  async getList(workspaceId: string, listId: string): Promise<List> {
    const lists = await this.getListsByWorkspace(workspaceId);
    const list = lists.find(l => l.id === listId);
    if (!list) {
      throw new Error('List not found');
    }
    return list;
  },

  async createList(workspaceId: string, data: ListCreate): Promise<List> {
    const response = await api.post<List>(`/workspaces/${workspaceId}/lists`, data);
    return response.data;
  },

  async updateList(workspaceId: string, listId: string, data: ListUpdate): Promise<List> {
    const response = await api.put<List>(`/workspaces/${workspaceId}/lists/${listId}`, data);
    return response.data;
  },

  async deleteList(workspaceId: string, listId: string): Promise<void> {
    await api.delete(`/workspaces/${workspaceId}/lists/${listId}`);
  },

  async reorderLists(workspaceId: string, listOrders: { id: string; position: number }[]): Promise<void> {
    await api.put(`/workspaces/${workspaceId}/lists/reorder`, { orders: listOrders });
  },
};