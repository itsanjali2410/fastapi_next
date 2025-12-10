'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { EnhancedChat } from '@/components/EnhancedChat';

export default function ChatPage() {
  const params = useParams();
  const receiverId = params.receiverId as string;
  const [chatName, setChatName] = useState('User');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const user = await apiClient.get<{ name: string }>(`/users/${receiverId}`);
        if (user && user.name) {
          setChatName(user.name);
        }
      } catch (error: unknown) {
        const err = error as { detail?: string };
        console.error('Failed to fetch user:', err.detail || 'Unknown error');
        // Keep default "User" name if fetch fails
      } finally {
        setLoading(false);
      }
    };

    if (receiverId) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [receiverId]);

  if (loading) {
    return null;
  }

  return <EnhancedChat chatId={receiverId} chatName={chatName} receiverId={receiverId} />;
}

