import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MessageCircle, User, Clock, Bell } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/hooks/use-auth';
import { useChatApi } from '@/hooks/use-chat-api';
import { ChatRoom } from '@/components/ChatRoom';
import { formatDistanceToNow } from 'date-fns';

// Company logo imports
import airbnbLogo from '@assets/logos/airbnb.svg';
import amazonLogo from '@assets/logos/amazon.svg';
import appleLogo from '@assets/logos/apple.svg';
import googleLogo from '@assets/logos/google.svg';
import mcdonaldLogo from '@assets/logos/mcdonald.svg';
import metaLogo from '@assets/logos/meta.svg';
import microsoftLogo from '@assets/logos/microsoft.svg';
import netflixLogo from '@assets/logos/netflix.svg';
import snapchatLogo from '@assets/logos/snapchat.svg';
import stripeLogo from '@assets/logos/stripe.svg';

interface Conversation {
  conversation_id: string;
  other_user_id: string;
  other_user_username: string;
  last_message: string;
  last_message_timestamp: string;
  is_other_user_online: boolean;
  unread_count?: number;
}

// Company logo mapping for users
const companyLogos = [
  airbnbLogo, amazonLogo, appleLogo, googleLogo, mcdonaldLogo,
  metaLogo, microsoftLogo, netflixLogo, snapchatLogo, stripeLogo
];

// Function to get consistent logo for a user based on their ID
const getUserLogo = (userId: string): string => {
  const hash = userId.split('').reduce((a, b) => {
    a = ((a << 5) - a) + b.charCodeAt(0);
    return a & a;
  }, 0);
  return companyLogos[Math.abs(hash) % companyLogos.length];
};

// Function to check if message is recent (within last hour)
const isRecentMessage = (timestamp: string): boolean => {
  if (!timestamp) return false;
  const messageTime = new Date(timestamp);
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
  return messageTime > oneHourAgo;
};

interface RecentChatsProps {
  className?: string;
}

export function RecentChats({ className }: RecentChatsProps) {
  const { user: currentUser } = useAuth();
  const [selectedRoom, setSelectedRoom] = useState<any>(null);
  const [isChatRoomOpen, setIsChatRoomOpen] = useState(false);
  const [hasNewMessages, setHasNewMessages] = useState<Set<string>>(new Set());
  
  // Fetch user conversations
  const { token } = useAuth();
  const { data: conversations = [], isLoading, error } = useQuery<Conversation[]>({
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
                    onClick={() => {
                      handleStartChat(conversation);
                      // Remove notification when chat is opened
                      setHasNewMessages(prev => {
                        const updated = new Set(prev);
                        updated.delete(conversation.other_user_id);
                        return updated;
                      });
                    }}
                    className="flex items-center space-x-3 p-3 rounded-lg hover:bg-muted cursor-pointer transition-all duration-200 hover:scale-[1.02] hover:shadow-sm"
                    data-testid={`conversation-${conversation.other_user_id}`}
                  >
                    <div className="relative">
                      <Avatar className="w-12 h-12 ring-2 ring-background hover:ring-primary/20 transition-all">
                        <AvatarImage 
                          src={getUserLogo(conversation.other_user_id)} 
                          alt={conversation.other_user_username}
                          className="object-contain p-1"
                        />
                        <AvatarFallback className="bg-gradient-to-br from-primary/10 to-primary/5 text-primary font-semibold">
                          {conversation.other_user_username.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      
                      {/* Online status indicator */}
                      {conversation.is_other_user_online && (
                        <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-green-500 rounded-full ring-2 ring-background animate-pulse" />
                      )}
                      
                      {/* New message notification dot */}
                      {(isRecentMessage(conversation.last_message_timestamp) || hasNewMessages.has(conversation.other_user_id)) && (
                        <div className="absolute -top-1 -left-1 w-4 h-4 bg-yellow-500 rounded-full ring-2 ring-background flex items-center justify-center animate-bounce">
                          <Bell className="w-2 h-2 text-white" />
                        </div>
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-medium truncate flex items-center space-x-2">
                          <span>{conversation.other_user_username}</span>
                          {(isRecentMessage(conversation.last_message_timestamp) || hasNewMessages.has(conversation.other_user_id)) && (
                            <span className="text-xs bg-yellow-500 text-white px-1.5 py-0.5 rounded-full font-bold animate-pulse">
                              NEW
                            </span>
                          )}
                        </p>
                        {conversation.last_message_timestamp && (
                          <span className="text-xs text-muted-foreground font-medium">
                            {formatTimeAgo(conversation.last_message_timestamp)}
                          </span>
                        )}
                      </div>
                      
                      <p className="text-xs text-muted-foreground truncate leading-relaxed">
                        {truncateMessage(conversation.last_message)}
                      </p>
                    </div>

                    {/* Status indicators */}
                    <div className="flex flex-col items-end space-y-1">
                      {conversation.is_other_user_online && (
                        <Badge variant="outline" className="text-xs px-2 py-0.5 bg-green-50 border-green-200 text-green-700">
                          <div className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1 animate-pulse" />
                          Online
                        </Badge>
                      )}
                      
                      {(isRecentMessage(conversation.last_message_timestamp) || hasNewMessages.has(conversation.other_user_id)) && (
                        <Badge className="text-xs px-2 py-0.5 bg-yellow-500 hover:bg-yellow-600 text-white font-bold">
                          <Bell className="w-2.5 h-2.5 mr-1" />
                          Unread
                        </Badge>
                      )}
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