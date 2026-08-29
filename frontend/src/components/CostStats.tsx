import React from 'react';
import type { Task, TokenUsage } from '../types';

interface CostStatsProps {
  tasks: Task[];
}

export const CostStats: React.FC<CostStatsProps> = ({ tasks }) => {
  const notesMap = new Map<string, TokenUsage>();
  tasks.forEach((t) => {
    if (t.correlation_id && t.usage && !notesMap.has(t.correlation_id)) {
      notesMap.set(t.correlation_id, t.usage);
    }
  });

  const usages = Array.from(notesMap.values());
  const noteCount = usages.length;
  const totalTokens = usages.reduce((sum, u) => sum + (u.total || 0), 0);

  const formatCompact = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toLocaleString();
  };

  const tokenStr = formatCompact(totalTokens);
  const tokenNum = totalTokens > 0 ? tokenStr.replace(/[KM]/, '') : '0';
  const tokenSuffix = totalTokens > 0 ? tokenStr.match(/[KM]/)?.[0] || '' : '';

  return (
    <div className="bg-[#2a6f2b] p-6 sm:p-12 rounded-[24px] grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
      
      {/* Notes Processed Block */}
      <div className="bg-[#043f2e] rounded-[16px] p-8 sm:p-12 flex flex-col items-center justify-center text-center shadow-[inset_0_1px_3px_rgba(0,0,0,0.2)]">
        <span className="text-[64px] sm:text-[96px] font-sans font-bold text-[#eef2e3] tracking-tighter leading-[1] mb-2">
          {noteCount.toLocaleString()}
        </span>
        <span className="text-base sm:text-xl font-sans text-[#eef2e3]/90 font-medium">
          Notes Processed
        </span>
      </div>

      {/* Total Tokens Block */}
      <div className="bg-[#043f2e] rounded-[16px] p-8 sm:p-12 flex flex-col items-center justify-center text-center shadow-[inset_0_1px_3px_rgba(0,0,0,0.2)]">
        <span className="text-[64px] sm:text-[96px] font-sans font-bold text-[#eef2e3] tracking-tighter leading-[1] mb-2 flex items-baseline">
          {tokenNum}
          <span className="text-[#c8f169]">{tokenSuffix}</span>
        </span>
        <span className="text-base sm:text-xl font-sans text-[#eef2e3]/90 font-medium">
          Total Tokens
        </span>
      </div>

    </div>
  );
};
