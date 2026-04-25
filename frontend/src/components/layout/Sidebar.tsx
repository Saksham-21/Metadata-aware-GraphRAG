import React from 'react';
import { NavLink } from 'react-router-dom';
import { Search, Clock, Database, User as UserIcon, LogOut } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import './Sidebar.css';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const isAdmin = user?.role === 'admin' || user?.role === 'superuser';

  return (
    <aside className="sidebar glass-panel">
      <div className="sidebar-header">
        <Database className="logo-icon" />
        <h2 className="logo-text text-gradient">GraphRAG</h2>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Search size={20} />
          <span>Query</span>
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Clock size={20} />
          <span>History</span>
        </NavLink>
        {isAdmin && (
          <NavLink to="/admin" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <UserIcon size={20} />
            <span>Admin</span>
          </NavLink>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">
            <UserIcon size={18} />
          </div>
          <span className="sidebar-user-email">{user?.email || 'Guest'}</span>
        </div>
        <button className="sidebar-logout-btn" onClick={logout} title="Log out">
          <LogOut size={16} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
};
