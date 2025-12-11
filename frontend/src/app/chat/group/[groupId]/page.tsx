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
        
        // Mark all messages as read when opening group
        try {
          await apiClient.post(`/chat/groups/${groupId}/mark-read`);
        } catch (error) {
          console.error('Failed to mark messages as read:', error);
        }
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

