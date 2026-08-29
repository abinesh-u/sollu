import React from 'react';
import { motion } from 'framer-motion';
import './TrustRung.css';

interface TrustRungProps {
  score: number;
  max?: number;
  className?: string;
}

/** Horizontal segmented approvals bar — fills left to right as a class earns trust. */
export const TrustRung: React.FC<TrustRungProps> = ({ score, max = 3, className = '' }) => {
  const bounded = Math.max(0, Math.min(score, max));

  return (
    <div
      className={`trust-rung-bar ${className}`}
      role="img"
      aria-label={`Approvals: ${bounded} of ${max}`}
    >
      {Array.from({ length: max }, (_, i) => {
        const isActive = i < bounded;
        return (
          <motion.div
            key={i}
            className={`trust-rung-segment ${isActive ? 'is-active' : ''}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.32, ease: [0.2, 0.6, 0.3, 1] }}
          />
        );
      })}
    </div>
  );
};
