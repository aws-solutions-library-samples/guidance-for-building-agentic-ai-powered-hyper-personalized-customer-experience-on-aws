import { v4 as uuidv4 } from 'uuid';
import type { Product } from '../store/types';
import { apiConfig } from '../config/api';

export interface ChatMessage {
  role: 'user' | 'ai' | 'system';
  text?: string;
  product?: Product;
  products?: Product[];
  timestamp?: Date;
  isStreaming?: boolean;
  rawText?: string; // For maintaining complete raw response during streaming
}

export interface FileUpload {
  filename: string;
  file_type: string;
  file_data: string; // base64 encoded
  size?: number;
}

export interface WebSocketMessage {
  type: 'chat' | 'file_upload';
  message?: string;
  files?: FileUpload[];
  user_id: string;
  customer_id?: string;
  timestamp?: string;
}

export interface WebSocketResponse {
  type: 'chat' | 'system' | 'error' | 'file_saved' | 'stream' | 'chat_complete' | 'message_boundary' | 'structured_recommendations';
  message: string;
  user_id: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private userId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: ((message: WebSocketResponse) => void)[] = [];
  private connectionHandlers: ((connected: boolean) => void)[] = [];

  constructor() {
    this.userId = this.generateUserId();
  }

  private generateUserId(): string {
    // Check if user ID exists in session storage
    let userId = sessionStorage.getItem('chat_user_id');
    if (!userId) {
      userId = uuidv4();
      sessionStorage.setItem('chat_user_id', userId);
    }
    return userId;
  }

  public getUserId(): string {
    return this.userId;
  }

  public connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // WebSocket connections must go directly to ALB, not CloudFront
        // Use environment variable for WebSocket endpoint or fall back to API base URL
        const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || apiConfig.baseUrl;
        
        // Construct WebSocket URL based on environment
        const baseUrl = wsBaseUrl.replace('https://', '').replace('http://', '');
        const wsUrl: string = `wss://${baseUrl}/ws/chat/${this.userId}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          this.reconnectAttempts = 0;
          this.notifyConnectionHandlers(true);
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const response: WebSocketResponse = JSON.parse(event.data);
            this.notifyMessageHandlers(response);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = () => {
          this.notifyConnectionHandlers(false);
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  public sendMessage(message: string, customerId?: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const wsMessage: WebSocketMessage = {
        type: 'chat',
        message: message,
        user_id: this.userId,
        timestamp: new Date().toISOString()
      };
      
      // Include customer_id only if user is logged in
      if (customerId) {
        wsMessage.customer_id = customerId;
      }
      
      this.ws.send(JSON.stringify(wsMessage));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  public sendFiles(files: FileUpload[], message?: string, customerId?: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const wsMessage: WebSocketMessage = {
        type: 'file_upload',
        message: message,
        files: files,
        user_id: this.userId,
        timestamp: new Date().toISOString()
      };
      
      // Include customer_id only if user is logged in
      if (customerId) {
        wsMessage.customer_id = customerId;
      }
      
      this.ws.send(JSON.stringify(wsMessage));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  public onMessage(handler: (message: WebSocketResponse) => void): () => void {
    this.messageHandlers.push(handler);
    return () => {
      const index = this.messageHandlers.indexOf(handler);
      if (index > -1) {
        this.messageHandlers.splice(index, 1);
      }
    };
  }

  public onConnectionChange(handler: (connected: boolean) => void): () => void {
    this.connectionHandlers.push(handler);
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  private notifyMessageHandlers(message: WebSocketResponse): void {
    this.messageHandlers.forEach(handler => handler(message));
  }

  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => handler(connected));
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(error => {
          console.error('Reconnection failed:', error);
        });
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  // Utility function to convert File to base64
  public static fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        const result = reader.result as string;
        // Remove the data:mime/type;base64, prefix
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = error => reject(error);
    });
  }
}

// Create a singleton instance
export const websocketService = new WebSocketService();
