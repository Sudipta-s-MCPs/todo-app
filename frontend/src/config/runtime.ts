// Runtime configuration handler
// This file reads configuration from the runtime-injected config.js file

interface RuntimeConfig {
  API_URL: string;
}

declare global {
  interface Window {
    __RUNTIME_CONFIG__?: RuntimeConfig;
  }
}

// Get runtime config with fallbacks
export function getRuntimeConfig(): RuntimeConfig {
  // First try runtime config (from docker-entrypoint.sh)
  if (window.__RUNTIME_CONFIG__) {
    return window.__RUNTIME_CONFIG__;
  }
  
  // Then try Vite env (for local development)
  if (import.meta.env.VITE_API_URL) {
    return {
      API_URL: import.meta.env.VITE_API_URL
    };
  }
  
  // Finally use default
  return {
    API_URL: 'http://localhost:5482/api/v1'
  };
}

// Export convenience getter
export const config = getRuntimeConfig();

// Helper function to get WebSocket URL from API URL
export function getWebSocketUrl(): string {
  const apiUrl = config.API_URL;
  
  // Remove /api/v1 suffix if present
  const baseUrl = apiUrl.replace(/\/api\/v1\/?$/, '');
  
  // Convert http/https to ws/wss
  const wsUrl = baseUrl
    .replace(/^https:/, 'wss:')
    .replace(/^http:/, 'ws:');
  
  return `${wsUrl}/ws`;
}