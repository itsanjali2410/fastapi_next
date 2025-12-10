'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { colors } from '@/lib/colors';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
    } catch (err: unknown) {
      const error = err as { detail?: string };
      setError(error.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4" style={{ background: `linear-gradient(to bottom right, ${colors.lightBlue}, ${colors.lightBg})` }}>
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2" style={{ color: colors.primaryText }}>Welcome Back</h1>
            <p style={{ color: colors.secondaryText }}>Sign in to your account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="px-4 py-3 rounded-lg text-sm" style={{ backgroundColor: '#FEE', borderColor: colors.danger, borderWidth: '1px', borderStyle: 'solid', color: colors.danger }}>
                {error}
              </div>
            )}

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
                  Signing in...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm" style={{ color: colors.secondaryText }}>
              Don&apos;t have an account?{' '}
              <a href="/register" className="font-medium" style={{ color: colors.primaryBlue }} onMouseEnter={(e) => e.currentTarget.style.color = colors.darkBlue} onMouseLeave={(e) => e.currentTarget.style.color = colors.primaryBlue}>
                Sign up
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
