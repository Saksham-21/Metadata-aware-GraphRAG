import React from 'react';
import './Input.css';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({ 
  label, 
  error, 
  icon, 
  className = '', 
  id, 
  ...props 
}) => {
  const inputId = id || Math.random().toString(36).substring(7);

  return (
    <div className={`input-container ${className}`}>
      {label && <label htmlFor={inputId} className="input-label">{label}</label>}
      <div className="input-wrapper">
        {icon && <span className="input-icon">{icon}</span>}
        <input 
          id={inputId} 
          className={`input-field ${icon ? 'with-icon' : ''} ${error ? 'error' : ''}`}
          {...props} 
        />
      </div>
      {error && <span className="input-error">{error}</span>}
    </div>
  );
};
