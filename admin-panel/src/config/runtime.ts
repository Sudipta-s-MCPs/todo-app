// Runtime configuration handler for admin panel
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