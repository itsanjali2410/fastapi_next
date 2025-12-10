'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireOrg?: boolean;
  requireAdmin?: boolean;
}

/**
 * ProtectedRoute component that redirects unauthenticated users
 * and handles org/admin requirements
 */
export function ProtectedRoute({ 
  children, 
  requireOrg = false,
  requireAdmin = false 
}: ProtectedRouteProps) {
  const { user, loading, isAuthenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
      router.push('/');
      return;
    }

    if (!user) return;

    // Redirect to onboarding if org is required but user has no org
    if (requireOrg && !user.org_id) {
      router.push('/onboarding');
      return;
    }

    // Redirect to chat if admin is required but user is not admin
    if (requireAdmin && user.role !== 'admin') {
      router.push('/chat');
      return;
    }
  }, [user, loading, isAuthenticated, requireOrg, requireAdmin, router]);

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Don't render children until authenticated
  if (!isAuthenticated || !user) {
    return null;
  }

  // Check org requirement
  if (requireOrg && !user.org_id) {
    return null;
  }

  // Check admin requirement
  if (requireAdmin && user.role !== 'admin') {
    return null;
  }

  return <>{children}</>;
}

