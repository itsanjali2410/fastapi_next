'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { useTaskSocket } from '@/hooks/useTaskSocket';
import { useSocket } from '@/contexts/SocketContext';

interface TaskSummary {
  id: string;
  status: string;
}

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { socket, connected } = useSocket();
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [unreadChats, setUnreadChats] = useState<number>(0);

  const fetchPendingCount = useCallback(async () => {
    try {
      const data = await apiClient.get<TaskSummary[]>('/tasks?status=pending&limit=100');
      setPendingCount(data.length);
    } catch (error) {
      console.error('Failed to fetch pending tasks count', error);
    }
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      fetchPendingCount();
    }, 0);
    return () => clearTimeout(id);
  }, [fetchPendingCount]);

  const fetchUnreadChats = useCallback(async () => {
    try {
      const data = await apiClient.get<Array<{ unread_count?: number }>>('/chat/list');
      const totalUnread = data.reduce((sum, chat) => sum + (chat.unread_count || 0), 0);
      setUnreadChats(totalUnread);
    } catch (error) {
      console.error('Failed to fetch unread chats count', error);
    }
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      fetchUnreadChats();
    }, 0);
    return () => clearTimeout(id);
  }, [fetchUnreadChats]);

  useEffect(() => {
    if (!socket || !connected) return;

    const handleNewMessage = (message: { sender_id: string; receiver_id?: string; group_chat_id?: string }) => {
      // Assume any incoming message increments unread until list refresh logic handles it
      if (message.sender_id !== user?.id) {
        setUnreadChats((prev) => prev + 1);
      }
    };

    const handleChatListUpdate = () => {
      fetchUnreadChats();
    };

    socket.on('new_message', handleNewMessage);
    socket.on('chat_list_update', handleChatListUpdate);

    return () => {
      socket.off('new_message', handleNewMessage);
      socket.off('chat_list_update', handleChatListUpdate);
    };
  }, [socket, connected, user?.id, fetchUnreadChats]);

  useTaskSocket(
    (task) => {
      if (task.status === 'pending') {
        setPendingCount((prev) => prev + 1);
      }
    },
    undefined,
    ({ status, old_status }) => {
      if (old_status === 'pending' && status !== 'pending') {
        setPendingCount((prev) => Math.max(0, prev - 1));
      } else if (old_status !== 'pending' && status === 'pending') {
        setPendingCount((prev) => prev + 1);
      }
    },
    undefined,
    () => {
      // Deleted task might have been pending; refresh to stay accurate
      fetchPendingCount();
    },
    undefined
  );

  const isActive = (path: string) => pathname === path || pathname.startsWith(path);

  const navItems = [
    { href: '/chat', label: 'Chats', icon: '💬' },
    { href: '/tasks', label: 'Tasks', icon: '✓' },
    ...(user?.role === 'admin' ? [{ href: '/admin/users', label: 'Users', icon: '👥' }] : []),
    ...(user?.role === 'admin' ? [{ href: '/admin/invites', label: 'Invite', icon: '🔗' }] : []),
    ...(user?.role === 'admin' ? [{ href: '/admin/settings', label: 'Settings', icon: '⚙️' }] : []),
    { href: '/profile', label: 'Profile', icon: '👤' },
  ];

  return (
    <div 
      className={`text-white min-h-screen flex flex-col transition-all duration-300 relative`}
      style={{ 
        backgroundColor: '#073B82',
        width: collapsed ? '80px' : '256px'
      }}
    >
      {/* Header with Toggle */}
      <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: '#0D58A6' }}>
        {!collapsed && (
          <>
            <h1 className="text-xl font-bold">Platform</h1>
            {user && user.name && (
              <p className="text-xs mt-1" style={{ color: '#B2E9FB' }}>{user.name}</p>
            )}
          </>
        )}
        <button
          onClick={onToggle}
          className="p-2 rounded hover:bg-white/10 transition"
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          <span className="text-xl">☰</span>
        </button>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center ${collapsed ? 'justify-center' : 'space-x-3'} px-4 py-3 rounded-lg transition group relative ${
              isActive(item.href)
                ? 'text-white'
                : 'text-white/70 hover:bg-white/10 hover:text-white'
            }`}
            style={isActive(item.href) ? { backgroundColor: '#00AEEF' } : {}}
            title={collapsed ? item.label : undefined}
          >
            <span className="text-lg">{item.icon}</span>
            {!collapsed && <span className="flex-1">{item.label}</span>}
            {item.href === '/chat' && unreadChats > 0 && (
              <span
                className={`${
                  collapsed ? 'absolute right-3 top-1/2 -translate-y-1/2' : 'ml-auto'
                } inline-flex items-center justify-center rounded-full bg-red-500 text-white text-xs min-w-[24px] px-2 py-0.5`}
              >
                {unreadChats > 99 ? '99+' : unreadChats}
              </span>
            )}
            {item.href === '/tasks' && pendingCount > 0 && (
              <span
                className={`${
                  collapsed ? 'absolute right-3 top-1/2 -translate-y-1/2' : 'ml-auto'
                } inline-flex items-center justify-center rounded-full bg-red-500 text-white text-xs min-w-[24px] px-2 py-0.5`}
              >
                {pendingCount > 99 ? '99+' : pendingCount}
              </span>
            )}
            {collapsed && (
              <div className="absolute left-full ml-2 px-2 py-1 bg-gray-800 text-white text-sm rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50">
                {item.label}
              </div>
            )}
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t" style={{ borderColor: '#0D58A6' }}>
        <button
          onClick={logout}
          className={`w-full flex items-center ${collapsed ? 'justify-center' : 'space-x-3'} px-4 py-3 rounded-lg text-white/70 hover:bg-white/10 hover:text-white transition group relative`}
          title={collapsed ? "Logout" : undefined}
        >
          <span>🚪</span>
          {!collapsed && <span>Logout</span>}
          {collapsed && (
            <div className="absolute left-full ml-2 px-2 py-1 bg-gray-800 text-white text-sm rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50">
              Logout
            </div>
          )}
        </button>
      </div>
    </div>
  );
}

