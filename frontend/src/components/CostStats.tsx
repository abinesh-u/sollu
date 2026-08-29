import React from 'react';
import type { Task, TokenUsage } from '../types';
import { BarChart2 } from 'lucide-react';

interface CostStatsProps {
  tasks: Task[];
}

export const CostStats: React.FC<CostStatsProps> = ({ tasks }) => {
  // De-duplicate token usage by correlation_id
  const notesMap = new Map<string, TokenUsage>();
  tasks.forEach((t) => {
    if (t.correlation_id && t.usage && !notesMap.has(t.correlation_id)) {
      notesMap.set(t.correlation_id, t.usage);
    }
  });

  const usages = Array.from(notesMap.values());
  const noteCount = usages.length;
  const totalTokens = usages.reduce((sum, u) => sum + (u.total || 0), 0);
  const avgTokens = noteCount ? Math.round(totalTokens / noteCount) : 0;
  const latestUsage = usages[0] || {};

  return (
    /* Forest Stat Card Component from DESIGN.md */
    <div className="bg-[#043f2e] text-[#fcfcfc] rounded-[16px] p-6 border border-[#043f2e]">
      
      {/* Header */}
      <div className="flex items-center justify-between gap-2.5 mb-6 pb-3 border-b border-[#fcfcfc]/15">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-[4px] bg-[#c8f169] text-[#000000]">
            <BarChart2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-lg font-serif text-[#fcfcfc] tracking-[-0.36px]">
              Token & Cost Accounting
            </h3>
            <p className="text-[11px] text-[#fcfcfc]/70">
              Measured live per voice note via Gemini 3.5 Flash UsageMetadata
            </p>
          </div>
        </div>

        <span className="text-[11px] font-mono tracking-wider uppercase px-2.5 py-1 rounded-[4px] bg-[#c8f169] text-[#000000] font-semibold">
          18.4:1 Contrast
        </span>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        
        {/* Notes Processed */}
        <div className="p-4 rounded-[8px] bg-[#fcfcfc]/10 border border-[#fcfcfc]/10">
          <span className="text-[11px] font-mono uppercase tracking-[0.06em] text-[#c8f169] block mb-1">
            Notes Processed
          </span>
          <span className="text-2xl font-serif text-[#fcfcfc]">
            {noteCount.toLocaleString()}
          </span>
        </div>

        {/* Total Tokens */}
        <div className="p-4 rounded-[8px] bg-[#fcfcfc]/10 border border-[#fcfcfc]/10">
          <span className="text-[11px] font-mono uppercase tracking-[0.06em] text-[#c8f169] block mb-1">
            Total Tokens
          </span>
          <span className="text-2xl font-serif text-[#c8f169]">
            {noteCount ? totalTokens.toLocaleString() : '—'}
          </span>
        </div>

        {/* Avg Tokens / Note */}
        <div className="p-4 rounded-[8px] bg-[#fcfcfc]/10 border border-[#fcfcfc]/10">
          <span className="text-[11px] font-mono uppercase tracking-[0.06em] text-[#c8f169] block mb-1">
            Avg Tokens / Note
          </span>
          <span className="text-2xl font-serif text-[#fcfcfc]">
            {noteCount ? avgTokens.toLocaleString() : '—'}
          </span>
        </div>

        {/* Latest Audio Input Tokens */}
        <div className="p-4 rounded-[8px] bg-[#fcfcfc]/10 border border-[#fcfcfc]/10">
          <span className="text-[11px] font-mono uppercase tracking-[0.06em] text-[#c8f169] block mb-1">
            Latest Audio Tokens
          </span>
          <span className="text-2xl font-serif text-[#fcfcfc]">
            {noteCount ? (latestUsage.audio || 0).toLocaleString() : '—'}
          </span>
        </div>

      </div>

      {/* Latest Note Breakdown */}
      {noteCount > 0 && (
        <div className="p-3.5 rounded-[6px] bg-[#000000]/20 border border-[#fcfcfc]/10 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
          <span className="text-[#fcfcfc]/80">Latest Note Token Breakdown:</span>
          <div className="flex items-center gap-5 text-[11px]">
            <span>Audio: <strong className="text-[#c8f169] font-bold">{latestUsage.audio || 0}</strong></span>
            <span>Text: <strong className="text-[#fcfcfc] font-bold">{latestUsage.text || 0}</strong></span>
            <span>Candidate: <strong className="text-[#c8f169] font-bold">{latestUsage.candidate || 0}</strong></span>
          </div>
        </div>
      )}

    </div>
  );
};
