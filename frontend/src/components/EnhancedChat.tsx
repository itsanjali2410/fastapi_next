'use client';

import { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useSocket } from '@/contexts/SocketContext';
import { colors } from '@/lib/colors';

interface Message {
  id: string;
  sender_id: string;
  receiver_id?: string;
  group_chat_id?: string;
  content: string;
  reply_to?: string;
  reply_to_content?: string;
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
}

function ChatHeader({ name, isOnline, lastSeen, isGroup }: ChatHeaderProps) {
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
          {!isGroup && (
            <p className="text-xs" style={{ color: colors.secondaryText }}>
              {isOnline ? 'Online' : lastSeen ? `Last seen ${new Date(lastSeen).toLocaleTimeString()}` : 'Offline'}
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
            className="absolute right-0 mt-2 bg-white rounded-lg shadow-lg py-1 z-50 min-w-[160px]"
            style={{ border: `1px solid ${colors.borderGray}` }}
          >
            <button
              onClick={() => {
                setShowMenu(false);
                // View profile action
              }}
              className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
              style={{ color: colors.primaryText }}
            >
              View Profile
            </button>
            <button
              onClick={() => {
                setShowMenu(false);
                // Search in chat action
              }}
              className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
              style={{ color: colors.primaryText }}
            >
              Search in Chat
            </button>
            {isGroup && (
              <button
                onClick={() => {
                  setShowMenu(false);
                  // Group info action
                }}
                className="w-full text-left px-4 py-2 hover:bg-gray-50 text-sm"
                style={{ color: colors.primaryText }}
              >
                Group Info
              </button>
            )}
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
}

function MessageBubble({ message, isOwn, onReply, onEdit, onDelete, onReact }: MessageBubbleProps) {
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
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} mb-2 group`}>
      <div className="relative max-w-xs lg:max-w-md">
        {message.reply_to && message.reply_to_content && (
          <div className="mb-1 px-3 py-1 rounded border-l-4 text-sm" style={{ borderColor: colors.primaryBlue, backgroundColor: colors.lightBg }}>
            <p className="font-medium text-xs" style={{ color: colors.primaryBlue }}>Replying to:</p>
            <p className="truncate" style={{ color: colors.secondaryText }}>{message.reply_to_content}</p>
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
          <p>{message.content}</p>
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
                {new Date(message.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
              </span>
              {isOwn && (
                <span className="text-xs" style={{ color: isRead ? colors.primaryBlue : (isDelivered ? colors.secondaryText : 'transparent') }}>
                  {isRead ? '✓✓' : isDelivered ? '✓' : '○'}
                </span>
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
}

interface EnhancedChatProps {
  chatId: string;
  chatName: string;
  isGroup?: boolean;
  receiverId?: string;
}

export function EnhancedChat({ chatId, chatName, isGroup, receiverId }: EnhancedChatProps) {
  const { user } = useAuth();
  const { socket, connected } = useSocket();
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [replyingTo, setReplyingTo] = useState<Message | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const [lastSeen, setLastSeen] = useState<string>();
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        if (isGroup) {
          // Use group messages endpoint with pagination
          const response = await apiClient.get<{ messages: Message[]; page: number; limit: number; total: number; has_more: boolean }>(`/chat/groups/${chatId}/messages?page=1`);
          setMessages(response.messages || []);
          
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

    socket.on('new_message', handleNewMessage);
    socket.on('group_message', handleGroupMessage);
    socket.on('message_updated', handleMessageUpdate);
    socket.on('message_deleted', handleMessageDelete);
    if (isGroup) {
      socket.on('group_typing', handleGroupTyping);
    }

    return () => {
      socket.off('new_message', handleNewMessage);
      socket.off('group_message', handleGroupMessage);
      socket.off('message_updated', handleMessageUpdate);
      socket.off('message_deleted', handleMessageDelete);
      if (isGroup) {
        socket.off('group_typing', handleGroupTyping);
      }
    };
  }, [socket, connected, chatId, receiverId, isGroup, user?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || sending || !user?.id) return;

    setSending(true);
    try {
      if (isGroup && socket && connected) {
        // Use socket for group messages
        socket.emit('group_message', {
          groupId: chatId,
          senderId: user.id,
          content: newMessage.trim(),
        });
        setNewMessage('');
        setReplyingTo(null);
      } else {
        // Use API for 1-to-1 messages
        const payload: {
          content: string;
          reply_to?: string;
          group_chat_id?: string;
          receiver_id?: string;
        } = {
          content: newMessage.trim(),
        };

        if (replyingTo) {
          payload.reply_to = replyingTo.id;
        }

        if (isGroup) {
          payload.group_chat_id = chatId;
        } else {
          payload.receiver_id = receiverId;
        }

        await apiClient.post('/messages/send', payload);
        setNewMessage('');
        setReplyingTo(null);
      }
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
    if (newContent && newContent !== message.content) {
      try {
        await apiClient.put(`/messages/${message.id}`, { content: newContent });
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
    <div className="h-full flex flex-col" style={{ backgroundColor: colors.lightBg }}>
      <ChatHeader 
        name={chatName} 
        isOnline={isOnline} 
        lastSeen={lastSeen}
        isGroup={isGroup}
      />

      <div className="flex-1 overflow-y-auto p-4" style={{ backgroundColor: '#ECE5DD' }}>
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            isOwn={message.sender_id === user?.id}
            onReply={handleReply}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onReact={handleReact}
          />
        ))}
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

      <form onSubmit={handleSend} className="bg-white p-4 border-t" style={{ borderColor: colors.borderGray }}>
        <div className="flex items-center space-x-2">
          {/* File Attachment Button */}
          <button
            type="button"
            className="p-2 rounded-lg hover:bg-gray-100 transition"
            title="Attach file"
            onClick={() => {
              // File attachment functionality
              const input = document.createElement('input');
              input.type = 'file';
              input.accept = 'image/*,video/*,.pdf,.doc,.docx';
              input.onchange = (e) => {
                const file = (e.target as HTMLInputElement).files?.[0];
                if (file) {
                  // Handle file upload
                  console.log('File selected:', file.name);
                }
              };
              input.click();
            }}
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
            disabled={sending || !newMessage.trim()}
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

