import React, { useState } from 'react';
import type { Task } from '../types';
import { X, Sparkles, Globe, Copy, Check, Clock, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ArtifactModalProps {
  task: Task | null;
  onClose: () => void;
}

export const ArtifactModal: React.FC<ArtifactModalProps> = ({ task, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!task) return null;

  const handleCopy = () => {
    if (task.artifact) {
      navigator.clipboard.writeText(task.artifact);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
        
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-[#043f2e]/40 backdrop-blur-xs"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          transition={{ duration: 0.2 }}
          className="relative w-full max-w-2xl rounded-[16px] bg-[#fcfcfc] border border-[#043f2e]/20 shadow-none overflow-hidden z-10 my-8"
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-[#043f2e]/10 flex items-center justify-between bg-[#fcfcfc]">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-[4px] bg-[#c8f169] text-[#000000]">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-serif text-lg text-[#043f2e] tracking-[-0.36px]">Execution Output</h3>
                <p className="text-xs text-[#242423]/70 font-mono">Class: {task.class}</p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-[4px] text-[#043f2e]/60 hover:text-[#043f2e] hover:bg-[#eef2e3] transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
            
            {/* Task Prompt */}
            <div className="p-4 rounded-[8px] bg-[#eef2e3] border border-[#043f2e]/10">
              <span className="text-[11px] font-mono text-[#043f2e]/70 uppercase tracking-[0.06em] block mb-1">
                Original Task Item
              </span>
              <p className="text-sm font-medium text-[#043f2e]">{task.task}</p>
            </div>

            {/* Artifact Content */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-[#043f2e] font-semibold uppercase tracking-[0.06em] flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#2a6f2b]" /> Generated Artifact
                </span>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 text-xs font-medium text-[#043f2e] hover:underline transition-colors cursor-pointer"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-[#2a6f2b]" />
                      <span className="text-[#2a6f2b]">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Artifact</span>
                    </>
                  )}
                </button>
              </div>

              <div className="p-4 rounded-[8px] bg-[#eef2e3] border border-[#043f2e]/10 font-sans text-sm text-[#043f2e] leading-relaxed whitespace-pre-wrap selection:bg-[#c8f169]">
                {task.artifact || 'No output generated.'}
              </div>
            </div>

            {/* Grounding & Sources */}
            {task.grounded && task.sources && task.sources.length > 0 && (
              <div className="p-4 rounded-[8px] bg-[#eef2e3] border border-[#043f2e]/10 space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-mono text-[#043f2e]">
                  <Globe className="w-3.5 h-3.5 text-[#2a6f2b]" />
                  <span>Verified Google Search Grounding Sources:</span>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {task.sources.map((src, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-[4px] bg-[#fcfcfc] border border-[#043f2e]/15 text-xs font-mono text-[#043f2e]"
                    >
                      {src}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Telemetry */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              {task.execution_seconds !== undefined && (
                <div className="p-3 rounded-[6px] bg-[#eef2e3] border border-[#043f2e]/10 flex items-center gap-3">
                  <Clock className="w-4 h-4 text-[#043f2e]" />
                  <div>
                    <span className="text-[10px] font-mono text-[#043f2e]/70 block">Execution Latency</span>
                    <span className="text-xs font-mono font-bold text-[#043f2e]">{task.execution_seconds}s</span>
                  </div>
                </div>
              )}

              {task.execution_usage && (
                <div className="p-3 rounded-[6px] bg-[#eef2e3] border border-[#043f2e]/10 flex items-center gap-3">
                  <Cpu className="w-4 h-4 text-[#043f2e]" />
                  <div>
                    <span className="text-[10px] font-mono text-[#043f2e]/70 block">Execution Tokens</span>
                    <span className="text-xs font-mono font-bold text-[#043f2e]">
                      {task.execution_usage.total || 0} tokens
                    </span>
                  </div>
                </div>
              )}
            </div>

          </div>

          {/* Footer */}
          <div className="px-6 py-3 border-t border-[#043f2e]/10 bg-[#fcfcfc] flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-[4px] bg-[#eef2e3] hover:bg-[#e4ebce] text-[#043f2e] text-xs font-medium transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>

        </motion.div>
      </div>
    </AnimatePresence>
  );
};
