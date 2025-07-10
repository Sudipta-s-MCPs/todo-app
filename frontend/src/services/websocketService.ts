import { getWebSocketUrl } from '../config/runtime';

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

  connect(token: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    const baseWsUrl = getWebSocketUrl();
    const wsUrl = `${baseWsUrl}?token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.scheduleReconnect();
    }
  }

  disconnect() {
    this.isIntentionallyClosed = true;
    this.cleanup();
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
      this.cleanup();
      
      if (!this.isIntentionallyClosed) {
        this.scheduleReconnect();
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
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const websocketService = new WebSocketService();