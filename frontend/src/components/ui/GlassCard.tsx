import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export const GlassCard: React.FC<GlassCardProps> = ({ 
  children, 
  className = '', 
  onClick 
}) => {
  return (
    <div 
      className={`glass-panel ${className}`} 
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default', padding: '1.5rem' }}
    >
      {children}
    </div>
  );
};
