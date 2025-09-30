import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageCircle, User, Send, ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import { useChatApi } from '@/hooks/use-chat-api';
import { useChatWebSocket } from '@/hooks/use-chat-websocket';
import { useToast } from '@/hooks/use-toast';
import { formatDistanceToNow } from 'date-fns';

interface Conversation {
  conversation_id: string;
  other_user_id: string;
  other_user_username: string;
  last_message: string;
  last_message_timestamp: string;
  unread_count?: number;
}

export function CommunityChatBox() {
  const { user: currentUser, token } = useAuth();
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const { sendMessageApi, getChatHistory } = useChatApi();
  const { messages: wsMessages, isConnected, connect, disconnect } = useChatWebSocket(currentUser?.id, token);
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentConversationRef = useRef<string | null>(null);

  const { data: conversations = [], isLoading } = useQuery<Conversation[]>({
    queryKey: ['/api/chat/conversations'],
    queryFn: async () => {
      const response = await fetch('/api/chat/conversations', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch conversations');
      }
      return response.json();
    },
    enabled: !!currentUser && !!token,
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (currentUser?.id && token) {
      connect();
    } else {
      disconnect();
    }
    return () => disconnect();
  }, [currentUser?.id, token, connect, disconnect]);

  useEffect(() => {
    if (!selectedConversation) {
      return;
    }
    
    const filteredWsMessages = wsMessages.filter(msg => 
      (msg.sender_id === currentUser?.id && msg.receiver_id === selectedConversation.other_user_id) ||
      (msg.sender_id === selectedConversation.other_user_id && msg.receiver_id === currentUser?.id)
    );
    
    setMessages(prevMessages => {
      const messageMap = new Map();
      [...prevMessages, ...filteredWsMessages].forEach(msg => {
        messageMap.set(msg.id, msg);
      });
      return Array.from(messageMap.values()).sort((a, b) => 
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );
    });
  }, [wsMessages, selectedConversation, currentUser?.id]);

  useEffect(() => {
    if (selectedConversation) {
      currentConversationRef.current = selectedConversation.other_user_id;
      setMessages([]);
      loadChatHistory();
    } else {
      currentConversationRef.current = null;
      setMessages([]);
    }
  }, [selectedConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadChatHistory = async () => {
    if (!selectedConversation?.other_user_id) return;
    
    const conversationId = selectedConversation.other_user_id;
    
    try {
      const history = await getChatHistory(conversationId);
      
      if (currentConversationRef.current !== conversationId) {
        return;
      }
      
      setMessages(prevMessages => {
        const messageMap = new Map();
        [...prevMessages, ...history].forEach(msg => {
          messageMap.set(msg.id, msg);
        });
        return Array.from(messageMap.values()).sort((a, b) => 
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );
      });
    } catch (error) {
      console.error("Error loading chat history:", error);
      toast({
        title: "Error",
        description: "Failed to load chat history",
        variant: "destructive",
      });
    }
  };

  const handleSendMessage = async () => {
    if (!message.trim() || !selectedConversation?.other_user_id || !currentUser) return;

    try {
      await sendMessageApi({
        receiver_id: selectedConversation.other_user_id,
        content: message.trim()
      });
      
      setMessage('');
      loadChatHistory();
    } catch (error) {
      console.error("Error sending message:", error);
      toast({
        title: "Error", 
        description: "Failed to send message",
        variant: "destructive",
      });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTimeAgo = (dateString: string) => {
    if (!dateString) return '';
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch (error) {
      return '';
    }
  };

  if (!currentUser) return null;

  return (
    <Card className="h-[600px] flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center space-x-2">
          {selectedConversation ? (
            <>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setSelectedConversation(null)}
                className="mr-2 h-8 w-8 p-0"
                data-testid="button-back-to-chats"
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <Avatar className="w-6 h-6">
                <AvatarFallback className="text-xs bg-gradient-to-br from-primary/10 to-primary/5 text-primary">
                  {selectedConversation.other_user_username.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <span>{selectedConversation.other_user_username}</span>
            </>
          ) : (
            <>
              <MessageCircle className="w-5 h-5 text-primary" />
              <span>Messages</span>
            </>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
        {!selectedConversation ? (
          <div className="flex-1 overflow-hidden">
            {isLoading ? (
              <div className="p-4 space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex items-center space-x-3 animate-pulse">
                    <div className="w-10 h-10 bg-muted rounded-full" />
                    <div className="flex-1 space-y-1">
                      <div className="h-4 bg-muted rounded w-3/4" />
                      <div className="h-3 bg-muted rounded w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
            ) : conversations.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <User className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="text-sm font-medium">No conversations yet</p>
                <p className="text-xs mt-1">Start chatting with community members!</p>
              </div>
            ) : (
              <ScrollArea className="h-full">
                <div className="space-y-1 p-2">
                  {conversations.map((conversation) => (
                    <div
                      key={conversation.conversation_id}
                      onClick={() => setSelectedConversation(conversation)}
                      className="flex items-center space-x-3 p-3 rounded-lg hover:bg-muted cursor-pointer transition-colors"
                      data-testid={`conversation-${conversation.other_user_id}`}
                    >
                      <Avatar className="w-10 h-10">
                        <AvatarFallback className="bg-gradient-to-br from-primary/10 to-primary/5 text-primary font-semibold">
                          {conversation.other_user_username.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-sm font-medium truncate">
                            {conversation.other_user_username}
                          </p>
                          {conversation.last_message_timestamp && (
                            <span className="text-xs text-muted-foreground">
                              {formatTimeAgo(conversation.last_message_timestamp)}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground truncate">
                          {conversation.last_message || 'No messages yet'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden min-h-0">
            <ScrollArea className="flex-1 p-4">
              {!isConnected && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg p-2 mb-3">
                  <p className="text-xs text-yellow-800 dark:text-yellow-200">
                    Real-time updates unavailable
                  </p>
                </div>
              )}
              
              {messages.length === 0 ? (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <p className="text-sm">No messages yet. Start the conversation!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {messages.map((msg) => {
                    const isOwnMessage = msg.sender_id === currentUser?.id;
                    
                    return (
                      <div 
                        key={msg.id} 
                        className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}
                        data-testid={`message-${msg.id}`}
                      >
                        <div className={`flex flex-col max-w-[75%] ${isOwnMessage ? 'items-end' : 'items-start'}`}>
                          <div className={`px-3 py-2 rounded-lg ${
                            isOwnMessage 
                              ? 'bg-primary text-primary-foreground' 
                              : 'bg-muted text-foreground'
                          }`}>
                            <p className="text-sm break-words">{msg.content}</p>
                          </div>
                          <span className="text-xs text-muted-foreground mt-1">
                            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </ScrollArea>
            
            <div className="p-3 border-t">
              <div className="flex items-center space-x-2">
                <Input
                  placeholder="Type a message..."
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="flex-1"
                  data-testid="input-message"
                />
                <Button 
                  onClick={handleSendMessage}
                  disabled={!message.trim()}
                  size="sm"
                  data-testid="button-send"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
