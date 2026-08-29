import React from 'react';
import type { ClassInfo } from '../types';
import { CLASS_ICONS, CLASS_LABELS } from '../constants';
import { ShieldCheck, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

interface TrustLadderMatrixProps {
  classes: ClassInfo[];
}

export const TrustLadderMatrix: React.FC<TrustLadderMatrixProps> = ({ classes }) => {
  const THRESHOLD = 3;

  return (
    <div className="bg-[#fcfcfc] rounded-[16px] p-6 border border-[#043f2e]/10 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#043f2e]/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-[4px] bg-[#eef2e3] border border-[#043f2e]/15 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-[#043f2e]" />
          </div>
          <div>
            <h3 className="text-xl font-sans font-semibold text-[#043f2e] tracking-tight">
              Trust Ladder Autonomy Matrix
            </h3>
            <p className="text-xs text-[#242423]">
              Every class starts by asking permission. After <strong className="text-[#043f2e]">3 approvals</strong>, it earns autonomous auto-execution. 1 rejection resets to 0.
            </p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-[#242423]">
            <span className="w-2 h-2 rounded-full bg-[#043f2e]/30" />
            <span>&lt;3: Ask Permission</span>
          </div>
          <div className="flex items-center gap-1.5 text-[#043f2e] font-semibold">
            <span className="w-2 h-2 rounded-full bg-[#c8f169] border border-[#043f2e]/20" />
            <span>3+: Auto-Execute</span>
          </div>
        </div>
      </div>

      {/* Grid of Classes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-[#043f2e]/10 rounded-[12px] overflow-hidden border border-[#043f2e]/10">
        {classes.map((cls) => {
          const approvals = cls.approvals || 0;
          const isAuto = approvals >= THRESHOLD;

          return (
            <div
              key={cls.class}
              className={`p-5 bg-[#fcfcfc] transition-all hover:bg-white`}
            >
              {/* Class Header */}
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-[4px] bg-white border border-[#043f2e]/10 shrink-0">
                    {CLASS_ICONS[cls.class] || CLASS_ICONS['other']}
                  </div>
                  <span className="text-xs font-mono font-semibold text-[#043f2e] truncate">
                    {CLASS_LABELS[cls.class] || cls.class}
                  </span>
                </div>

                {isAuto ? (
                  <span className="flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-[4px] bg-[#c8f169] text-[#000000] shrink-0 uppercase">
                    <Sparkles className="w-2.5 h-2.5 text-[#000000]" />
                    <span>AUTO-APPROVES</span>
                  </span>
                ) : (
                  <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-[4px] bg-white text-[#043f2e]/70 border border-[#043f2e]/15 shrink-0 uppercase tracking-wide">
                    ASKS FIRST
                  </span>
                )}
              </div>

              {/* Description */}
              <p className="text-[11px] text-[#242423] line-clamp-2 mb-4 min-h-[32px]">
                {cls.label || cls.description}
              </p>

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-[#242423]/70">Approvals:</span>
                  <span className={isAuto ? 'text-[#043f2e] font-bold' : 'text-[#043f2e]'}>
                    {approvals} / {THRESHOLD}
                  </span>
                </div>

                <div className="flex gap-1 h-1.5 w-full">
                  {[...Array(THRESHOLD)].map((_, i) => {
                    const isActive = i < approvals;
                    return (
                      <motion.div
                        key={i}
                        className={`flex-1 rounded-full ${
                          isActive ? 'bg-[#c8f169]' : 'bg-[#043f2e]/10'
                        }`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                      />
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
};
