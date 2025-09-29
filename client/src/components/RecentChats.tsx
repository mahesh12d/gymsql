import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageCircle, User, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/hooks/use-auth';
import { useChatApi } from '@/hooks/use-chat-api';
import { ChatRoom } from '@/components/ChatRoom';
import { formatDistanceToNow } from 'date-fns';

interface Conversation {
  conversation_id: string;
  other_user_id: string;
  other_user_username: string;
  last_message: string;
  last_message_timestamp: string;
  is_other_user_online: boolean;
}

interface RecentChatsProps {
  className?: string;
}

export function RecentChats({ className }: RecentChatsProps) {
  const { user: currentUser } = useAuth();
  const [selectedRoom, setSelectedRoom] = useState<any>(null);
  const [isChatRoomOpen, setIsChatRoomOpen] = useState(false);
  
  // Fetch user conversations
  const { data: conversations = [], isLoading, error } = useQuery<Conversation[]>({
    queryKey: ['/api/chat/conversations'],
    queryFn: async () => {
      const response = await fetch('/api/chat/conversations', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch conversations');
      }
      return response.json();
    },
    enabled: !!currentUser,
    refetchInterval: 5000, // Refresh every 5 seconds for new messages
  });

  const handleStartChat = (conversation: Conversation) => {
    setSelectedRoom({
      id: conversation.conversation_id,
      name: conversation.other_user_username,
      avatar: conversation.other_user_username.charAt(0).toUpperCase(),
      userId: conversation.other_user_id
    });
    setIsChatRoomOpen(true);
  };

  const formatTimeAgo = (dateString: string) => {
    if (!dateString) return '';
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch (error) {
      return '';
    }
  };

  const truncateMessage = (message: string, maxLength: number = 50) => {
    if (!message) return 'No messages yet';
    return message.length > maxLength ? `${message.substring(0, maxLength)}...` : message;
  };

  if (!currentUser) return null;

  return (
    <>
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center space-x-2">
            <MessageCircle className="w-5 h-5 text-primary" />
            <span>Recent Chats</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
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
          ) : error ? (
            <div className="p-4 text-center text-muted-foreground">
              <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Unable to load chats</p>
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              <User className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No conversations yet</p>
              <p className="text-xs mt-1">Start chatting with community members!</p>
            </div>
          ) : (
            <ScrollArea className="h-64">
              <div className="space-y-1 p-2">
                {conversations.map((conversation) => (
                  <div
                    key={conversation.conversation_id}
                    onClick={() => handleStartChat(conversation)}
                    className="flex items-center space-x-3 p-3 rounded-lg hover:bg-muted cursor-pointer transition-colors"
                    data-testid={`conversation-${conversation.other_user_id}`}
                  >
                    <div className="relative">
                      <Avatar className="w-10 h-10">
                        <AvatarImage src="" alt={conversation.other_user_username} />
                        <AvatarFallback>
                          {conversation.other_user_username.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      {conversation.is_other_user_online && (
                        <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full ring-2 ring-background" />
                      )}
                    </div>
                    
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
                        {truncateMessage(conversation.last_message)}
                      </p>
                    </div>

                    {/* Unread indicator (could be enhanced with actual unread count) */}
                    <div className="flex items-center space-x-1">
                      {conversation.is_other_user_online && (
                        <Badge variant="secondary" className="text-xs px-1 py-0">
                          Online
                        </Badge>
                      )}
                      <Clock className="w-3 h-3 text-muted-foreground" />
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Chat Room Modal */}
      {selectedRoom && (
        <ChatRoom
          isOpen={isChatRoomOpen}
          onClose={() => {
            setIsChatRoomOpen(false);
            setSelectedRoom(null);
          }}
          room={selectedRoom}
        />
      )}
    </>
  );
}