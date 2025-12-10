'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { authApi } from '@/lib/auth';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { colors } from '@/lib/colors';

export default function InviteSignupPage() {
  const params = useParams();
  const token = params.token as string;
  const router = useRouter();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      await authApi.useInviteLink({ token, email, password, name });
      router.push('/chat');
    } catch (err: any) {
      setError(err.detail || 'Failed to sign up. Please check your invite link.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4 py-8" style={{ background: `linear-gradient(to bottom right, ${colors.lightBlue}, ${colors.lightBg})` }}>
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2" style={{ color: colors.primaryText }}>Join Organization</h1>
            <p style={{ color: colors.secondaryText }}>Complete your signup</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="px-4 py-3 rounded-lg text-sm" style={{ backgroundColor: '#FEE', borderColor: colors.danger, borderWidth: '1px', borderStyle: 'solid', color: colors.danger }}>
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="block text-sm font-medium mb-2" style={{ color: colors.primaryText }}>
                Full Name
              </label>
              <input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 rounded-lg outline-none transition"
                style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
                placeholder="John Doe"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2" style={{ color: colors.primaryText }}>
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-lg outline-none transition"
                style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2" style={{ color: colors.primaryText }}>
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-lg outline-none transition"
                style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
                placeholder="••••••••"
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium mb-2" style={{ color: colors.primaryText }}>
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-lg outline-none transition"
                style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
                placeholder="••••••••"
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
                  Joining...
                </span>
              ) : (
                'Join Organization'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

