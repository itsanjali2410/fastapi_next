'use client';

import React, { useEffect, useState } from 'react';
import { groupApi } from '@/lib/groupApi';
import { apiClient } from '@/lib/api';
import { useSocket } from '@/contexts/SocketContext';
import { colors } from '@/lib/colors';

export default function GroupMembersList({ groupId, currentUser }: { groupId: string; currentUser: any }) {
  const [group, setGroup] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [addingUserId, setAddingUserId] = useState('');
  const { socket } = useSocket();

  const fetchGroup = async () => {
    try {
      const g = await groupApi.getGroup(groupId);
      setGroup(g);
    } catch (err) {
      console.error('Failed to fetch group:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroup();
  }, [groupId]);

  useEffect(() => {
    if (!socket) return;
    const handleAdded = (data: any) => {
      if (data.groupId === groupId) fetchGroup();
    };
    const handleRemoved = (data: any) => {
      if (data.groupId === groupId) fetchGroup();
    };
    socket.on('group_member_added', handleAdded);
    socket.on('group_member_removed', handleRemoved);
    return () => {
      socket.off('group_member_added', handleAdded);
      socket.off('group_member_removed', handleRemoved);
    };
  }, [socket, groupId]);

  const handleAdd = async () => {
    if (!addingUserId) return;
    try {
      const ids = addingUserId.split(',').map(s => s.trim()).filter(Boolean);
      await groupApi.addMembers(groupId, ids);
      setAddingUserId('');
      fetchGroup();
    } catch (err) {
      console.error('Failed to add members:', err);
    }
  };

  const handleRemove = async (userId: string) => {
    try {
      await groupApi.removeMember(groupId, userId);
      fetchGroup();
    } catch (err) {
      console.error('Failed to remove member:', err);
    }
  };

  if (loading) return <div className="text-xs text-gray-500">Loading...</div>;
  if (!group) return <div className="text-xs text-gray-500">Group not found</div>;

  const isAdmin = group.admins && group.admins.includes(currentUser?.id);

  return (
    <div>
      <div className="space-y-2">
        {group.members.map((m: string, idx: number) => (
          <div key={m} className="flex items-center justify-between p-2 border rounded" style={{ borderColor: colors.borderGray }}>
            <div>
              <div className="text-sm font-medium" style={{ color: colors.primaryText }}>{group.member_names?.[idx] || m}</div>
              <div className="text-xs" style={{ color: colors.secondaryText }}>{m}{group.admins && group.admins.includes(m) ? ' • Admin' : ''}</div>
            </div>
            <div>
              {(isAdmin || m === currentUser?.id) && (
                <button onClick={() => handleRemove(m)} className="px-2 py-1 text-xs rounded hover:bg-gray-100" style={{ color: colors.danger }}>
                  Remove
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {isAdmin && (
        <div className="mt-3">
          <p className="text-sm font-medium" style={{ color: colors.primaryText }}>Add member by ID (comma separated)</p>
          <div className="flex items-center space-x-2 mt-2">
            <input value={addingUserId} onChange={(e) => setAddingUserId(e.target.value)} className="flex-1 px-3 py-2 rounded border" style={{ borderColor: colors.borderGray }} />
            <button onClick={handleAdd} className="px-3 py-2 rounded text-white" style={{ backgroundColor: colors.primaryBlue }}>Add</button>
          </div>
        </div>
      )}
    </div>
  );
}
