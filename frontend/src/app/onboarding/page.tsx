'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { colors } from '@/lib/colors';

export default function OnboardingPage() {
  return (
    <ProtectedRoute>
      <OnboardingContent />
    </ProtectedRoute>
  );
}

function OnboardingContent() {
  const [orgName, setOrgName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { refreshUser } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await apiClient.post('/org/setup', { name: orgName });
      await refreshUser();
      router.push('/chat');
    } catch (err: any) {
      setError(err.detail || 'Failed to create organization. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4" style={{ background: `linear-gradient(to bottom right, ${colors.lightBlue}, ${colors.lightBg})` }}>
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2" style={{ color: colors.primaryText }}>Create Organization</h1>
            <p style={{ color: colors.secondaryText }}>Set up your organization to get started</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="px-4 py-3 rounded-lg text-sm" style={{ backgroundColor: '#FEE', borderColor: colors.danger, borderWidth: '1px', borderStyle: 'solid', color: colors.danger }}>
                {error}
              </div>
            )}

            <div>
              <label htmlFor="orgName" className="block text-sm font-medium mb-2" style={{ color: colors.primaryText }}>
                Organization Name
              </label>
              <input
                id="orgName"
                type="text"
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="w-full px-4 py-3 rounded-lg outline-none transition"
                style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
                placeholder="Acme Inc."
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full text-white py-3 rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition"
              style={{ backgroundColor: colors.primaryBlue }}
              onMouseEnter={(e) => !loading && (e.currentTarget.style.backgroundColor = colors.darkBlue)}
              onMouseLeave={(e) => !loading && (e.currentTarget.style.backgroundColor = colors.primaryBlue)}
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <LoadingSpinner size="sm" className="mr-2" />
                  Creating...
                </span>
              ) : (
                'Create Organization'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

