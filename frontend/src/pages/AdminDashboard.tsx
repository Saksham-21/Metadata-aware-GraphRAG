import React, { useEffect, useState } from 'react';
import { Database, ShieldCheck, RefreshCw, UserPlus, Mail, Lock, User as UserIcon, ChevronDown } from 'lucide-react';
import { api } from '../api/client';
import { GlassCard } from '../components/ui/GlassCard';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import './AdminDashboard.css';

interface SystemHealth {
  status: string;
  postgres: string;
  chromadb: string;
  neo4j: string;
}

export const AdminDashboard: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('viewer');
  const [registering, setRegistering] = useState(false);
  const [regMsg, setRegMsg] = useState('');

  const fetchHealth = async () => {
    setLoadingHealth(true);
    try {
      const res = await api.get<SystemHealth>('/admin/health');
      setHealth(res);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to fetch system health');
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const triggerSync = async () => {
    setSyncing(true);
    try {
      await api.post('/admin/force-reindex', {});
      await fetchHealth();
    } catch (err: any) {
      setError(err.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegMsg('');
    setRegistering(true);
    try {
      await api.post('/auth/register', { name, email, password, role });
      setRegMsg('User created successfully.');
      setName('');
      setEmail('');
      setPassword('');
      setRole('viewer');
    } catch (err: any) {
      setRegMsg(err.message || 'Registration failed');
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div className="page-container admin-dashboard animate-fade-in">
      <div className="page-header">
        <h1 className="text-gradient">Admin Center</h1>
        <p className="text-muted">Manage system configuration and data ingestion</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="admin-grid">
        <GlassCard className="admin-card">
          <div className="admin-card-header">
            <ShieldCheck className="icon-cyan" size={24} />
            <h3>System Status</h3>
          </div>
          
          <div className="status-list">
            <div className="status-item">
              <span>PostgreSQL</span>
              <span className={`status-badge ${health?.postgres === 'ok' ? 'ok' : 'error'}`}>
                {loadingHealth ? '...' : health?.postgres || 'offline'}
              </span>
            </div>
            <div className="status-item">
              <span>ChromaDB</span>
              <span className={`status-badge ${health?.chromadb === 'ok' ? 'ok' : 'error'}`}>
                {loadingHealth ? '...' : health?.chromadb || 'offline'}
              </span>
            </div>
            <div className="status-item">
              <span>Neo4j</span>
              <span className={`status-badge ${health?.neo4j === 'ok' ? 'ok' : 'error'}`}>
                {loadingHealth ? '...' : health?.neo4j || 'offline'}
              </span>
            </div>
          </div>

          <Button 
            className="w-full mt-4" 
            variant="secondary"
            onClick={fetchHealth}
            isLoading={loadingHealth}
          >
            Check Status
          </Button>
        </GlassCard>

        <GlassCard className="admin-card">
          <div className="admin-card-header">
            <Database className="icon-purple" size={24} />
            <h3>Data Ingestion</h3>
          </div>
          <p className="text-muted mb-4">
            Push structural data from PostgreSQL to Vector DB and Graph DB engines to make it available for GraphRAG queries.
          </p>
          <Button 
            className="w-full"
            onClick={triggerSync}
            isLoading={syncing}
          >
            <RefreshCw size={18} className={syncing ? 'spin' : ''} />
            {syncing ? 'Indexing...' : 'Force Full Re-index'}
          </Button>
        </GlassCard>
      </div>

      <div className="admin-grid" style={{ marginTop: '1.5rem' }}>
        <GlassCard className="admin-card">
          <div className="admin-card-header">
            <UserPlus className="icon-cyan" size={24} />
            <h3>Create User Account</h3>
          </div>
          <p className="text-muted mb-4">
            Manually assign accounts and roles to internal team members.
          </p>

          {regMsg && (
            <div className={`auth-error ${regMsg.includes('successfully') ? 'success' : ''}`} style={{ marginBottom: '1rem', padding: '0.75rem', borderRadius: '8px', border: '1px solid', borderColor: regMsg.includes('successfully') ? 'var(--border-glass-glow)' : 'rgba(255, 77, 79, 0.3)', backgroundColor: regMsg.includes('successfully') ? 'rgba(59, 130, 246, 0.1)' : 'rgba(255, 77, 79, 0.1)', color: regMsg.includes('successfully') ? 'var(--text-accent)' : '#ff4d4f' }}>
              {regMsg}
            </div>
          )}

          <form onSubmit={handleRegister} className="auth-form" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <Input 
              icon={<UserIcon size={18} />}
              placeholder="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
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
              placeholder="Secure Password (Upper + Digit)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            
            <div className="input-container">
              <label className="input-label">Role</label>
              <div className="input-wrapper" style={{ position: 'relative' }}>
                <select 
                  className="input-field" 
                  value={role} 
                  onChange={(e) => setRole(e.target.value)}
                  style={{ paddingLeft: '1rem', appearance: 'none', WebkitAppearance: 'none', background: 'rgba(11, 15, 25, 0.4)', color: 'var(--text-main)', paddingRight: '2.5rem', width: '100%' }}
                >
                  <option value="admin">Admin</option>
                  <option value="developer">Developer</option>
                  <option value="ba">BA</option>
                  <option value="viewer">Viewer</option>
                </select>
                <div style={{ position: 'absolute', right: '1rem', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
                  <ChevronDown size={18} />
                </div>
              </div>
            </div>
            
            <Button type="submit" isLoading={registering} style={{ marginTop: '0.5rem' }}>
              Create Account
            </Button>
          </form>
        </GlassCard>
      </div>
    </div>
  );
};
