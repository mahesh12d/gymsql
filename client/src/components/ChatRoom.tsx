import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Send, X } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { useChatApi } from "@/hooks/use-chat-api";
import { useChatWebSocket } from "@/hooks/use-chat-websocket";
import { useToast } from "@/hooks/use-toast";

interface ChatRoomProps {
  isOpen: boolean;
  onClose: () => void;
  room: {
    id: string;
    name: string;
    avatar: string;
    userId?: string;
  };
}

export function ChatRoom({ isOpen, onClose, room }: ChatRoomProps) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const { user: currentUser, token } = useAuth();
  const { sendMessageApi, getChatHistory } = useChatApi();
  const { messages: wsMessages, isConnected, connect, disconnect } = useChatWebSocket(currentUser?.id, token);
  const { toast } = useToast();

  // Connect WebSocket when room opens
  useEffect(() => {
    if (isOpen && currentUser?.id && token) {
      connect();
    } else {
      disconnect();
    }
    
    return () => disconnect();
  }, [isOpen, currentUser?.id, token, connect, disconnect]);

  // Load chat history when room opens
  useEffect(() => {
    if (isOpen && room?.userId && currentUser?.id) {
      loadChatHistory();
    }
  }, [isOpen, room?.userId, currentUser?.id]);

  // Update messages from WebSocket
  useEffect(() => {
    setMessages(wsMessages);
  }, [wsMessages]);

  const loadChatHistory = async () => {
    if (!room?.userId) return;
    
    try {
      const history = await getChatHistory(room.userId);
      setMessages(history);
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
    if (!message.trim() || !room?.userId || !currentUser) return;

    try {
      await sendMessageApi({
        receiver_id: room.userId,
        content: message.trim()
      });
      
      setMessage("");
      
      // Refresh chat history to show the sent message
      await loadChatHistory();
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
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!room) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl h-[600px] flex flex-col" data-testid="dialog-chat-room">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between" data-testid="text-room-name">
            <div className="flex items-center space-x-3">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-gradient-to-br from-purple-400 to-blue-500 text-white">
                  {room.avatar}
                </AvatarFallback>
              </Avatar>
              <span>{room.name}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose} data-testid="button-close-chat">
              <X className="h-4 w-4" />
            </Button>
          </DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 flex flex-col space-y-4">
          <div className="flex-1 p-4 border rounded-lg overflow-y-auto" data-testid="scroll-messages">
            {!isConnected && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg p-3 mb-3">
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  Real-time updates unavailable. Messages will still be delivered.
                </p>
              </div>
            )}
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <p>No messages yet. Start the conversation!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((msg) => {
                  const isOwnMessage = msg.sender_id === currentUser?.id;
                  const senderName = isOwnMessage ? "You" : (msg.sender_username || "Unknown");
                  const senderInitial = isOwnMessage ? "Y" : (msg.sender_username?.charAt(0) || "U");
                  
                  return (
                    <div key={msg.id} className={`flex items-start space-x-3 ${isOwnMessage ? 'flex-row-reverse space-x-reverse' : ''}`} data-testid={`message-${msg.id}`}>
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className={`text-white text-xs ${isOwnMessage ? 'bg-blue-500' : 'bg-gray-500'}`}>
                          {senderInitial}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className={`flex items-center space-x-2 mb-1 ${isOwnMessage ? 'flex-row-reverse space-x-reverse' : ''}`}>
                          <span className="font-medium text-sm">{senderName}</span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(msg.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className={`inline-block px-3 py-2 rounded-lg max-w-xs ${
                          isOwnMessage 
                            ? 'bg-blue-500 text-white ml-auto' 
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                        }`}>
                          <p className="text-sm">{msg.content}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          
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
      </DialogContent>
    </Dialog>
  );
}