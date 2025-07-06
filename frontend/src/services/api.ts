import axios, { AxiosError } from 'axios';
import { useAuthStore } from '../store/authStore';
import { getDeviceInfo } from '../utils/deviceId';

// Get API URL from environment or default to local
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://todo-api.sudiptadhara.in/api/v1';

// Store device info
let deviceInfo: { deviceId: string; deviceName: string; deviceType: string } | null = null;

// Initialize device info
getDeviceInfo().then(info => {
  deviceInfo = info;
  console.log('Device info initialized:', info);
}).catch(err => {
  console.error('Failed to initialize device info:', err);
});

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token and device info
api.interceptors.request.use(
  async (config) => {
    // Add auth token
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add device info
    if (!deviceInfo) {
      try {
        deviceInfo = await getDeviceInfo();
      } catch (err) {
        console.error('Failed to get device info:', err);
      }
    }
    
    if (deviceInfo) {
      config.headers['X-Device-ID'] = deviceInfo.deviceId;
      config.headers['X-Device-Name'] = deviceInfo.deviceName;
      config.headers['X-Device-Type'] = deviceInfo.deviceType;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = useAuthStore.getState().refreshToken;
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token, refresh_token } = response.data;
          const { user } = useAuthStore.getState();
          
          if (user) {
            useAuthStore.getState().login(access_token, refresh_token, user);
          }
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, logout user
          useAuthStore.getState().logout();
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }
    
    return Promise.reject(error);
  }
);

// Helper function to handle form data for login
export const createFormData = (data: Record<string, any>): URLSearchParams => {
  const formData = new URLSearchParams();
  Object.keys(data).forEach(key => {
    formData.append(key, data[key]);
  });
  return formData;
};