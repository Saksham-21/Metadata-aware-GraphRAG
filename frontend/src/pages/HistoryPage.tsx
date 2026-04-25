import React, { useEffect, useState } from 'react';
import { Clock, CheckCircle2, MessageSquare } from 'lucide-react';
import { api } from '../api/client';
import { GlassCard } from '../components/ui/GlassCard';
import './HistoryPage.css';

interface QueryHistory {
  id: string;
  question: string;
  created_at: string;
  feedback: string;
}

export const HistoryPage: React.FC = () => {
  const [history, setHistory] = useState<QueryHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await api.get<{ items: QueryHistory[] }>('/query/history');
        setHistory(res.items || []);
      } catch (err: any) {
        setError(err.message || 'Failed to load history');
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div className="page-container history-page animate-fade-in">
      <div className="page-header">
        <h1 className="text-gradient">Query History</h1>
        <p className="text-muted">Review your past explorations</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="history-list">
        {loading ? (
          <div className="loading-state">
            <span className="spinner"></span>
            <p>Loading your history...</p>
          </div>
        ) : history.length === 0 ? (
          <GlassCard className="empty-state">
            <Clock size={48} className="text-muted" />
            <h3>No history yet</h3>
            <p className="text-muted">Your past queries will appear here</p>
          </GlassCard>
        ) : (
          history.map(item => (
            <GlassCard key={item.id} className="history-item">
              <div className="history-item-header">
                <span className="history-question">"{item.question}"</span>
                <span className="history-date">
                  {new Date(item.created_at).toLocaleDateString()}
                </span>
              </div>
              
              <div className="history-meta text-muted">
                <div className="meta-tag">
                  <CheckCircle2 size={14} className="icon-cyan" />
                  <span>Success</span>
                </div>
                {item.feedback !== 'none' && (
                  <div className="meta-tag">
                    <MessageSquare size={14} className="icon-purple" />
                    <span>Feedback Provided</span>
                  </div>
                )}
              </div>
            </GlassCard>
          ))
        )}
      </div>
    </div>
  );
};
