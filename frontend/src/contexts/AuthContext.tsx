import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';
import { useNavigate } from 'react-router-dom';

export interface User {
  id: string;
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (token: string, userData: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUser = async () => {
      const token = localStorage.getItem('jwt_token');
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const userData = await api.get<User>('/auth/me');
        setUser(userData);
      } catch (err) {
        console.error('Failed to fetch user session', err);
        localStorage.removeItem('jwt_token');
      } finally {
        setIsLoading(false);
      }
    };

    fetchUser();
  }, []);

  const login = (token: string, userData: User) => {
    localStorage.setItem('jwt_token', token);
    setUser(userData);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout', {});
    } catch (e) {
      console.warn("Logout request failed or unauthorized, but clearing locally");
    } finally {
      localStorage.removeItem('jwt_token');
      setUser(null);
      navigate('/login');
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
