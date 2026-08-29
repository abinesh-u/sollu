import React from 'react';
import type { Task, TokenUsage } from '../types';
import './StatsBar.css';

interface StatsBarProps {
  tasks: Task[];
}

const formatCompact = (num: number) => {
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
  return num.toLocaleString();
};

export const StatsBar: React.FC<StatsBarProps> = ({ tasks }) => {
  const notesMap = new Map<string, TokenUsage>();
  tasks.forEach((t) => {
    if (t.correlation_id && t.usage && !notesMap.has(t.correlation_id)) {
      notesMap.set(t.correlation_id, t.usage);
    }
  });

  const usages = Array.from(notesMap.values());
  const noteCount = usages.length;
  const totalTokens = usages.reduce((sum, u) => sum + (u.total || 0), 0);

  const tokenStr = totalTokens > 0 ? formatCompact(totalTokens) : '0';
  const tokenNum = tokenStr.replace(/[KM]/, '');
  const tokenSuffix = tokenStr.match(/[KM]/)?.[0] || '';

  return (
    <div className="stats-band" aria-label="Dashboard statistics">
      <div className="stats-tile">
        <span className="stats-figure">{noteCount.toLocaleString()}</span>
        <span className="stats-label">Notes Processed</span>
      </div>

      <div className="stats-tile">
        <span className="stats-figure">
          {tokenNum}
          <span className="stats-figure-suffix">{tokenSuffix}</span>
        </span>
        <span className="stats-label">Total Tokens</span>
      </div>
    </div>
  );
};
