'use client';

import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';

const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:8000';

interface Message {
  id: string;
  sender_id: string;
  receiver_id?: string;
  group_chat_id?: string;
  content: string;
  sender_name?: string;
  created_at: string;
}

export interface TypingEvent {
  sender_id: string;
  receiver_id: string;
  group_chat_id?: string;
  is_group: boolean;
}

interface SocketContextType {
  socket: Socket | null;
  connected: boolean;
  requestNotificationPermission: () => Promise<boolean>;
  showNotification: (title: string, options?: NotificationOptions) => void;
  onTyping: (callback: (event: TypingEvent) => void) => void;
  offTyping: (callback: (event: TypingEvent) => void) => void;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

export function SocketProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);
  const notificationPermissionRef = useRef<NotificationPermission>('default');
  const lastNotificationTimeRef = useRef<Map<string, number>>(new Map());

  // Request notification permission
  const requestNotificationPermission = useCallback(async (): Promise<boolean> => {
    if (!('Notification' in window)) {
      console.warn('This browser does not support desktop notifications');
      return false;
    }

    if (Notification.permission === 'granted') {
      notificationPermissionRef.current = 'granted';
      return true;
    }

    if (Notification.permission === 'denied') {
      notificationPermissionRef.current = 'denied';
      return false;
    }

    const permission = await Notification.requestPermission();
    notificationPermissionRef.current = permission;
    return permission === 'granted';
  }, []);

  // Show desktop notification
  const showNotification = useCallback((title: string, options?: NotificationOptions) => {
    if (!('Notification' in window)) {
      return;
    }

    if (notificationPermissionRef.current !== 'granted') {
      return;
    }

    // Prevent duplicate notifications within 2 seconds
    const notificationKey = `${title}-${options?.body || ''}`;
    const now = Date.now();
    const lastTime = lastNotificationTimeRef.current.get(notificationKey);
    
    if (lastTime && now - lastTime < 2000) {
      return;
    }
    
    lastNotificationTimeRef.current.set(notificationKey, now);

    const notification = new Notification(title, {
      icon: '/favicon.ico',
      badge: '/favicon.ico',
      tag: notificationKey,
      requireInteraction: false,
      ...options,
    });

    // Auto-close after 5 seconds
    setTimeout(() => {
      notification.close();
    }, 5000);

    // Handle click to focus window and navigate to chat
    notification.onclick = (event) => {
      event.preventDefault();
      window.focus();
      
      // Navigate to chat if data is provided
      if (options?.data) {
        const data = options.data as { chatId?: string; isGroup?: boolean };
        if (data.chatId) {
          const chatUrl = data.isGroup 
            ? `/chat/group/${data.chatId}`
            : `/chat/${data.chatId}`;
          window.location.href = chatUrl;
        }
      }
      
      notification.close();
    };
  }, []);

  // Initialize socket connection
  useEffect(() => {
    if (!user?.id) {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
        setSocket(null);
        setConnected(false);
      }
      return;
    }

    // Request notification permission on mount
    requestNotificationPermission();

    // Initialize socket connection
    const newSocket = io(SOCKET_URL, {
      auth: {
        user_id: user.id,
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    newSocket.on('connect', async () => {
      console.log('Socket connected:', newSocket.id);
      setConnected(true);
      // Update user status to online
      try {
        await apiClient.put('/users/status/me', { is_online: true });
      } catch (error) {
        console.error('Failed to update online status:', error);
      }
    });

    newSocket.on('disconnect', async () => {
      console.log('Socket disconnected');
      setConnected(false);
      // Update user status to offline
      try {
        await apiClient.put('/users/status/me', { is_online: false });
      } catch (error) {
        console.error('Failed to update offline status:', error);
      }
    });

    newSocket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
    });

    // Handle new messages with notifications
    const handleNewMessage = (message: Message) => {
      // Only show notification if message is not from current user
      if (message.sender_id !== user.id) {
        const isGroup = !!message.group_chat_id;
        const senderName = message.sender_name || 'Someone';
        const title = isGroup ? `${senderName} (Group)` : senderName;
        const body = message.content || 'New message';
        
        // Show desktop notification (will check permission internally)
        showNotification(title, {
          body: body.length > 100 ? body.substring(0, 100) + '...' : body,
          data: {
            messageId: message.id,
            chatId: message.group_chat_id || message.receiver_id,
            isGroup: isGroup,
          },
        });
      }
    };

    newSocket.on('new_message', handleNewMessage);

    socketRef.current = newSocket;
    setSocket(newSocket);

    return () => {
      newSocket.off('new_message', handleNewMessage);
      newSocket.close();
      socketRef.current = null;
      setSocket(null);
      setConnected(false);
    };
  }, [user?.id, showNotification, requestNotificationPermission]);

  // Typing event handlers
  const typingCallbacksRef = useRef<Set<(event: TypingEvent) => void>>(new Set());

  useEffect(() => {
    if (!socket || !connected) return;

    const handleTyping = (event: TypingEvent) => {
      typingCallbacksRef.current.forEach(callback => {
        callback(event);
      });
    };

    socket.on('typing', handleTyping);

    return () => {
      socket.off('typing', handleTyping);
    };
  }, [socket, connected]);

  const onTyping = useCallback((callback: (event: TypingEvent) => void) => {
    typingCallbacksRef.current.add(callback);
  }, []);

  const offTyping = useCallback((callback: (event: TypingEvent) => void) => {
    typingCallbacksRef.current.delete(callback);
  }, []);

  return (
    <SocketContext.Provider
      value={{
        socket,
        connected,
        requestNotificationPermission,
        showNotification,
        onTyping,
        offTyping,
      }}
    >
      {children}
    </SocketContext.Provider>
  );
}

export function useSocket() {
  const context = useContext(SocketContext);
  if (context === undefined) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
}

