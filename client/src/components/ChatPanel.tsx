import { useState, useEffect, useRef } from 'react';
import { Search, Send, X, MessageCircle, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/hooks/use-auth';
import { useChatWebSocket } from '@/hooks/use-chat-websocket';
import { useChatApi } from '@/hooks/use-chat-api';
import { formatDistanceToNow } from 'date-fns';

interface User {
  id: string;
  username: string;
  firstName?: string;
  lastName?: string;
  profileImageUrl?: string;
  isOnline?: boolean;
}

interface Message {
  id: string;
  senderId: string;
  receiverId: string;
  content: string;
  timestamp: string;
  senderUsername?: string;
}

interface ChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ChatPanel({ isOpen, onClose }: ChatPanelProps) {
  const { user: currentUser, token } = useAuth();
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [messageInput, setMessageInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { searchUsers, users, isSearching } = useChatApi();
  const { 
    messages, 
    isConnected, 
    sendMessage, 
    connect, 
    disconnect 
  } = useChatWebSocket(currentUser?.id, token);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Connect WebSocket when panel opens
  useEffect(() => {
    if (isOpen && currentUser?.id && token) {
      connect();
    } else {
      disconnect();
    }
    
    return () => disconnect();
  }, [isOpen, currentUser?.id, token, connect, disconnect]);

  // Search users when query changes
  useEffect(() => {
    if (searchQuery.trim()) {
      searchUsers(searchQuery.trim());
    }
  }, [searchQuery, searchUsers]);

  const handleSendMessage = () => {
    if (!messageInput.trim() || !selectedUser || !currentUser) return;

    sendMessage({
      receiverId: selectedUser.id,
      content: messageInput.trim(),
    });

    setMessageInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const filteredMessages = selectedUser 
    ? messages.filter(msg => 
        (msg.senderId === currentUser?.id && msg.receiverId === selectedUser.id) ||
        (msg.senderId === selectedUser.id && msg.receiverId === currentUser?.id)
      )
    : [];

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-background border-l border-border shadow-lg z-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <MessageCircle className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Chat</h3>
          {isConnected && (
            <div className="w-2 h-2 bg-green-500 rounded-full" title="Connected" />
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} data-testid="button-close-chat">
          <X className="w-4 h-4" />
        </Button>
      </div>

      {!selectedUser ? (
        /* User Search */
        <div className="flex-1 flex flex-col">
          <div className="p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search users..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
                data-testid="input-search-users"
              />
            </div>
          </div>

          <ScrollArea className="flex-1">
            <div className="space-y-1 p-2">
              {isSearching ? (
                <div className="text-center text-sm text-muted-foreground p-4">
                  Searching users...
                </div>
              ) : users.length > 0 ? (
                users.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center space-x-3 p-3 rounded-lg hover:bg-muted cursor-pointer transition-colors"
                    onClick={() => setSelectedUser(user)}
                    data-testid={`user-item-${user.id}`}
                  >
                    <Avatar className="w-8 h-8">
                      <AvatarImage src={user.profileImageUrl} />
                      <AvatarFallback>
                        {user.username.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{user.username}</p>
                      {(user.firstName || user.lastName) && (
                        <p className="text-xs text-muted-foreground truncate">
                          {[user.firstName, user.lastName].filter(Boolean).join(' ')}
                        </p>
                      )}
                    </div>
                    {user.isOnline && (
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                    )}
                  </div>
                ))
              ) : searchQuery ? (
                <div className="text-center text-sm text-muted-foreground p-4">
                  No users found
                </div>
              ) : (
                <div className="text-center text-sm text-muted-foreground p-4">
                  <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  Search for users to start chatting
                </div>
              )}
            </div>
          </ScrollArea>
        </div>
      ) : (
        /* Chat Interface */
        <div className="flex-1 flex flex-col">
          {/* Chat Header */}
          <div className="p-3 border-b border-border flex items-center space-x-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedUser(null)}
              data-testid="button-back-to-users"
            >
              ←
            </Button>
            <Avatar className="w-8 h-8">
              <AvatarImage src={selectedUser.profileImageUrl} />
              <AvatarFallback>
                {selectedUser.username.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{selectedUser.username}</p>
              {selectedUser.isOnline && (
                <p className="text-xs text-green-500">Online</p>
              )}
            </div>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {filteredMessages.length === 0 ? (
                <div className="text-center text-sm text-muted-foreground">
                  No messages yet. Start the conversation!
                </div>
              ) : (
                filteredMessages.map((message) => {
                  const isOwnMessage = message.senderId === currentUser?.id;
                  return (
                    <div
                      key={message.id}
                      className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                      data-testid={`message-${message.id}`}
                    >
                      <div
                        className={`max-w-[70%] rounded-lg p-3 ${
                          isOwnMessage
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted'
                        }`}
                      >
                        <p className="text-sm">{message.content}</p>
                        <p
                          className={`text-xs mt-1 ${
                            isOwnMessage
                              ? 'text-primary-foreground/70'
                              : 'text-muted-foreground'
                          }`}
                        >
                          {formatDistanceToNow(new Date(message.timestamp), {
                            addSuffix: true,
                          })}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Message Input */}
          <div className="p-4 border-t border-border">
            <div className="flex space-x-2">
              <Input
                placeholder="Type a message..."
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1"
                data-testid="input-message"
              />
              <Button
                onClick={handleSendMessage}
                disabled={!messageInput.trim() || !isConnected}
                data-testid="button-send-message"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
            {!isConnected && (
              <p className="text-xs text-destructive mt-1">
                Connection lost. Reconnecting...
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}