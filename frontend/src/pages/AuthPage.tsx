import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, User as UserIcon } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { GlassCard } from '../components/ui/GlassCard';
import './AuthPage.css';

export const AuthPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
        // Backend API expects JSON body (LoginRequest)
        const data = await api.post<any>('/auth/login', {
          email: email,
          password: password,
        });
        
        // TokenResponse returns access_token, user_id, role, name
        // Our AuthContext expects a User object { id, email, role }
        const userData = {
          id: data.user_id,
          email: email,
          role: data.role,
        };
        
        login(data.access_token, userData);
        navigate('/');
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-layout">
      <GlassCard className="auth-card animate-fade-in">
        <div className="auth-header">
          <h1 className="text-gradient">Welcome Back</h1>
          <p className="text-muted">
            Sign in to access GraphRAG engine
          </p>
        </div>

        {error && <div className={`auth-error ${error.includes('successful') ? 'success' : ''}`}>{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <Input 
            icon={<Mail size={18} />}
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input 
            icon={<Lock size={18} />}
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          
          <Button type="submit" className="auth-submit" isLoading={loading}>
            Sign In
          </Button>
        </form>
      </GlassCard>
    </div>
  );
};
