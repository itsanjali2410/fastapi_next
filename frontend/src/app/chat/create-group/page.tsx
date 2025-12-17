'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { colors } from '@/lib/colors';
import { LoadingSpinner } from '@/components/LoadingSpinner';

interface User {
  id: string;
  name: string;
  email: string;
}

export default function CreateGroupPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await apiClient.get<{ users: User[] }>('/messages/users');
        setAvailableUsers(response.users || []);
      } catch (error) {
        console.error('Failed to fetch users:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  const toggleUser = (userId: string) => {
    setSelectedUsers(prev =>
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) {
      setError('Group name is required');
      return;
    }

    if (selectedUsers.length === 0) {
      setError('Select at least one member');
      return;
    }

    setCreating(true);
    try {
      const group = await apiClient.post('/chat/groups', {
        name: name.trim(),
        description: description.trim() || undefined,
        member_ids: selectedUsers,
      });
      router.push(`/chat/group/${group.id}`);
    } catch (err: any) {
      setError(err.detail || 'Failed to create group. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: colors.lightBg }}>
      <div className="bg-white p-6 border-b" style={{ borderColor: colors.borderGray }}>
        <h1 className="text-2xl font-bold" style={{ color: colors.primaryText }}>Create Group Chat</h1>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto">
          <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
            {error && (
              <div className="px-4 py-3 rounded-lg text-sm" style={{ backgroundColor: '#FEE', borderColor: colors.danger, borderWidth: '1px', borderStyle: 'solid', color: colors.danger }}>
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="block text-sm font-medium mb-2" style={{ color: colors.primaryText }}>
                Group Name *
              </label>
              <input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 rounded-lg outline-none transition"
                style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
                placeholder="Enter group name"
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium mb-2" style={{ color: colors.primaryText }}>
                Description (Optional)
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 rounded-lg outline-none transition"
                style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
                placeholder="Enter group description"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-3" style={{ color: colors.primaryText }}>
                Select Members ({selectedUsers.length} selected)
              </label>
              <div className="border rounded-lg p-4 max-h-96 overflow-y-auto" style={{ borderColor: colors.borderGray }}>
                {availableUsers.length === 0 ? (
                  <p className="text-center py-4" style={{ color: colors.secondaryText }}>No users available</p>
                ) : (
                  <div className="space-y-2">
                    {availableUsers.map((user) => (
                      <label
                        key={user.id}
                        className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition"
                      >
                        <input
                          type="checkbox"
                          checked={selectedUsers.includes(user.id)}
                          onChange={() => toggleUser(user.id)}
                          className="w-4 h-4 rounded"
                          style={{ accentColor: colors.primaryBlue }}
                        />
                        <div className="flex-1">
                          <p className="font-medium" style={{ color: colors.primaryText }}>{user.name}</p>
                          <p className="text-sm" style={{ color: colors.secondaryText }}>{user.email}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={creating}
                className="px-6 py-3 text-white rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition"
                style={{ backgroundColor: colors.primaryBlue }}
                onMouseEnter={(e) => !creating && (e.currentTarget.style.backgroundColor = colors.darkBlue)}
                onMouseLeave={(e) => !creating && (e.currentTarget.style.backgroundColor = colors.primaryBlue)}
              >
                {creating ? (
                  <span className="flex items-center">
                    <LoadingSpinner size="sm" className="mr-2" />
                    Creating...
                  </span>
                ) : (
                  'Create Group'
                )}
              </button>
              <button
                type="button"
                onClick={() => router.back()}
                className="px-6 py-3 rounded-lg font-medium transition"
                style={{ backgroundColor: colors.borderGray, color: colors.primaryText }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#C0C0C0'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = colors.borderGray}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}


