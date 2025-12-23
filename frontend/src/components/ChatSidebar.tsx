'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { colors } from '@/lib/colors';
import { useSocket } from '@/contexts/SocketContext';
import { formatHeaderTime } from '@/lib/timeUtils';

interface ChatSidebarProps {
  isMobile?: boolean;
  onOpenSidebar?: () => void;
}

interface Chat {
  id: string;
  type?: "personal" | "group";
  chatId?: string;
  receiver_id?: string;
  receiver_name?: string;
  group_chat_id?: string;
  name: string;
  last_message?: string;
  last_message_time?: string;
  lastMessage?: {
    content: string;
    createdAt: string | null;
  };
  unread_count?: number;
  is_group?: boolean;
  avatar?: string;
}

interface UserStatus {
  user_id: string;
  is_online: boolean;
  last_seen: string;
  user_name?: string;
}

export function ChatSidebar({ isMobile = false, onOpenSidebar }: ChatSidebarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { socket, connected } = useSocket();
  const [allChats, setAllChats] = useState<Chat[]>([]);
  const [userStatuses, setUserStatuses] = useState<Record<string, UserStatus>>({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch initial data and normalize into single list
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [chatsData, statusesData, usersData] = await Promise.all([
          apiClient.get<Chat[]>('/chat/list').catch(() => []),
          apiClient.get<{ statuses: UserStatus[] }>('/users/status').catch(() => ({ statuses: [] })),
          apiClient.get<Array<{ id: string; name: string; email: string }>>('/users').catch(() => []),
        ]);

        // Create status map
        const statusMap: Record<string, UserStatus> = {};
        (statusesData.statuses || []).forEach((status: UserStatus) => {
          statusMap[status.user_id] = status;
        });
        setUserStatuses(statusMap);

        // Normalize chats from unified endpoint
        const normalizedChats: Chat[] = chatsData.map((chat: Chat) => ({
          ...chat,
          id: chat.chatId || chat.id || chat.receiver_id || chat.group_chat_id || '',
          name: chat.receiver_name || chat.name || 'Unknown',
          is_group: chat.type === 'group' || chat.is_group || false,
        }));

        // Create a set of user IDs that already have chats
        const existingChatUserIds = new Set(
          normalizedChats
            .filter((chat: Chat) => chat.type === 'personal' || !chat.is_group)
            .map((chat: Chat) => chat.receiver_id || chat.id)
            .filter(Boolean)
        );

        // Normalize org users that don't have chats yet
        const orgUsersWithoutChats: Chat[] = (usersData || [])
          .filter((u: { id: string; name: string; email: string }) => u.id !== user?.id && !existingChatUserIds.has(u.id))
          .map((orgUser: { id: string; name: string; email: string }) => ({
            id: orgUser.id,
            type: 'personal',
            chatId: orgUser.id,
            receiver_id: orgUser.id,
            receiver_name: orgUser.name,
            name: orgUser.name,
            lastMessage: {
              content: '',
              createdAt: null,
            },
            last_message: undefined,
            last_message_time: undefined,

            is_group: false,
          }));

        // Merge all chats
        const merged = [...normalizedChats, ...orgUsersWithoutChats];

        // Sort using lastMessage.createdAt (MOST IMPORTANT FIX)
        const sorted = merged.sort((a, b) => {
          const timeA = a.lastMessage?.createdAt
            ? new Date(a.lastMessage.createdAt).getTime()
            : (a.last_message_time ? new Date(a.last_message_time).getTime() : 0);

          const timeB = b.lastMessage?.createdAt
            ? new Date(b.lastMessage.createdAt).getTime()
            : (b.last_message_time ? new Date(b.last_message_time).getTime() : 0);

          // Latest first (descending order)
          return timeB - timeA;
        });

        setAllChats(sorted);
      } catch (error) {
        console.error('Failed to fetch chat data:', error);
      } finally {
        setLoading(false);
      }
    };

    if (user?.org_id) {
      fetchData();
    }
  }, [user]);

  // Play notification sound for new messages
  const playNotification = () => {
    try {
      const audio = new Audio('/80921__justinbw__buttonchime02up.wav');
      audio.volume = 0.5;
      audio.play().catch(() => {
        // Ignore audio play errors
      });
    } catch {
      // Ignore audio errors
    }
  };

  // Real-time updates via Socket.io

  useEffect(() => {
    if (!socket || !connected || !user?.org_id) return;

    const refreshChatList = async () => {
      try {
        const [chatsData, statusesData, usersData] = await Promise.all([
          apiClient.get<Chat[]>('/chat/list').catch(() => []),
          apiClient.get<{ statuses: UserStatus[] }>('/users/status').catch(() => ({ statuses: [] })),
          apiClient.get<Array<{ id: string; name: string; email: string }>>('/users').catch(() => []),
        ]);

        // Update status map
        const statusMap: Record<string, UserStatus> = {};
        (statusesData.statuses || []).forEach((status: UserStatus) => {
          statusMap[status.user_id] = status;
        });
        setUserStatuses(statusMap);

        // Normalize chats from unified endpoint
        const normalizedChats: Chat[] = chatsData.map((chat: Chat) => ({
          ...chat,
          id: chat.chatId || chat.id || chat.receiver_id || chat.group_chat_id || '',
          name: chat.receiver_name || chat.name || 'Unknown',
          is_group: chat.type === 'group' || chat.is_group || false,
        }));

        // Create a set of user IDs that already have chats
        const existingChatUserIds = new Set(
          normalizedChats
            .filter((chat: Chat) => chat.type === 'personal' || !chat.is_group)
            .map((chat: Chat) => chat.receiver_id || chat.id)
            .filter(Boolean)
        );

        // Normalize org users that don't have chats yet
        const orgUsersWithoutChats: Chat[] = (usersData || [])
          .filter((u: { id: string; name: string; email: string }) => u.id !== user?.id && !existingChatUserIds.has(u.id))
          .map((orgUser: { id: string; name: string; email: string }) => ({
            id: orgUser.id,
            type: 'personal',
            chatId: orgUser.id,
            receiver_id: orgUser.id,
            receiver_name: orgUser.name,
            name: orgUser.name,
            lastMessage: {
              content: '',
              createdAt: null,
            },
            last_message: undefined,
            last_message_time: undefined,
            is_group: false,
          }));

        // Merge all chats
        const merged = [...normalizedChats, ...orgUsersWithoutChats];

        // Sort using lastMessage.createdAt (MOST IMPORTANT FIX)
        const sorted = merged.sort((a, b) => {
          const timeA = a.lastMessage?.createdAt
            ? new Date(a.lastMessage.createdAt).getTime()
            : (a.last_message_time ? new Date(a.last_message_time).getTime() : 0);

          const timeB = b.lastMessage?.createdAt
            ? new Date(b.lastMessage.createdAt).getTime()
            : (b.last_message_time ? new Date(b.last_message_time).getTime() : 0);

          // Latest first (descending order)
          return timeB - timeA;
        });

        setAllChats(sorted);
      } catch (error) {
        console.error('Failed to refresh chat list:', error);
      }
    };

    const handleUserStatusUpdate = (status: UserStatus) => {
      setUserStatuses(prev => ({
        ...prev,
        [status.user_id]: status,
      }));
    };

    interface NewMessageEvent {
      sender_id: string;
      receiver_id?: string;
      group_chat_id?: string;
      content?: string;
    }

    const handleNewMessage = (message: NewMessageEvent) => {
      // Only play notification if message is not from current user
      if (message.sender_id !== user?.id) {
        playNotification();
      }
      refreshChatList();
    };

    const handleGroupMessage = (message: NewMessageEvent) => {
      // Treat group messages the same for sounds/unread refresh
      if (message.sender_id !== user?.id) {
        playNotification();
      }
      refreshChatList();
    };

    const handleChatListUpdate = () => {
      refreshChatList();
    };

    const handleGroupUnreadUpdate = (data: { groupId: string; unreadCount: number }) => {
      setAllChats(prev =>
        prev.map(chat => {
          if (chat.group_chat_id === data.groupId) {
            if (data.unreadCount > 0) {
              return { ...chat, unread_count: data.unreadCount };
            }
            // 🔥 REMOVE unread_count completely
            const { unread_count, ...rest } = chat;
            return rest;
          }
          return chat;
        })
      );
    };


    socket.on('user_status_update', handleUserStatusUpdate);
    socket.on('new_message', handleNewMessage);
    socket.on('group_message', handleGroupMessage);
    socket.on('chat_list_update', handleChatListUpdate);
    socket.on('group_unread_update', handleGroupUnreadUpdate);

    return () => {
      socket.off('user_status_update', handleUserStatusUpdate);
      socket.off('new_message', handleNewMessage);
      socket.off('group_message', handleGroupMessage);
      socket.off('chat_list_update', handleChatListUpdate);
      socket.off('group_unread_update', handleGroupUnreadUpdate);
    };
  }, [socket, connected, user]);

  const isActive = (chatId: string, isGroup: boolean) => {
    if (isGroup) {
      return pathname === `/chat/group/${chatId}`;
    }
    return pathname === `/chat/${chatId}`;
  };

  const filteredChats = allChats.filter(chat =>
    chat.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusIndicator = (userId?: string) => {
    if (!userId) return null;
    const status = userStatuses[userId];
    if (!status) return null;

    if (status.is_online) {
      return (
        <div className="absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white" style={{ backgroundColor: colors.success }}></div>
      );
    }
    return null;
  };

  const formatLastSeen = (lastSeen?: string) => {
    if (!lastSeen) return 'Offline';
    // Use IST-aware formatting from formatHeaderTime
    const formatted = formatHeaderTime(lastSeen);
    // formatHeaderTime already returns 'just now', 'X min ago', 'X hour(s) ago', or time/date in IST
    return `Last seen ${formatted}`;
  };

  if (loading) {
    return (
      <div className="w-80 bg-white border-r" style={{ borderColor: colors.borderGray }}>
        <div className="p-4 flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: colors.primaryBlue }}></div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`${isMobile ? 'w-full' : 'w-80'} bg-white border-r flex flex-col`}
      style={{ borderColor: colors.borderGray, height: '100dvh' }}
    >
      {/* Header */}
      <div className="p-4 border-b" style={{ borderColor: colors.borderGray }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            {isMobile && (
              <button
                onClick={onOpenSidebar}
                className="p-2 rounded-lg hover:bg-gray-100 transition"
                aria-label="Open navigation"
              >
                ☰
              </button>
            )}
            <h2 className="text-lg font-semibold" style={{ color: colors.primaryText }}>Chats</h2>
          </div>
          <Link
            href="/chat/create-group"
            className="p-2 rounded-lg hover:bg-gray-100 transition"
            title="Create Group"
          >
            <span className="text-xl">➕</span>
          </Link>
        </div>
        <input
          type="text"
          placeholder="Search chats..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-3 py-2 rounded-lg outline-none text-sm"
          style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
        />
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2">
          {filteredChats.length > 0 ? (
            filteredChats.map((chat) => {
              const status = chat.receiver_id ? userStatuses[chat.receiver_id] : undefined;
              const chatId = chat.chatId || chat.id || chat.receiver_id || chat.group_chat_id || '';
              const chatUrl = chat.is_group
                ? `/chat/group/${chatId}`
                : `/chat/${chatId}`;

              return (
                <Link
                  key={chat.id || chatId}
                  href={chatUrl}
                  className={`block p-3 rounded-lg mb-1 transition ${isActive(chatId, chat.is_group || false)
                      ? 'bg-blue-50'
                      : 'hover:bg-gray-50'
                    }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <div
                        className="w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold"
                        style={{
                          backgroundColor: chat.is_group ? colors.darkBlue : colors.chatAccent
                        }}
                      >
                        {chat.name.charAt(0).toUpperCase()}
                      </div>
                      {!chat.is_group && getStatusIndicator(chat.receiver_id || chat.chatId)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-sm truncate" style={{ color: colors.primaryText }}>
                          {chat.name}
                        </h4>
                        {(chat.lastMessage?.createdAt || chat.last_message_time) ? (
                          <span className="text-xs ml-2 whitespace-nowrap" style={{ color: colors.secondaryText }}>
                            {formatHeaderTime(chat.lastMessage?.createdAt || chat.last_message_time)}
                          </span>
                        ) : !chat.is_group && status && (
                          <span className="text-xs ml-2 whitespace-nowrap" style={{ color: colors.secondaryText }}>
                            {status.is_online ? 'Online' : formatLastSeen(status.last_seen)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <p className="text-sm truncate" style={{ color: colors.secondaryText }}>
                          {chat.lastMessage?.content || chat.last_message || 'No messages yet'}
                        </p>
                        {typeof chat.unread_count === 'number' && chat.unread_count > 0 && (
                          <span
                            className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium text-white whitespace-nowrap"
                            style={{ backgroundColor: colors.chatAccent }}
                          >
                            {chat.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })
          ) : (
            <div className="p-8 text-center" style={{ color: colors.secondaryText }}>
              <p>No chats found. Start a conversation!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

