import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';

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

interface SendMessageRequest {
  receiverId: string;
  content: string;
}

interface UseChatApiReturn {
  searchUsers: (query: string) => void;
  users: User[];
  isSearching: boolean;
  sendMessageApi: (data: SendMessageRequest) => Promise<void>;
  getChatHistory: (userId: string) => Promise<Message[]>;
}

export function useChatApi(): UseChatApiReturn {
  const [users, setUsers] = useState<User[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const queryClient = useQueryClient();

  // Search users function
  const searchUsers = useCallback(async (query: string) => {
    if (!query.trim()) {
      setUsers([]);
      return;
    }

    setIsSearching(true);
    setSearchQuery(query);

    try {
      const response = await apiRequest('GET', `/api/users/search?q=${encodeURIComponent(query)}`);
      const userData = await response.json();
      setUsers(userData || []);
    } catch (error) {
      console.error('Error searching users:', error);
      setUsers([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (data: SendMessageRequest) => {
      const response = await apiRequest('POST', '/api/chat/send', data);
      return response.json();
    },
    onSuccess: () => {
      // Invalidate chat history queries
      queryClient.invalidateQueries({ queryKey: ['/api/chat/history'] });
    },
    onError: (error) => {
      console.error('Error sending message:', error);
    },
  });

  // Get chat history function
  const getChatHistory = useCallback(async (userId: string): Promise<Message[]> => {
    try {
      const response = await apiRequest('GET', `/api/chat/history/${userId}`);
      const historyData = await response.json();
      return historyData || [];
    } catch (error) {
      console.error('Error fetching chat history:', error);
      return [];
    }
  }, []);

  const sendMessageApi = useCallback(async (data: SendMessageRequest) => {
    return sendMessageMutation.mutateAsync(data);
  }, [sendMessageMutation]);

  return {
    searchUsers,
    users,
    isSearching,
    sendMessageApi,
    getChatHistory,
  };
}