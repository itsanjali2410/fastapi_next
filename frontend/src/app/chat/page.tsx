'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
// import { useAuth } from '@/contexts/AuthContext';
import { colors } from '@/lib/colors';

interface Chat {
  id: string;
  receiver_id: string;
  receiver_name: string;
  last_message?: string;
  last_message_time?: string;
  unread_count?: number;
}

export default function ChatHomePage() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  // const { user } = useAuth();

  useEffect(() => {
    const fetchChats = async () => {
      try {
        const data = await apiClient.get<Chat[]>('/chat/list');
        setChats(data);
      } catch (error) {
        console.error('Failed to fetch chats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchChats();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: colors.primaryBlue }}></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: colors.lightBg }}>
      <div className="bg-white p-6" style={{ borderBottom: `1px solid ${colors.borderGray}` }}>
        <h1 className="text-2xl font-bold" style={{ color: colors.primaryText }}>Chats</h1>
      </div>

      <div className="flex-1 overflow-y-auto">
        {chats.length === 0 ? (
          <div className="flex items-center justify-center h-full" style={{ color: colors.secondaryText }}>
            <p>No chats yet. Start a conversation!</p>
          </div>
        ) : (
          <div style={{ borderTop: `1px solid ${colors.borderGray}` }}>
            {chats.map((chat, index) => (
              <Link
                key={chat.id ?? chat.receiver_id ?? `chat-${index}`}
                href={`/chat/${chat.receiver_id}`}
                className="block p-4 transition"
                style={{ borderBottom: `1px solid ${colors.borderGray}` }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = colors.white}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold" style={{ color: colors.primaryText }}>{chat.receiver_name}</h3>
                    {chat.last_message && (
                      <p className="text-sm mt-1 truncate" style={{ color: colors.secondaryText }}>
                        {chat.last_message}
                      </p>
                    )}
                  </div>
                  <div className="ml-4 text-right">
                    {chat.last_message_time && (
                      <p className="text-xs" style={{ color: colors.secondaryText }}>
                        {new Date(chat.last_message_time).toLocaleDateString()}
                      </p>
                    )}
                    {chat.unread_count && chat.unread_count > 0 && (
                      <span className="inline-block mt-1 text-white text-xs rounded-full px-2 py-1" style={{ backgroundColor: colors.chatAccent }}>
                        {chat.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

