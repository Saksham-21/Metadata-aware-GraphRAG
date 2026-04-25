import React, { useState } from 'react';
import { Search, Sparkles, Server } from 'lucide-react';
import { api } from '../api/client';
import { GlassCard } from '../components/ui/GlassCard';
import './QueryDashboard.css';

interface QueryResult {
  query_id: string;
  question: string;
  primary_results: any[];
  cross_section_expansions: any[];
  suggested_sql?: string;
  explanation: string;
  section_filter?: string;
}

import './QueryDashboard.css';

export const QueryDashboard: React.FC = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState('');

  const submitQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    try {
      const res = await api.post<QueryResult>('/query', {
        question: query,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to execute query');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container query-dashboard animate-fade-in">
      <div className="dashboard-header">
        <h1 className="text-gradient">Metadata-Aware GraphRAG</h1>
        <p className="text-muted">Navigate your database schemas with natural language</p>
      </div>

      <GlassCard className="search-card">
        <form onSubmit={submitQuery} className="search-form">
          <Search className="search-icon" size={24} />
          <input 
            type="text" 
            className="search-input"
            placeholder="Ask a question about your database (e.g. 'Show me columns related to users')"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="search-btn" disabled={loading || !query.trim()}>
            {loading ? <span className="spinner small"></span> : <Sparkles size={20} />}
          </button>
        </form>
      </GlassCard>

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div className="results-container animate-fade-in">
          <GlassCard className="result-card explanation-card">
            <h3 className="card-title">
              <Sparkles size={18} className="icon-cyan" /> 
              Engine Response
            </h3>
            <p className="explanation-text">{result.explanation}</p>
          </GlassCard>

          {result.suggested_sql && (
             <GlassCard className="result-card sql-card">
               <h3 className="card-title">
                 <Server size={18} className="icon-purple" /> 
                 Suggested SQL
               </h3>
               <pre className="sql-code"><code>{result.suggested_sql}</code></pre>
             </GlassCard>
          )}

          <div className="graph-insights">
            {/* Phase 2: Iterate over primary_results and cross_section_expansions */}
            {(result.primary_results?.length > 0 || result.cross_section_expansions?.length > 0) && (
              <p className="text-muted">Detailed schema entities found. (Phase 2 integration needed to render complex graphs)</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
