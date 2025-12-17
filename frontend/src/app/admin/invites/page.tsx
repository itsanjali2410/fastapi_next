'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import { colors } from '@/lib/colors';
import { LoadingSpinner } from '@/components/LoadingSpinner';

interface InviteLink {
  id: string;
  token: string;
  org_id: string;
  created_by: string;
  is_used: boolean;
  used_by?: string;
  expires_at?: string;
  created_at: string;
  invite_url: string;
}

export default function InviteLinksPage() {
  const [invites, setInvites] = useState<InviteLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [expiresAt, setExpiresAt] = useState('');

  useEffect(() => {
    const fetchInvites = async () => {
      try {
        const data = await apiClient.get<InviteLink[]>('/invites');
        setInvites(data);
      } catch (error) {
        console.error('Failed to fetch invites:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchInvites();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const invite = await apiClient.post<InviteLink>('/invites/create', {
        expires_at: expiresAt || undefined,
      });
      setInvites(prev => [invite, ...prev]);
      setExpiresAt('');
    } catch (error) {
      console.error('Failed to create invite:', error);
    } finally {
      setCreating(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
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
      <div className="bg-white border-b p-6 flex justify-between items-center" style={{ borderColor: colors.borderGray }}>
        <h1 className="text-2xl font-bold" style={{ color: colors.primaryText }}>Invite Links</h1>
        <div className="flex items-center space-x-4">
          <input
            type="datetime-local"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
            className="px-3 py-2 rounded-lg outline-none text-sm"
            style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
            placeholder="Expires at (optional)"
          />
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 text-white rounded-lg font-medium transition disabled:opacity-50"
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
              'Create Invite Link'
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y" style={{ borderColor: colors.borderGray }}>
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: colors.secondaryText }}>
                  Invite URL
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: colors.secondaryText }}>
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: colors.secondaryText }}>
                  Expires
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: colors.secondaryText }}>
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: colors.secondaryText }}>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: colors.borderGray }}>
              {invites.map((invite) => (
                <tr key={invite.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      <code className="text-sm" style={{ color: colors.primaryText }}>
                        {invite.invite_url}
                      </code>
                      <button
                        onClick={() => copyToClipboard(invite.invite_url)}
                        className="text-sm px-2 py-1 rounded hover:bg-gray-100"
                        style={{ color: colors.primaryBlue }}
                      >
                        Copy
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        invite.is_used
                          ? 'bg-gray-100 text-gray-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {invite.is_used ? 'Used' : 'Active'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm" style={{ color: colors.secondaryText }}>
                    {invite.expires_at
                      ? new Date(invite.expires_at).toLocaleDateString()
                      : 'Never'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm" style={{ color: colors.secondaryText }}>
                    {new Date(invite.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {!invite.is_used && (
                      <button
                        className="text-red-600 hover:text-red-900"
                        onClick={async () => {
                          if (confirm('Delete this invite link?')) {
                            try {
                              await apiClient.delete(`/invites/${invite.id}`);
                              setInvites(prev => prev.filter(i => i.id !== invite.id));
                            } catch (error) {
                              console.error('Failed to delete invite:', error);
                            }
                          }
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}


