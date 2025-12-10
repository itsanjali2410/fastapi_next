'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { EnhancedChat } from '@/components/EnhancedChat';

export default function GroupChatPage() {
  const params = useParams();
  const groupId = params.groupId as string;
  const [groupName, setGroupName] = useState('Group');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGroup = async () => {
      try {
        const group = await apiClient.get<{ name: string }>(`/chat/groups/${groupId}`);
        setGroupName(group.name);
      } catch (error) {
        console.error('Failed to fetch group:', error);
      } finally {
        setLoading(false);
      }
    };

    if (groupId) {
      fetchGroup();
    }
  }, [groupId]);

  if (loading) {
    return null;
  }

  return <EnhancedChat chatId={groupId} chatName={groupName} isGroup={true} />;
}

