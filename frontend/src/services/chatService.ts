import { api } from './api';
import type { ChatMessage, ChatConversation, ChatResponse } from '../types';

export const chatService = {
  async sendMessage(
    content: string,
    conversationId?: string | null
  ): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/chat/message', {
      content,
      conversation_id: conversationId,
    });
    return response.data;
  },

  async getConversations(): Promise<ChatConversation[]> {
    const response = await api.get<ChatConversation[]>('/chat/conversations');
    return response.data;
  },

  async getConversationMessages(conversationId: string): Promise<ChatMessage[]> {
    const response = await api.get<ChatMessage[]>(
      `/chat/conversations/${conversationId}/messages`
    );
    return response.data;
  },

  async deleteConversation(conversationId: string): Promise<void> {
    await api.delete(`/chat/conversations/${conversationId}`);
  },

  async getAiUsage(): Promise<{ used: number; limit: number }> {
    const response = await api.get<{ used: number; limit: number }>('/chat/ai-usage');
    return response.data;
  },

  // Pattern-based command execution (no AI)
  async executeCommand(command: string, args: string): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/chat/execute', {
      command,
      args,
    });
    return response.data;
  },
};