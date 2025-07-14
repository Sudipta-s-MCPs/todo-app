export type WebSocketEventType = 
  | 'task_created'
  | 'task_updated'
  | 'task_deleted'
  | 'workspace_created'
  | 'workspace_updated'
  | 'workspace_deleted'
  | 'workspace_member_added'
  | 'workspace_member_removed'
  | 'workspace_member_updated';

export interface WebSocketMessage {
  type: WebSocketEventType;
  resource_id: string;
  workspace_id?: string;
  data: any;
  timestamp: string;
  user_id: string;
}

export type WebSocketHandler = (message: WebSocketMessage) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectInterval: ReturnType<typeof setTimeout> | null = null;
  private handlers: Map<WebSocketEventType, Set<WebSocketHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private isIntentionallyClosed = false;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private pollingInterval: ReturnType<typeof setInterval> | null = null;
  private pollingMode = false;

  connect(token: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    // Use the same domain as the API
    const apiUrl = import.meta.env.VITE_API_URL || 'https://todo-api.sudiptadhara.in/api/v1';
    // WebSocket endpoint is at /api/v1/ws to work with proxy
    const deviceId = localStorage.getItem('device_id') || 'web-' + Math.random().toString(36).substr(2, 9);
    const wsUrl = apiUrl.replace(/^http/, 'ws') + '/ws?token=' + token + '&device_id=' + deviceId;

    try {
      this.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error('WebSocket connection error, using fallback mode:', error);
      this.startPollingFallback(token);
    }
  }

  disconnect() {
    this.isIntentionallyClosed = true;
    this.cleanup();
  }


  private setupEventHandlers() {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      
      // Setup ping to keep connection alive
      this.pingInterval = setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000); // Ping every 30 seconds
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        
        // Handle pong messages
        if (message.type === 'pong' as any) {
          return;
        }

        // Notify all handlers for this event type
        const handlers = this.handlers.get(message.type);
        if (handlers) {
          handlers.forEach(handler => {
            try {
              handler(message);
            } catch (error) {
              console.error('WebSocket handler error:', error);
            }
          });
        }
      } catch (error) {
        console.error('WebSocket message parsing error:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.ws = null;
      
      if (!this.isIntentionallyClosed) {
        // Try fallback mode if not in polling mode yet
        if (!this.pollingMode) {
          console.log('WebSocket disconnected, switching to polling mode');
          const token = localStorage.getItem('access_token');
          if (token) {
            this.startPollingFallback(token);
          }
        }
      }
    };
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectInterval = setTimeout(async () => {
      try {
        // Get fresh token
        const token = localStorage.getItem('access_token');
        if (token) {
          this.connect(token);
        }
      } catch (error) {
        console.error('Reconnection failed:', error);
        this.scheduleReconnect();
      }
    }, delay);
  }

  subscribe(eventType: WebSocketEventType, handler: WebSocketHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    
    this.handlers.get(eventType)!.add(handler);
    
    // Return unsubscribe function
    return () => {
      const handlers = this.handlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.handlers.delete(eventType);
        }
      }
    };
  }

  send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN || this.pollingMode;
  }

  private startPollingFallback(token: string) {
    console.log('Starting polling fallback for real-time updates');
    this.pollingMode = true;
    
    // Clear any existing polling
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
    
    // Start polling every 30 seconds
    this.pollingInterval = setInterval(() => {
      if (!this.isIntentionallyClosed) {
        this.checkForUpdates(token);
      }
    }, 30000);
  }

  private async checkForUpdates(token: string) {
    try {
      // This is a placeholder - in a real implementation, you'd call an API endpoint
      // that returns recent updates/events for the user
      console.log('Checking for updates (polling mode) with token:', token.substring(0, 10) + '...');
      
      // For now, we'll just emit a synthetic event to test the system
      // In production, this would fetch actual updates from an API endpoint
      
    } catch (error) {
      console.error('Error checking for updates:', error);
    }
  }

  private cleanup() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    if (this.reconnectInterval) {
      clearTimeout(this.reconnectInterval);
      this.reconnectInterval = null;
    }
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
    
    this.pollingMode = false;
  }
}

export const websocketService = new WebSocketService();