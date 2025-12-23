'use client';

import React, { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useSocket } from '@/contexts/SocketContext';
import { colors } from '@/lib/colors';
import GroupMembersList from '@/components/GroupMembersList';
import { formatHeaderTime, formatTimeShort } from '@/lib/timeUtils';

interface Message {
  id: string;
  chat_type?: 'personal' | 'group';
  sender_id: string;
  receiver_id?: string;
  group_id?: string;
  group_chat_id?: string;
  content: string;
  type?: 'text' | 'image' | 'video' | 'audio' | 'document';
  attachment_url?: string;
  attachment_name?: string;
  mime_type?: string;
  reply_to?: string;
  quoted_message?: Message; // Populated reply message
  edited: boolean;
  edited_at?: string;
  deleted: boolean;
  reactions?: Array<{ user_id: string; emoji: string }>;
  delivery_status?: Record<string, { delivered: boolean; read: boolean; read_at?: string }>;
  created_at: string;
  sender_name?: string;
}

interface ChatHeaderProps {
  name: string;
  isOnline?: boolean;
  lastSeen?: string;
  isGroup?: boolean;
  groupHeaderTime?: string | null;
  showBack?: boolean;
  onBack?: () => void;
  onSearch?: () => void;
  onInfo?: () => void;
}

function ChatHeader({ name, isOnline, lastSeen, isGroup, groupHeaderTime, showBack, onBack, onSearch, onInfo }: ChatHeaderProps) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="bg-white p-4 flex items-center justify-between border-b relative" style={{ borderColor: colors.borderGray }}>
      <div className="flex items-center space-x-3">
        {showBack && (
          <button
            onClick={onBack}
            className="mr-2 p-2 rounded-lg hover:bg-gray-100 transition"
            aria-label="Back"
          >
            ←
          </button>
        )}
        <div className="relative">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
            style={{ backgroundColor: colors.chatAccent }}
          >
            {name.charAt(0).toUpperCase()}
          </div>
          {isOnline && !isGroup && (
            <div className="absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white" style={{ backgroundColor: colors.success }}></div>
          )}
        </div>
        <div>
          <h2 className="text-lg font-semibold" style={{ color: colors.primaryText }}>{name}</h2>
          {!isGroup ? (
            <p className="text-xs" style={{ color: colors.secondaryText }}>
              {isOnline ? 'Online' : lastSeen ? `Last seen ${formatHeaderTime(lastSeen)}` : 'Offline'}
            </p>
          ) : (
            <p className="text-xs" style={{ color: colors.secondaryText }}>
              {groupHeaderTime || ''}
            </p>
          )}
        </div>
      </div>
      
      {/* Context Menu Button */}
      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="p-2 rounded-lg hover:bg-gray-100 transition"
          title="More options"
        >
          <span className="text-xl">⋮</span>
        </button>
        
        {showMenu && (
          <div
            className="absolute right-0 mt-2 bg-white rounded-lg shadow-lg py-1 z-50 min-w-40"
            style={{ border: `1px solid ${colors.borderGray}` }}
          >
            <button
              onClick={() => {
                setShowMenu(false);
                onInfo?.();
              }}
              className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
              style={{ color: colors.primaryText }}
            >
              {isGroup ? 'Group Info' : 'View Profile'}
            </button>
            <button
              onClick={() => {
                setShowMenu(false);
                onSearch?.();
              }}
              className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
              style={{ color: colors.primaryText }}
            >
              Search in Chat
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

interface MessageBubbleProps {
  message: Message;
  isOwn: boolean;
  onReply: (message: Message) => void;
  onEdit: (message: Message) => void;
  onDelete: (messageId: string) => void;
  onReact: (messageId: string, emoji: string) => void;
  quotedMessage?: Message | null;
}

const MessageBubble = React.forwardRef<HTMLDivElement, MessageBubbleProps>(function MessageBubble(
  { message, isOwn, onReply, onEdit, onDelete, onReact, quotedMessage },
  ref
) {
  const [showMenu, setShowMenu] = useState(false);
  const [showReactions, setShowReactions] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (message.deleted) {
    return (
      <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} mb-2`}>
        <div className="px-4 py-2 rounded-lg italic" style={{ color: colors.secondaryText, backgroundColor: colors.lightBg }}>
          This message was deleted
        </div>
      </div>
    );
  }

  // Get delivery status for read receipts
  const deliveryStatus = isOwn && message.delivery_status 
    ? (message.receiver_id && message.delivery_status[message.receiver_id]
       ? message.delivery_status[message.receiver_id]
       : message.group_chat_id 
         ? Object.values(message.delivery_status).find((status: { read?: boolean; delivered?: boolean }) => status.read)
         : undefined)
    : undefined;
  const isRead = deliveryStatus && typeof deliveryStatus === 'object' ? deliveryStatus.read : false;
  const isDelivered = deliveryStatus && typeof deliveryStatus === 'object' ? deliveryStatus.delivered : false;

  return (
    <div ref={ref} className={`flex ${isOwn ? 'justify-end' : 'justify-start'} mb-2 group`}>
      <div className="relative max-w-xs lg:max-w-md">
        {/* Quoted message (reply) */}
        {(message.reply_to && (quotedMessage || message.quoted_message)) && (
          <div className="mb-1 px-3 py-1 rounded border-l-4 text-sm" style={{ borderColor: colors.primaryBlue, backgroundColor: colors.lightBg }}>
            <p className="font-medium text-xs" style={{ color: colors.primaryBlue }}>
              {(quotedMessage || message.quoted_message)?.sender_name || 'Someone'}
            </p>
            <p className="truncate" style={{ color: colors.secondaryText }}>
              {(quotedMessage || message.quoted_message)?.content || '[Message]'}
            </p>
          </div>
        )}
        <div
          className="px-4 py-2 rounded-lg relative"
          style={{
            backgroundColor: isOwn ? colors.chatAccent : colors.white,
            color: isOwn ? colors.white : colors.primaryText,
            border: isOwn ? 'none' : `1px solid ${colors.borderGray}`,
          }}
        >
          {!isOwn && message.sender_name && (
            <p className="text-xs font-semibold mb-1" style={{ color: isOwn ? colors.lightBlue : colors.primaryBlue }}>
              {message.sender_name}
            </p>
          )}
          
          {/* Attachment preview */}
          {message.attachment_url && (
            <div className="mb-2">
              {message.type === 'image' && (
                <div className="relative w-full max-w-xs">
                  <Image
                    src={message.attachment_url}
                    alt={message.attachment_name || 'Image'}
                    className="rounded-lg cursor-pointer h-auto w-full"
                    width={400}
                    height={400}
                    onClick={() => window.open(message.attachment_url, '_blank')}
                  />
                </div>
              )}
              {message.type === 'video' && (
                <video 
                  src={message.attachment_url} 
                  controls 
                  className="max-w-full rounded-lg"
                />
              )}
              {message.type === 'audio' && (
                <audio 
                  src={message.attachment_url} 
                  controls 
                  className="w-full"
                />
              )}
              {(message.type === 'document' || !message.type || message.type === 'text') && message.attachment_url && (
                <a 
                  href={message.attachment_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex items-center space-x-2 p-2 rounded hover:bg-white/10"
                >
                  <span className="text-2xl">📎</span>
                  <span className="text-sm">{message.attachment_name || 'Download file'}</span>
                </a>
              )}
            </div>
          )}
          
          {/* Message content */}
          {message.content && <p>{message.content}</p>}
          {message.edited && (
            <span className="text-xs italic ml-2" style={{ color: isOwn ? colors.lightBlue : colors.secondaryText }}>
              (edited)
            </span>
          )}
          <div className="flex items-center justify-between mt-2">
            <div className="flex items-center space-x-2">
              {message.reactions && message.reactions.length > 0 && (
                <div className="flex space-x-1">
                  {message.reactions.map((reaction, idx) => (
                    <span
                      key={idx}
                      className="text-xs px-1 py-0.5 rounded"
                      style={{ backgroundColor: isOwn ? 'rgba(255,255,255,0.2)' : colors.lightBg }}
                    >
                      {reaction.emoji}
                    </span>
                  ))}
                </div>
              )}
              <span className="text-xs" style={{ color: isOwn ? colors.lightBlue : colors.secondaryText }}>
                {formatTimeShort(message.created_at)}
              </span>
              {isOwn && (
                <div className="flex items-center space-x-1">
                  <span className="text-xs" style={{ color: isRead ? '#FFFFFF' : (isDelivered ? colors.secondaryText : 'transparent') }}>
                    {isRead ? '✓✓' : isDelivered ? '✓' : '○'}
                  </span>
                  {isRead && deliveryStatus && (deliveryStatus.read_at || deliveryStatus.read_at || deliveryStatus.read_at) && (
                    <span className="text-xs" style={{ color: colors.secondaryText }}>{formatHeaderTime((deliveryStatus.read_at || deliveryStatus.read_at) as string)}</span>
                  )}
                </div>
              )}
            </div>
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="p-1 rounded hover:bg-white/20 transition opacity-0 group-hover:opacity-100"
                title="More options"
                style={{ color: isOwn ? colors.lightBlue : colors.secondaryText }}
              >
                <span className="text-sm">⋮</span>
              </button>
              {showMenu && (
                <div
                  className="absolute right-0 mt-1 bg-white rounded-lg shadow-lg py-1 z-50 min-w-[120px]"
                  style={{ border: `1px solid ${colors.borderGray}` }}
                >
                  <button
                    onClick={() => { onReply(message); setShowMenu(false); }}
                    className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
                    style={{ color: colors.primaryText }}
                  >
                    Reply
                  </button>
                  {isOwn && (
                    <>
                      <button
                        onClick={() => { onEdit(message); setShowMenu(false); }}
                        className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
                        style={{ color: colors.primaryText }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => { onDelete(message.id); setShowMenu(false); }}
                        className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
                        style={{ color: colors.danger }}
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {showReactions && (
          <div
            className="absolute top-full mt-1 bg-white rounded-lg shadow-lg p-2 z-20"
            style={{ border: `1px solid ${colors.borderGray}` }}
          >
            <div className="flex space-x-2">
              {['👍', '❤️', '😂', '😮', '😢', '🙏'].map(emoji => (
                <button
                  key={emoji}
                  onClick={() => { onReact(message.id, emoji); setShowReactions(false); }}
                  className="text-2xl hover:scale-125 transition"
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

interface EnhancedChatProps {
  chatId: string;
  chatName: string;
  isGroup?: boolean;
  receiverId?: string;
  onBackToList?: () => void;
}

export function EnhancedChat({ chatId, chatName, isGroup, receiverId, onBackToList }: EnhancedChatProps) {
  const { user } = useAuth();
  const { socket, connected } = useSocket();
  const router = useRouter();
  const [isMobile, setIsMobile] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showInfo, setShowInfo] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [replyingTo, setReplyingTo] = useState<Message | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const [lastSeen, setLastSeen] = useState<string>();
  const [isTyping, setIsTyping] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<{ url: string; name: string; mime: string; type: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messageRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const messageLookup = React.useMemo(() => {
    const map: Record<string, Message> = {};
    messages.forEach((m) => { map[m.id] = m; });
    return map;
  }, [messages]);

  useEffect(() => {
    const updateIsMobile = () => setIsMobile(typeof window !== 'undefined' && window.innerWidth <= 768);
    updateIsMobile();
    window.addEventListener('resize', updateIsMobile);
    return () => window.removeEventListener('resize', updateIsMobile);
  }, []);

  const [groupLastSeen, setGroupLastSeen] = useState<{ last_message?: any; read_by?: any[]; header_time?: string } | null>(null);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        if (isGroup) {
          // Use group messages endpoint with pagination
          const response = await apiClient.get<{ messages: Message[]; page: number; limit: number; total: number; has_more: boolean }>(`/chat/groups/${chatId}/messages?page=1`);
          setMessages(response.messages || []);
          
          // Fetch last-seen info for group
          try {
            const lastSeen = await apiClient.get<{ last_message?: any; read_by?: any[]; header_time?: string }>(`/chat/groups/${chatId}/last-seen`);
            setGroupLastSeen(lastSeen);
          } catch (err) {
            // ignore
          }

          // Mark all group messages as read when group is opened
          if (user?.id) {
            try {
              await apiClient.post(`/chat/groups/${chatId}/mark-read`);
            } catch (error) {
              console.error('Failed to mark group messages as read:', error);
            }
          }
        } else {
          const response = await apiClient.get<{ messages: Message[] }>(`/messages/history/${receiverId}`);
          setMessages(response.messages || []);
          
          // Mark all messages as read when chat is opened
          if (user?.id) {
            try {
              await apiClient.post('/messages/mark-all-read', {
                receiver_id: receiverId,
              });
            } catch (error) {
              console.error('Failed to mark messages as read:', error);
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch messages:', error);
      } finally {
        setLoading(false);
      }
    };

    if (chatId) {
      fetchMessages();
    }

    // Fetch user status for 1-to-1 chats
    if (!isGroup && receiverId) {
      const fetchStatus = async () => {
        try {
          const status = await apiClient.get<{ is_online: boolean; last_seen: string }>(`/users/status/${receiverId}`);
          if (status) {
            setIsOnline(status.is_online);
            setLastSeen(status.last_seen);
          }
        } catch (error: unknown) {
          const err = error as { detail?: string };
          console.error('Failed to fetch status:', err.detail || 'Unknown error');
          // Set default offline status if fetch fails
          setIsOnline(false);
        }
      };
      fetchStatus();
    }
  }, [chatId, receiverId, isGroup, user?.id]);

  // Typing indicator
  useEffect(() => {
    if (!socket || !connected) return;

    let typingTimeout: NodeJS.Timeout;
    const handleTyping = () => {
      setIsTyping(true);
      clearTimeout(typingTimeout);
      typingTimeout = setTimeout(() => setIsTyping(false), 3000);
    };

    socket.on('typing', handleTyping);

    return () => {
      socket.off('typing', handleTyping);
      clearTimeout(typingTimeout);
    };
  }, [socket, connected]);

  // Join group room when group chat is opened
  useEffect(() => {
    if (!socket || !connected || !isGroup || !chatId) return;

    // Join the group room
    socket.emit('join_group', { groupId: chatId });

    return () => {
      // Optionally leave room on unmount (though socket will handle this on disconnect)
    };
  }, [socket, connected, chatId, isGroup]);

  // Socket.io real-time updates
  useEffect(() => {
    if (!socket || !connected) return;

    const handleNewMessage = (message: Message) => {
      // Only handle 1-to-1 messages here, group messages are handled separately
      if (!isGroup && ((message.sender_id === receiverId && message.receiver_id === user?.id) ||
                      (message.sender_id === user?.id && message.receiver_id === receiverId))) {
        setMessages(prev => {
          // Check if message already exists
          if (prev.some(m => m.id === message.id)) {
            return prev;
          }
          return [...prev, message];
        });
        
        // Play notification sound and mark as read if message is from another user
        if (message.sender_id !== user?.id) {
          try {
            const audio = new Audio('/80921__justinbw__buttonchime02up.wav');
            audio.volume = 0.5;
            audio.play().catch(() => {
              // Ignore audio play errors (user may have blocked autoplay)
            });
          } catch {
            // Ignore audio errors
          }
          
          // Mark message as read immediately when received in open chat
          if (user?.id) {
            apiClient.post('/messages/mark-all-read', {
              receiver_id: receiverId,
            }).catch(() => {
              // Ignore errors
            });
          }
        }
      }
    };

    // Handle group messages separately
    const handleGroupMessage = (message: Message) => {
      if (isGroup && message.group_chat_id === chatId) {
        setMessages(prev => {
          // Check if message already exists
          if (prev.some(m => m.id === message.id)) {
            return prev;
          }
          return [...prev, message];
        });
        
        // Play notification sound and mark as read if message is from another user
        if (message.sender_id !== user?.id) {
          try {
            const audio = new Audio('/80921__justinbw__buttonchime02up.wav');
            audio.volume = 0.5;
            audio.play().catch(() => {
              // Ignore audio play errors
            });
          } catch {
            // Ignore audio errors
          }
          
          // Mark group messages as read immediately when received in open chat
          if (user?.id) {
            apiClient.post(`/chat/groups/${chatId}/mark-read`).catch(() => {
              // Ignore errors
            });
          }
        }
      }
    };

    const handleMessageUpdate = (updatedMessage: Message) => {
      setMessages(prev => prev.map(msg => 
        msg.id === updatedMessage.id ? updatedMessage : msg
      ));
    };

    const handleMessageDelete = (data: { message_id: string }) => {
      setMessages(prev => prev.map(msg => 
        msg.id === data.message_id ? { ...msg, deleted: true } : msg
      ));
    };

    // Handle group typing
    const handleGroupTyping = (data: { userId: string; groupId: string }) => {
      if (isGroup && data.groupId === chatId && data.userId !== user?.id) {
        setIsTyping(true);
        setTimeout(() => setIsTyping(false), 3000);
      }
    };

    // Handle receive_message (unified for personal and group)
    const handleReceiveMessage = (message: Message) => {
      if (
        (isGroup && (message.group_id === chatId || message.group_chat_id === chatId)) ||
        (!isGroup && ((message.sender_id === receiverId && message.receiver_id === user?.id) ||
                      (message.sender_id === user?.id && message.receiver_id === receiverId)))
      ) {
        setMessages(prev => {
          if (prev.some(m => m.id === message.id)) {
            return prev;
          }
          return [...prev, message];
        });
        
        // Mark as read if message is from another user
        if (message.sender_id !== user?.id) {
          if (isGroup) {
            apiClient.post(`/chat/groups/${chatId}/mark-read`).catch(() => {});
          } else {
            apiClient.post('/messages/mark-all-read', { receiver_id: receiverId }).catch(() => {});
            // Mark this specific message as delivered to the receiver
            apiClient.post(`/messages/${message.id}/mark-delivered`).catch(() => {});
          }
        }
      }
    };

    // Handle message edited
    const handleMessageEdited = (data: { id: string; content: string; edited: boolean; edited_at: string }) => {
      setMessages(prev => prev.map(msg => 
        msg.id === data.id 
          ? { ...msg, content: data.content, edited: data.edited, edited_at: data.edited_at }
          : msg
      ));
    };

    socket.on('new_message', handleNewMessage);
    socket.on('group_message', handleGroupMessage);
    socket.on('receive_message', handleReceiveMessage);
    socket.on('message_updated', handleMessageUpdate);
    socket.on('message_edited', handleMessageEdited);
    socket.on('message_deleted', handleMessageDelete);
    socket.on('messages_read', (data: { receiver_id?: string; timestamp?: string }) => {
      // For personal chats: if current chat is the receiver, update delivery status timestamps
      if (!isGroup && data.receiver_id && data.receiver_id === receiverId) {
        const ts = data.timestamp;
        setMessages(prev => prev.map(m => {
          if (m.sender_id === user?.id && m.receiver_id === receiverId) {
            const updated = { ...m, delivery_status: { ...(m.delivery_status || {}) } };
            updated.delivery_status[receiverId as string] = { delivered: true, read: true, read_at: ts } as any;
            return updated;
          }
          return m;
        }));
      }
    });

    socket.on('group_read_update', async (data: { groupId: string; userId: string; userName?: string; seenAt?: string }) => {
      if (isGroup && data.groupId === chatId) {
        // Refresh group last-seen info
        try {
          const lastSeen = await apiClient.get<{ last_message?: any; read_by?: any[]; header_time?: string }>(`/chat/groups/${chatId}/last-seen`);
          setGroupLastSeen(lastSeen);
        } catch (err) {
          // ignore
        }
      }
    });

    socket.on('message_delivered', (data: { messageId: string; receiver_id?: string; timestamp?: string }) => {
      // Update message delivery status for sender view
      setMessages(prev => prev.map(m => {
        if (m.id === data.messageId) {
          const updated = { ...m, delivery_status: { ...(m.delivery_status || {}) } };
          const rid = data.receiver_id as string;
          updated.delivery_status[rid] = { delivered: true, delivered_at: data.timestamp } as any;
          return updated;
        }
        return m;
      }));
    });

    if (isGroup) {
      socket.on('group_typing', handleGroupTyping);
    }

    return () => {
      socket.off('new_message', handleNewMessage);
      socket.off('group_message', handleGroupMessage);
      socket.off('receive_message', handleReceiveMessage);
      socket.off('message_updated', handleMessageUpdate);
      socket.off('message_edited', handleMessageEdited);
      socket.off('message_deleted', handleMessageDelete);
      socket.off('messages_read');
      socket.off('group_read_update');
      socket.off('message_delivered');
      if (isGroup) {
        socket.off('group_typing', handleGroupTyping);
      }
    };
  }, [socket, connected, chatId, receiverId, isGroup, user?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const filteredMessages = searchQuery
    ? messages.filter((m) => m.content?.toLowerCase().includes(searchQuery.toLowerCase()))
    : messages;

  const scrollToMessage = (id: string) => {
    const node = messageRefs.current[id];
    if (node) {
      node.scrollIntoView({ behavior: 'smooth', block: 'center' });
      node.classList.add('ring-2', 'ring-blue-400');
      setTimeout(() => {
        node.classList.remove('ring-2', 'ring-blue-400');
      }, 1200);
    }
    setShowSearch(false);
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Use fetch directly for FormData since apiClient might not handle it correctly
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const response = await fetch(`${API_BASE_URL}/upload/upload`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const data = await response.json();
      setUploadedFile(data);
      return data;
    } catch (error) {
      console.error('Failed to upload file:', error);
      throw error;
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!newMessage.trim() && !uploadedFile) || sending || uploading || !user?.id || !socket || !connected) return;

    setSending(true);
    try {
      // Upload file if present
      let attachmentData = null;
      if (uploadedFile) {
        attachmentData = uploadedFile;
      }

      // Use unified send_message socket event
      const messageData: {
        chatType: 'personal' | 'group';
        senderId: string;
        receiverId?: string;
        groupId?: string;
        content: string;
        type: string;
        attachmentUrl?: string;
        attachmentName?: string;
        mimeType?: string;
        replyTo?: string;
      } = {
        chatType: isGroup ? 'group' : 'personal',
        senderId: user.id,
        content: newMessage.trim() || '',
        type: attachmentData ? attachmentData.type : 'text',
      };

      if (isGroup) {
        messageData.groupId = chatId;
      } else {
        messageData.receiverId = receiverId;
      }

      if (attachmentData) {
        messageData.attachmentUrl = attachmentData.url;
        messageData.attachmentName = attachmentData.name;
        messageData.mimeType = attachmentData.mime;
      }

      if (replyingTo) {
        messageData.replyTo = replyingTo.id;
      }

      socket.emit('send_message', messageData);
      setNewMessage('');
      setReplyingTo(null);
      setUploadedFile(null);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setSending(false);
    }
  };

  const handleReply = (message: Message) => {
    setReplyingTo(message);
  };

  const handleEdit = async (message: Message) => {
    const newContent = prompt('Edit message:', message.content);
    if (newContent && newContent !== message.content && socket && connected) {
      try {
        socket.emit('edit_message', {
          messageId: message.id,
          newContent: newContent
        });
      } catch (error) {
        console.error('Failed to edit message:', error);
      }
    }
  };

  const handleDelete = async (messageId: string) => {
    if (!confirm('Are you sure you want to delete this message?')) return;
    try {
      await apiClient.delete(`/messages/${messageId}`);
    } catch (error) {
      console.error('Failed to delete message:', error);
    }
  };

  const handleReact = async (messageId: string, emoji: string) => {
    try {
      await apiClient.post(`/messages/${messageId}/reaction`, { emoji });
    } catch (error) {
      console.error('Failed to add reaction:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderColor: colors.primaryBlue }}></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col" style={{ backgroundColor: colors.lightBg, height: isMobile ? '100dvh' : '100%' }}>
      <ChatHeader 
        name={chatName} 
        isOnline={isOnline} 
        lastSeen={lastSeen}
        isGroup={isGroup}
        groupHeaderTime={groupLastSeen?.header_time || null}
        showBack={isMobile}
        onBack={() => {
          if (onBackToList) {
            onBackToList();
          } else {
            router.push('/chat');
          }
        }}
        onSearch={() => setShowSearch(true)}
        onInfo={() => setShowInfo(true)}
      />

      {showSearch && (
        <div className="bg-white border-b" style={{ borderColor: colors.borderGray }}>
          <div className="px-4 py-3 flex items-center space-x-2">
            <input
              autoFocus
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search messages..."
              className="flex-1 px-3 py-2 rounded-lg outline-none border text-sm"
              style={{ borderColor: colors.borderGray }}
            />
            <button
              type="button"
              onClick={() => { setShowSearch(false); setSearchQuery(''); }}
              className="px-3 py-2 text-sm rounded-lg hover:bg-gray-100"
              style={{ color: colors.secondaryText }}
            >
              Close
            </button>
          </div>
          {searchQuery && filteredMessages.length > 0 && (
            <div className="border-t max-h-48 overflow-y-auto" style={{ borderColor: colors.borderGray }}>
              {filteredMessages.slice(0, 10).map((message) => (
                <button
                  key={message.id}
                  type="button"
                  onClick={() => scrollToMessage(message.id)}
                  className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b last:border-b-0"
                  style={{ borderColor: colors.borderGray }}
                >
                  <p className="text-xs font-medium" style={{ color: colors.secondaryText }}>
                    {message.sender_name || 'You'} • {new Date(message.created_at).toLocaleString()}
                  </p>
                  <p className="text-sm truncate mt-1" style={{ color: colors.primaryText }}>
                    {message.content}
                  </p>
                </button>
              ))}
              {filteredMessages.length > 10 && (
                <div className="px-4 py-2 text-xs text-center" style={{ color: colors.secondaryText }}>
                  {filteredMessages.length - 10} more results...
                </div>
              )}
            </div>
          )}
          {searchQuery && filteredMessages.length === 0 && (
            <div className="px-4 py-3 text-sm text-center" style={{ color: colors.secondaryText }}>
              No messages found
            </div>
          )}
        </div>
      )}

      {showInfo && (
        <div className="bg-white border-b px-4 py-3" style={{ borderColor: colors.borderGray }}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold" style={{ color: colors.primaryText }}>
                {isGroup ? 'Group Info' : 'Chat Info'}
              </p>
              <p className="text-xs" style={{ color: colors.secondaryText }}>
                Name: {chatName} {isGroup ? `(Group ID: ${chatId})` : `(User ID: ${receiverId})`}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowInfo(false)}
              className="px-3 py-2 text-sm rounded-lg hover:bg-gray-100"
              style={{ color: colors.secondaryText }}
            >
              Close
            </button>
          </div>

          {isGroup && (
            <div className="mt-3 grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium" style={{ color: colors.primaryText }}>Members</p>
                <div className="mt-2 space-y-2">
                  <GroupMembersList groupId={chatId} currentUser={user} />
                </div>
              </div>
              <div>
                <p className="text-sm font-medium" style={{ color: colors.primaryText }}>Seen by</p>
                <div className="mt-2 space-y-2 text-xs" style={{ color: colors.secondaryText }}>
                  {groupLastSeen?.read_by && groupLastSeen.read_by.length > 0 ? (
                    groupLastSeen.read_by.map((r: any) => (
                      <div key={r.userId} className="flex items-center justify-between">
                        <div>{r.userName}</div>
                        <div className="text-right">{r.seenAt}</div>
                      </div>
                    ))
                  ) : (
                    <div>No one has read the latest message yet.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 pb-28" style={{ backgroundColor: '#ECE5DD' }}>
        {(searchQuery ? filteredMessages : messages).map((message) => {
          const quoted = message.quoted_message || (message.reply_to ? messageLookup[message.reply_to] : undefined);
          return (
          <MessageBubble
            key={message.id}
            ref={(el: HTMLDivElement | null) => { messageRefs.current[message.id] = el; }}
            message={message}
            isOwn={message.sender_id === user?.id}
            onReply={handleReply}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onReact={handleReact}
            quotedMessage={quoted}
          />
        );
        })}
        {isTyping && (
          <div className="flex justify-start mb-2">
            <div className="px-4 py-2 rounded-lg bg-white" style={{ border: `1px solid ${colors.borderGray}` }}>
              <div className="flex space-x-1">
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {replyingTo && (
        <div className="bg-white px-4 py-2 border-t flex items-center justify-between" style={{ borderColor: colors.borderGray }}>
          <div className="flex-1">
            <p className="text-xs font-medium" style={{ color: colors.primaryBlue }}>Replying to:</p>
            <p className="text-sm truncate" style={{ color: colors.secondaryText }}>{replyingTo.content}</p>
          </div>
          <button
            onClick={() => setReplyingTo(null)}
            className="ml-2 text-lg"
            style={{ color: colors.secondaryText }}
          >
            ×
          </button>
        </div>
      )}

      {uploadedFile && (
        <div className="bg-white px-4 py-2 border-t flex items-center justify-between" style={{ borderColor: colors.borderGray }}>
          <div className="flex-1 flex items-center space-x-2">
            {uploadedFile.type === 'image' && (
              <Image
                src={uploadedFile.url}
                alt="Preview"
                width={48}
                height={48}
                className="w-12 h-12 object-cover rounded"
              />
            )}
            <div className="flex-1">
              <p className="text-xs font-medium" style={{ color: colors.primaryBlue }}>Attached:</p>
              <p className="text-sm truncate" style={{ color: colors.secondaryText }}>{uploadedFile.name}</p>
            </div>
          </div>
          <button
            onClick={() => setUploadedFile(null)}
            className="ml-2 text-lg"
            style={{ color: colors.secondaryText }}
          >
            ×
          </button>
        </div>
      )}

      <form onSubmit={handleSend} className="bg-white p-4 border-t sticky bottom-0" style={{ borderColor: colors.borderGray }}>
        <div className="flex items-center space-x-2">
          {/* File Attachment Button */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.zip,.rar"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (file) {
                try {
                  await handleFileUpload(file);
                } catch (error) {
                  console.error('File upload failed:', error);
                }
              }
            }}
          />
          <button
            type="button"
            className="p-2 rounded-lg hover:bg-gray-100 transition"
            title="Attach file"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <span className="text-xl">📎</span>
          </button>
          
          {/* Input Field */}
          <input
            type="text"
            value={newMessage}
            onChange={(e) => {
              setNewMessage(e.target.value);
              // Emit typing indicator
              if (socket && connected && e.target.value.length > 0) {
                if (isGroup) {
                  socket.emit('group_typing', {
                    groupId: chatId,
                    userId: user?.id
                  });
                } else {
                  socket.emit('typing', {
                    chat_id: receiverId,
                    is_group: false
                  });
                }
              }
            }}
            placeholder="Type a message..."
            className="flex-1 px-4 py-2 rounded-lg outline-none"
            style={{ borderColor: colors.borderGray, borderWidth: '1px', borderStyle: 'solid' }}
          />
          
          {/* Send Button */}
          <button
            type="submit"
            disabled={sending || uploading || (!newMessage.trim() && !uploadedFile)}
            className="px-6 py-2 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition"
            style={{ backgroundColor: colors.primaryBlue }}
            onMouseEnter={(e) => !sending && newMessage.trim() && (e.currentTarget.style.backgroundColor = colors.darkBlue)}
            onMouseLeave={(e) => !sending && newMessage.trim() && (e.currentTarget.style.backgroundColor = colors.primaryBlue)}
          >
            ➤
          </button>
        </div>
      </form>
    </div>
  );
}

