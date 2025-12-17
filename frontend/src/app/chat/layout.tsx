'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { Sidebar } from '@/components/Sidebar';
import { ChatSidebar } from '@/components/ChatSidebar';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const updateIsMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    updateIsMobile();
    window.addEventListener('resize', updateIsMobile);
    return () => window.removeEventListener('resize', updateIsMobile);
  }, []);

  const isChatList = pathname === '/chat';
  const isChatDetail = pathname.startsWith('/chat/') && !isChatList;

  return (
    <ProtectedRoute requireOrg>
      {isMobile ? (
        <div className="flex h-[100dvh]" style={{ backgroundColor: '#F5F7FA' }}>
          {showMobileSidebar ? (
            <Sidebar
              collapsed={false}
              onToggle={() => setShowMobileSidebar(false)}
            />
          ) : isChatDetail ? (
            <main className="flex-1 overflow-hidden flex flex-col">
              {children}
            </main>
          ) : (
            <ChatSidebar
              isMobile
              onOpenSidebar={() => setShowMobileSidebar(true)}
            />
          )}
        </div>
      ) : (
        <div className="flex h-screen" style={{ backgroundColor: '#F5F7FA' }}>
          {/* Column 1: Primary Navigation Sidebar */}
          <Sidebar 
            collapsed={sidebarCollapsed} 
            onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
          />
          
          {/* Column 2: WhatsApp-style List View */}
          <ChatSidebar />
          
          {/* Column 3: Active Workspace */}
          <main className="flex-1 overflow-hidden flex flex-col">
            {children}
          </main>
        </div>
      )}
    </ProtectedRoute>
  );
}

