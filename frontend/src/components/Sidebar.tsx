'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { colors } from '@/lib/colors';

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ collapsed = false, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const isActive = (path: string) => pathname === path || pathname.startsWith(path);

  const navItems = [
    { href: '/chat', label: 'Chats', icon: '💬' },
    { href: '/tasks', label: 'Tasks', icon: '✓' },
    ...(user?.role === 'admin' ? [{ href: '/admin/users', label: 'Users', icon: '👥' }] : []),
    ...(user?.role === 'admin' ? [{ href: '/admin/invites', label: 'Invite', icon: '🔗' }] : []),
    ...(user?.role === 'admin' ? [{ href: '/admin/settings', label: 'Settings', icon: '⚙️' }] : []),
    { href: '/profile', label: 'Profile', icon: '👤' },
  ];

  return (
    <div 
      className={`text-white min-h-screen flex flex-col transition-all duration-300 relative`}
      style={{ 
        backgroundColor: '#073B82',
        width: collapsed ? '80px' : '256px'
      }}
    >
      {/* Header with Toggle */}
      <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: '#0D58A6' }}>
        {!collapsed && (
          <>
            <h1 className="text-xl font-bold">Platform</h1>
            {user && user.name && (
              <p className="text-xs mt-1" style={{ color: '#B2E9FB' }}>{user.name}</p>
            )}
          </>
        )}
        <button
          onClick={onToggle}
          className="p-2 rounded hover:bg-white/10 transition"
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          <span className="text-xl">☰</span>
        </button>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center ${collapsed ? 'justify-center' : 'space-x-3'} px-4 py-3 rounded-lg transition group relative ${
              isActive(item.href)
                ? 'text-white'
                : 'text-white/70 hover:bg-white/10 hover:text-white'
            }`}
            style={isActive(item.href) ? { backgroundColor: '#00AEEF' } : {}}
            title={collapsed ? item.label : undefined}
          >
            <span className="text-lg">{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
            {collapsed && (
              <div className="absolute left-full ml-2 px-2 py-1 bg-gray-800 text-white text-sm rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50">
                {item.label}
              </div>
            )}
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t" style={{ borderColor: '#0D58A6' }}>
        <button
          onClick={logout}
          className={`w-full flex items-center ${collapsed ? 'justify-center' : 'space-x-3'} px-4 py-3 rounded-lg text-white/70 hover:bg-white/10 hover:text-white transition group relative`}
          title={collapsed ? "Logout" : undefined}
        >
          <span>🚪</span>
          {!collapsed && <span>Logout</span>}
          {collapsed && (
            <div className="absolute left-full ml-2 px-2 py-1 bg-gray-800 text-white text-sm rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50">
              Logout
            </div>
          )}
        </button>
      </div>
    </div>
  );
}

