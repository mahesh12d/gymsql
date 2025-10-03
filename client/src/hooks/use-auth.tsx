import { useState, useEffect, createContext, useContext } from 'react';
import { authApi } from '@/lib/auth';

interface User {
  id: string;
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  profileImageUrl?: string;
  xp: number;
  level: string;
  problemsSolved: number;
  premium?: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initializeAuth = async () => {
      // Development bypass - automatically log in as a fake user
      if (import.meta.env.DEV) {
        const fakeToken = 'dev-token-123';
        
        try {
          // Fetch real user data from API even in dev mode
          const userData = await authApi.getCurrentUser();
          setUser(userData);
          setToken(fakeToken);
          localStorage.setItem('auth_token', fakeToken);
          localStorage.setItem('auth_user', JSON.stringify(userData));
        } catch (error) {
          // Fallback to fake user if API fails
          const fakeUser: User = {
            id: 'dev-user-1',
            username: 'developer',
            email: 'dev@sqlgym.dev',
            firstName: 'Dev',
            lastName: 'User',
            xp: 1000,
            level: 'Advanced',
            problemsSolved: 2,
            premium: true
          };
          setUser(fakeUser);
          setToken(fakeToken);
          localStorage.setItem('auth_token', fakeToken);
          localStorage.setItem('auth_user', JSON.stringify(fakeUser));
        }
        setIsLoading(false);
        return;
      }

      try {
        // Always attempt to fetch current user data from backend
        // This supports both token-based and cookie-based authentication
        const userData = await authApi.getCurrentUser();
        setUser(userData);
        
        // Get token from localStorage if available (for token-based auth)
        const storedToken = localStorage.getItem('auth_token');
        if (storedToken) {
          setToken(storedToken);
        }
        
        // Update localStorage with fresh user data
        localStorage.setItem('auth_user', JSON.stringify(userData));
      } catch (error) {
        // Authentication failed - clear all auth state
        setToken(null);
        setUser(null);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('auth_token', newToken);
    localStorage.setItem('auth_user', JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
  };

  const value = {
    user,
    token,
    login,
    logout,
    isAuthenticated: !!user && !!token,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
