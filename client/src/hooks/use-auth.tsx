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
      try {
        // Check if there's a token in localStorage
        const storedToken = localStorage.getItem('auth_token');
        const storedUser = localStorage.getItem('auth_user');
        
        if (storedToken) {
          setToken(storedToken);
          
          // Fetch fresh user data from backend to ensure premium status is current
          try {
            const userData = await authApi.getCurrentUser();
            setUser(userData);
            localStorage.setItem('auth_user', JSON.stringify(userData));
          } catch (error) {
            // If token is invalid, try to use stored user data as fallback
            if (storedUser) {
              const parsedUser = JSON.parse(storedUser);
              setUser(parsedUser);
            } else {
              // Token is invalid and no stored user, clear auth
              setToken(null);
              setUser(null);
              localStorage.removeItem('auth_token');
              localStorage.removeItem('auth_user');
            }
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
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
