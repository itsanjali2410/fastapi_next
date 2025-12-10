'use client';

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { colors } from '@/lib/colors';

export default function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

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
      await register(email, password, name);
    } catch (err: any) {
      setError(err.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4 py-8" style={{ background: `linear-gradient(to bottom right, ${colors.lightBlue}, ${colors.lightBg})` }}>
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2" style={{ color: colors.primaryText }}>Create Account</h1>
            <p style={{ color: colors.secondaryText }}>Sign up as an admin</p>
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
                  Creating account...
                </span>
              ) : (
                'Sign Up'
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm" style={{ color: colors.secondaryText }}>
              Already have an account?{' '}
              <a href="/" className="font-medium" style={{ color: colors.primaryBlue }} onMouseEnter={(e) => e.currentTarget.style.color = colors.darkBlue} onMouseLeave={(e) => e.currentTarget.style.color = colors.primaryBlue}>
                Sign in
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

