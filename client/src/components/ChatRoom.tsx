import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
// Removed ScrollArea import - using regular div with overflow
import { Send, MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/queryClient";

interface Message {
  id: string;
  content: string;
  sender_id: string;
  sender: {
    id: string;
    username: string;
    avatar?: string;
  };
  sent_at: string;
}

interface ChatRoomProps {
  isOpen: boolean;
  onClose: () => void;
  room: {
    id: string;
    name: string;
    avatar: string;
    is_group: boolean;
  } | null;
}

export function ChatRoom({ isOpen, onClose, room }: ChatRoomProps) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch message history
  const { data: messageHistory, isLoading } = useQuery({
    queryKey: ['/api/chat/rooms', room?.id, 'messages'],
    enabled: !!room?.id && isOpen,
    refetchOnWindowFocus: false,
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      if (!room?.id) throw new Error('No room selected');
      return apiRequest(`/api/chat/rooms/${room.id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/chat/rooms'] });
    },
  });

  // WebSocket connection for real-time messages
  useEffect(() => {
    if (!room?.id || !isOpen || !user) return;

    const token = localStorage.getItem('auth_token');
    if (!token) return;

    // In Replit development, frontend is HTTPS but backend WebSocket is HTTP
    // Use WS for development, WSS for production
    const isReplit = window.location.hostname.includes('replit.dev') || window.location.hostname.includes('replit.app');
    const isDev = import.meta.env.DEV;
    
    console.log('🔍 WebSocket URL Debug:', {
      hostname: window.location.hostname,
      isReplit,
      isDev,
      protocol: window.location.protocol
    });
    
    let wsUrl;
    if (isDev && isReplit) {
      // Replit development: Use the same host as frontend (goes through proxy to backend)
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/ws/chat/${room.id}?token=${encodeURIComponent(token)}`;
      console.log('🎯 Using Replit development WebSocket URL (through proxy)');
    } else {
      // Production or local development: Use standard protocol detection
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/ws/chat/${room.id}?token=${encodeURIComponent(token)}`;
      console.log('🌐 Using standard WebSocket URL detection');
    }
    console.log('🔗 Attempting WebSocket connection to:', wsUrl);
    console.log('🔑 Using token:', token);
    console.log('🏠 Current hostname:', window.location.hostname);
    console.log('📍 Room ID:', room.id);
    console.log('👤 User ID:', user?.id);
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✅ WebSocket OPENED successfully for room:', room.id);
      console.log('✅ WebSocket readyState:', ws.readyState);
      setSocket(ws);
    };

    ws.onmessage = (event) => {
      try {
        console.log('📨 Received WebSocket message:', event.data);
        const messageData = JSON.parse(event.data);
        if (messageData.type === 'new_message') {
          setMessages(prev => [...prev, messageData]);
          // Scroll to bottom when new message arrives
          setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        }
      } catch (error) {
        console.error('❌ Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket ERROR occurred:', error);
      console.error('❌ WebSocket URL was:', wsUrl);
      console.error('❌ WebSocket state:', ws.readyState);
      console.error('❌ Token used:', token);
    };

    ws.onclose = (event) => {
      console.log('🔌 WebSocket CLOSED for room:', room.id);
      console.log('🔌 Close code:', event.code);
      console.log('🔌 Close reason:', event.reason);
      console.log('🔌 Was clean?:', event.wasClean);
      setSocket(null);
    };

    setSocket(ws);

    return () => {
      ws.close();
      setSocket(null);
    };
  }, [room?.id, isOpen, user]);

  // Load message history and merge with real-time messages
  useEffect(() => {
    if (messageHistory?.messages) {
      setMessages(messageHistory.messages);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'auto' }), 100);
    }
  }, [messageHistory]);

  const handleSendMessage = async () => {
    if (!message.trim() || !room?.id || sendMessageMutation.isPending) return;

    const messageContent = message.trim();
    setMessage("");

    // Send via WebSocket for immediate response
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ content: messageContent }));
    } else {
      // Fallback to HTTP if WebSocket isn't available
      try {
        await sendMessageMutation.mutateAsync(messageContent);
      } catch (error) {
        console.error('Failed to send message:', error);
      }
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString();
    }
  };

  // Group messages by date
  const groupedMessages = messages.reduce((groups, msg) => {
    const date = new Date(msg.sent_at).toDateString();
    if (!groups[date]) {
      groups[date] = [];
    }
    groups[date].push(msg);
    return groups;
  }, {} as Record<string, Message[]>);

  if (!room) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl h-[600px] p-0 flex flex-col" data-testid="dialog-chat-room">
        <DialogHeader className="px-6 py-4 border-b">
          <DialogTitle className="flex items-center space-x-3">
            <Avatar className="h-10 w-10">
              <AvatarFallback>{room.avatar}</AvatarFallback>
            </Avatar>
            <div>
              <div className="font-semibold">{room.name}</div>
              <div className="text-sm text-muted-foreground">
                {room.is_group ? 'Group chat' : 'Direct message'}
              </div>
            </div>
          </DialogTitle>
        </DialogHeader>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-sm text-muted-foreground">Loading messages...</div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-center">
              <MessageCircle className="h-12 w-12 text-muted-foreground mb-2" />
              <div className="text-sm text-muted-foreground">No messages yet</div>
              <div className="text-xs text-muted-foreground">Start the conversation!</div>
            </div>
          ) : (
            <div className="space-y-4">
              {Object.entries(groupedMessages).map(([date, dayMessages]) => (
                <div key={date}>
                  {/* Date separator */}
                  <div className="flex items-center justify-center my-4">
                    <div className="text-xs text-muted-foreground bg-background px-3 py-1 rounded-full border">
                      {formatDate(dayMessages[0].sent_at)}
                    </div>
                  </div>
                  
                  {/* Messages for this day */}
                  {dayMessages.map((msg) => {
                    const isOwn = msg.sender_id === user?.id;
                    return (
                      <div
                        key={msg.id}
                        className={cn(
                          "flex items-start space-x-3 mb-4",
                          isOwn && "flex-row-reverse space-x-reverse"
                        )}
                        data-testid={`message-${msg.id}`}
                      >
                        <Avatar className="h-8 w-8 mt-1">
                          <AvatarImage src={msg.sender?.avatar} alt={msg.sender?.username} />
                          <AvatarFallback>
                            {msg.sender?.username?.[0]?.toUpperCase() || '?'}
                          </AvatarFallback>
                        </Avatar>
                        <div className={cn("flex-1 max-w-[70%]", isOwn && "flex flex-col items-end")}>
                          <div className={cn("text-xs text-muted-foreground mb-1", isOwn && "text-right")}>
                            {msg.sender?.username} • {formatTime(msg.sent_at)}
                          </div>
                          <div
                            className={cn(
                              "px-4 py-2 rounded-lg break-words",
                              isOwn
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-foreground"
                            )}
                          >
                            {msg.content}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Message Input */}
        <div className="px-6 py-4 border-t">
          <div className="flex space-x-2">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type a message..."
              onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
              disabled={sendMessageMutation.isPending || !socket || socket.readyState !== WebSocket.OPEN}
              data-testid="input-message"
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!message.trim() || sendMessageMutation.isPending || !socket || socket.readyState !== WebSocket.OPEN}
              size="icon"
              data-testid="button-send-message"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          {(!socket || socket.readyState !== WebSocket.OPEN) && (
            <div className="text-xs text-muted-foreground mt-2 text-center">
              Connecting to chat...
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}