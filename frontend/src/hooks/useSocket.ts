'use client';

/**
 * @deprecated Use useSocket from @/contexts/SocketContext instead
 * This hook is kept for backward compatibility and now uses the SocketContext
 */
import { useSocket as useSocketContext } from '@/contexts/SocketContext';

export function useSocket() {
  const { socket, connected } = useSocketContext();
  return { socket, connected };
}

