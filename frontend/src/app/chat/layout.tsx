'use client';

import { useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { ChatSidebar } from '@/components/ChatSidebar';
import { ProtectedRoute } from '@/components/ProtectedRoute';

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <ProtectedRoute requireOrg>
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
    </ProtectedRoute>
  );
}

