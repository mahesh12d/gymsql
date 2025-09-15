import { useState, useEffect, createContext, useContext } from 'react';

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
  // TEMPORARY: Mock user for development purposes (using real user from database)
  const mockUser: User = {
    id: '880be3c3-e093-4274-9294-d20c5f08c583',
    username: 'demo12s',
    email: 'demo@demo.com',
    firstName: 'demo',
    lastName: 'deom',
    profileImageUrl: undefined,
    xp: 500,
    level: 'SQL Trainee',
    problemsSolved: 5,
  };

  const [user, setUser] = useState<User | null>(mockUser);
  const [token, setToken] = useState<string | null>('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI4ODBiZTNjMy1lMDkzLTQyNzQtOTI5NC1kMjBjNWYwOGM1ODMiLCJ1c2VybmFtZSI6ImRlbW8xMnMiLCJleHAiOjE3NTgwMzgzNDV9.xFadvOmd5EoIF40JSWTG87pJVv3XwRPYamXf69iL_DM');
  const [isLoading, setIsLoading] = useState(false); // Set to false to skip loading

  useEffect(() => {
    // TEMPORARY: Skip auth check for development
    // Uncomment below for normal auth behavior
    /*
    // Check for stored token on app start
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');
    
    if (storedToken && storedUser) {
      try {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      } catch (error) {
        console.error('Error parsing stored user data:', error);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
      }
    }
    */
    
    setIsLoading(false);
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
