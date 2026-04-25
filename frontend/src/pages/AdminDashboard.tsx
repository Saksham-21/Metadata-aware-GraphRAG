import React, { useEffect, useState } from 'react';
import { Database, ShieldCheck, RefreshCw, UserPlus, Mail, Lock, User as UserIcon, ChevronDown, Users, Edit2, Save, X } from 'lucide-react';
import { api } from '../api/client';
import { GlassCard } from '../components/ui/GlassCard';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import './AdminDashboard.css';

interface SystemHealth {
  status: string;
  services: {
    postgresql: string;
    chromadb: string;
    neo4j: string;
  };
}

interface UserResponse {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
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
  
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editFormData, setEditFormData] = useState({ name: '', role: '', is_active: true });
  const [updatingUser, setUpdatingUser] = useState(false);

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

  const loadUsers = async () => {
    setLoadingUsers(true);
    try {
      const res = await api.get<{ items: UserResponse[] }>('/auth/users');
      setUsers(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch users');
    } finally {
      setLoadingUsers(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    loadUsers();
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

  const handleEditClick = (u: UserResponse) => {
    setEditingUserId(u.id);
    setEditFormData({ name: u.name, role: u.role, is_active: u.is_active });
  };

  const cancelEdit = () => {
    setEditingUserId(null);
  };

  const handleUpdateUser = async (id: string) => {
    setUpdatingUser(true);
    try {
      await api.patch(`/auth/users/${id}`, editFormData);
      await loadUsers(); // Refresh the list
      setEditingUserId(null);
    } catch (err: any) {
      setError(err.message || 'Failed to update user');
    } finally {
      setUpdatingUser(false);
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
              <span className={`status-badge ${health?.services?.postgresql === 'ok' ? 'ok' : 'error'}`}>
                {loadingHealth ? '...' : health?.services?.postgresql || 'offline'}
              </span>
            </div>
            <div className="status-item">
              <span>ChromaDB</span>
              <span className={`status-badge ${health?.services?.chromadb?.includes('Phase 2') || health?.services?.chromadb === 'ok' ? 'ok' : 'error'}`}>
                {loadingHealth ? '...' : health?.services?.chromadb || 'offline'}
              </span>
            </div>
            <div className="status-item">
              <span>Neo4j</span>
              <span className={`status-badge ${health?.services?.neo4j?.includes('Phase 2') || health?.services?.neo4j === 'ok' ? 'ok' : 'error'}`}>
                {loadingHealth ? '...' : health?.services?.neo4j || 'offline'}
              </span>
            </div>
          </div>

          <Button 
            className="w-full" 
            style={{ marginTop: '1rem' }}
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

          <form onSubmit={handleRegister} className="auth-form" style={{ display: 'flex', flexDirection: 'column', gap: '1rem'}}>
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

      <div style={{ marginTop: '2rem' }}>
        <GlassCard>
          <div className="admin-card-header" style={{ marginBottom: '1.5rem' }}>
            <Users className="icon-cyan" size={24} />
            <h3>System Users Database</h3>
            <Button onClick={loadUsers} variant="secondary" style={{ marginLeft: 'auto', padding: '0.5rem 1rem' }} isLoading={loadingUsers}>
              <RefreshCw size={16} /> Refresh
            </Button>
          </div>
          
          <div style={{ overflowX: 'auto', maxHeight: '400px', overflowY: 'auto', border: '1px solid var(--border-glass)', borderRadius: '8px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '700px' }}>
              <thead style={{ position: 'sticky', top: 0, background: 'rgba(20, 25, 40, 0.95)', backdropFilter: 'blur(10px)', zIndex: 10 }}>
                <tr style={{ borderBottom: '1px solid var(--border-glass)' }}>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Name</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Email</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Role</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Status</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)' }}>Created</th>
                  <th style={{ padding: '1rem', color: 'var(--text-muted)', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => {
                  const isEditing = editingUserId === u.id;
                  
                  return (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border-glass)' }}>
                    <td style={{ padding: '1rem' }}>
                      {isEditing ? (
                        <input 
                           className="input-field" 
                           style={{ padding: '0.5rem', width: '140px' }} 
                           value={editFormData.name} 
                           onChange={e => setEditFormData({...editFormData, name: e.target.value})} 
                        />
                      ) : u.name}
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>{u.email}</td>
                    <td style={{ padding: '1rem' }}>
                      {isEditing ? (
                        <select 
                           className="input-field" 
                           style={{ padding: '0.5rem', width: '120px', appearance: 'none' }} 
                           value={editFormData.role} 
                           onChange={e => setEditFormData({...editFormData, role: e.target.value})}
                        >
                           <option value="admin">Admin</option>
                           <option value="developer">Developer</option>
                           <option value="ba">BA</option>
                           <option value="viewer">Viewer</option>
                        </select>
                      ) : (
                        <span style={{ padding: '0.25rem 0.75rem', borderRadius: '1rem', fontSize: '0.8rem', background: 'rgba(59, 130, 246, 0.1)', color: 'var(--text-accent)' }}>
                          {u.role.toUpperCase()}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '1rem' }}>
                      {isEditing ? (
                        <select 
                           className="input-field" 
                           style={{ padding: '0.5rem', width: '100px', appearance: 'none' }} 
                           value={editFormData.is_active ? 'true' : 'false'} 
                           onChange={e => setEditFormData({...editFormData, is_active: e.target.value === 'true'})}
                        >
                           <option value="true">Active</option>
                           <option value="false">Disabled</option>
                        </select>
                      ) : (
                        <span className={`status-badge ${u.is_active ? 'ok' : 'error'}`}>
                          {u.is_active ? 'Active' : 'Disabled'}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                      {isEditing ? (
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                          <button onClick={() => handleUpdateUser(u.id)} disabled={updatingUser} style={{ background: 'transparent', border: 'none', color: '#10b981', cursor: 'pointer', padding: '0.25rem' }} title="Save">
                            <Save size={18} />
                          </button>
                          <button onClick={cancelEdit} disabled={updatingUser} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '0.25rem' }} title="Cancel">
                            <X size={18} />
                          </button>
                        </div>
                      ) : (
                        <button onClick={() => handleEditClick(u)} style={{ background: 'transparent', border: 'none', color: 'var(--text-accent)', cursor: 'pointer', padding: '0.5rem' }} title="Edit">
                          <Edit2 size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                )})}
                {users.length === 0 && !loadingUsers && (
                  <tr>
                    <td colSpan={6} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No users found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>
    </div>
  );
};
