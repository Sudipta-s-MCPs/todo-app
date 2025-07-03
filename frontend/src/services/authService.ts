import { api, createFormData } from './api';
import type { AuthResponse, LoginCredentials, RegisterCredentials, User, UserDevice } from '../types';

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const formData = createFormData({
      username: credentials.email,
      password: credentials.password,
    });
    
    const response = await api.post<AuthResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    return response.data;
  },
  
  async register(credentials: RegisterCredentials): Promise<User> {
    const response = await api.post<User>('/auth/register', credentials);
    return response.data;
  },
  
  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      // Ignore logout errors
    }
  },
  
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },
  
  async updateProfile(data: Partial<User>): Promise<User> {
    const params = new URLSearchParams();
    if (data.name) params.append('name', data.name);
    if (data.timezone) params.append('timezone', data.timezone);
    if (data.locale) params.append('locale', data.locale);
    if (data.avatar_url !== undefined) params.append('avatar_url', data.avatar_url || '');
    
    const response = await api.put<User>('/auth/me', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },
  
  async updatePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },
  
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },
  
  async requestPasswordReset(email: string): Promise<void> {
    await api.post('/auth/password-reset', { email });
  },
  
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await api.post('/auth/password-reset/confirm', {
      token,
      new_password: newPassword,
    });
  },
  
  async getUserDevices(): Promise<UserDevice[]> {
    const response = await api.get<UserDevice[]>('/auth/devices');
    return response.data;
  },
  
  async revokeDevice(deviceId: string): Promise<void> {
    await api.delete(`/auth/devices/${deviceId}`);
  },
  
  async uploadAvatar(file: File): Promise<{ avatar_url: string }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post<{ avatar_url: string }>('/auth/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};