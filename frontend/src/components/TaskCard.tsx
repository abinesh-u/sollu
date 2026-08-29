import React, { useState } from 'react';
import type { Task } from '../types';
import { 
  Check, 
  X, 
  Sparkles, 
  Clock, 
  Loader2, 
  FileText, 
  PhoneCall, 
  MessageSquare, 
  Search, 
  TrendingUp, 
  Globe, 
  ExternalLink,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { motion } from 'framer-motion';

interface TaskCardProps {
  task: Task;
  onApprove: (taskId: string) => Promise<void>;
  onReject: (taskId: string) => Promise<void>;
  onViewArtifact: (task: Task) => void;
}

const CLASS_ICONS: Record<string, React.ReactNode> = {
  make_call: <PhoneCall className="w-3.5 h-3.5 text-[#043f2e]" />,
  message_person: <MessageSquare className="w-3.5 h-3.5 text-[#043f2e]" />,
  research: <Search className="w-3.5 h-3.5 text-[#043f2e]" />,
  watch_price: <TrendingUp className="w-3.5 h-3.5 text-[#043f2e]" />,
};

const CLASS_LABELS: Record<string, string> = {
  make_call: 'Make Call',
  message_person: 'Message Person',
  research: 'Grounded Research',
  watch_price: 'Watch Condition',
  other: 'General Task',
};

export const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onApprove,
  onReject,
  onViewArtifact,
}) => {
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleApprove = async () => {
    setIsApproving(true);
    try {
      await onApprove(task.id);
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    setIsRejecting(true);
    try {
      await onReject(task.id);
    } finally {
      setIsRejecting(false);
    }
  };

  const isAutoApproved = task.status === 'auto_approved';
  const isPending = task.status === 'pending_approval';
  const isApproved = task.status === 'approved';
  const isRejected = task.status === 'rejected';
  const isExecuting = task.execution_status === 'executing';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.2 }}
      className={`rounded-[16px] p-5 transition-all relative overflow-hidden shadow-[0_2px_10px_rgba(4,63,46,0.04)] border border-[#043f2e]/5 ${
        isRejected
          ? 'bg-[#f0e2dd]'
          : isAutoApproved
          ? 'bg-[#eef2e3]'
          : 'bg-[#fcfcfc]'
      }`}
    >
      {/* Top: Metadata & Status Badges */}
      <div className="flex items-center justify-between gap-2 mb-2.5">
        
        {/* Class Badge */}
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-[4px] bg-[#eef2e3] text-xs font-mono text-[#043f2e] border border-[#043f2e]/10">
          {CLASS_ICONS[task.class] || <FileText className="w-3.5 h-3.5 text-[#043f2e]" />}
          <span>{CLASS_LABELS[task.class] || task.class}</span>
        </div>

        {/* Autonomy Badge */}
        <div>
          {isAutoApproved && (
            <span className="flex items-center gap-1 text-[11px] font-mono font-medium px-2 py-0.5 rounded-[4px] bg-[#c8f169] text-[#000000]">
              <Sparkles className="w-3 h-3 text-[#000000]" />
              <span>Auto-Approved</span>
            </span>
          )}
          {isPending && (
            <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-[4px] bg-[#eef2e3] text-[#242423]">
              <Clock className="w-3 h-3 text-[#242423]" />
              <span>PENDING APPROVAL</span>
            </span>
          )}
          {isApproved && (
            <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-[4px] bg-[#eef2e3] text-[#2a6f2b] border border-[#2a6f2b]/30 font-medium">
              <Check className="w-3 h-3 text-[#2a6f2b]" />
              <span>Approved</span>
            </span>
          )}
          {isRejected && (
            <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-[4px] bg-[#7a2e1e] text-[#fcfcfc] font-medium">
              <X className="w-3 h-3 text-[#fcfcfc]" />
              <span>Rejected</span>
            </span>
          )}
        </div>
      </div>

      {/* Task Text */}
      <h3 className={`text-sm font-sans font-medium leading-relaxed mb-3 ${
        isRejected ? 'line-through text-[#7a2e1e]' : 'text-[#043f2e]'
      }`}>
        {task.task}
      </h3>

      {/* Deferred Condition Info */}
      {task.lane === 'later' && task.condition && (
        <div className="mb-3 p-2.5 rounded-[4px] bg-[#eef2e3] border border-[#043f2e]/10 text-xs font-mono text-[#043f2e] space-y-1">
          <div className="flex items-center gap-1.5 text-[#043f2e] font-semibold">
            <Clock className="w-3.5 h-3.5" />
            <span>Wake Condition:</span>
          </div>
          <p className="text-[#242423] pl-5 text-[11px]">{task.condition}</p>
        </div>
      )}

      {/* Execution in Progress Spinner */}
      {isExecuting && (
        <div className="mb-3 p-2.5 rounded-[4px] bg-[#c8f169]/30 border border-[#c8f169] flex items-center justify-between text-xs text-[#043f2e] font-mono">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-[#043f2e]" />
            <span>Executing grounded research...</span>
          </div>
          <span className="text-[10px] font-semibold uppercase">Autonomous</span>
        </div>
      )}

      {/* Artifact Preview Card */}
      {task.artifact && (
        <div className="mb-3 rounded-[8px] bg-[#eef2e3] border border-[#043f2e]/10 overflow-hidden">
          <div className="px-3 py-1.5 border-b border-[#043f2e]/10 flex items-center justify-between bg-[#eef2e3]">
            <div className="flex items-center gap-1.5 text-xs font-mono text-[#043f2e] font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-[#2a6f2b]" />
              <span>Execution Output</span>
            </div>
            <button
              onClick={() => onViewArtifact(task)}
              className="text-[11px] text-[#043f2e]/80 hover:text-[#043f2e] font-medium flex items-center gap-1 cursor-pointer font-sans"
            >
              <span>Expand</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          </div>

          <div className="p-3 text-xs text-[#242423] font-sans leading-relaxed">
            <p className={isExpanded ? '' : 'line-clamp-3'}>
              {task.artifact}
            </p>
            {task.artifact.length > 180 && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="mt-1 text-[11px] text-[#2a6f2b] font-medium hover:underline flex items-center gap-1 cursor-pointer"
              >
                {isExpanded ? (
                  <>Show less <ChevronUp className="w-3 h-3" /></>
                ) : (
                  <>Show more <ChevronDown className="w-3 h-3" /></>
                )}
              </button>
            )}
          </div>

          {/* Sources and Grounding Tags */}
          {task.grounded && task.sources && task.sources.length > 0 && (
            <div className="px-3 py-2 border-t border-[#043f2e]/10 bg-[#eef2e3]/60 flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] font-mono text-[#043f2e]/70 uppercase tracking-wider flex items-center gap-1">
                <Globe className="w-2.5 h-2.5" /> Sources:
              </span>
              {task.sources.slice(0, 3).map((s, idx) => (
                <span
                  key={idx}
                  className="text-[10px] font-mono px-1.5 py-0.5 rounded-[2px] bg-[#fcfcfc] border border-[#043f2e]/15 text-[#043f2e]"
                >
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Execution Error Display */}
      {task.execution_error && (
        <div className="mb-3 p-2.5 rounded-[4px] bg-[#f0e2dd] border border-[#7a2e1e]/30 text-xs text-[#7a2e1e] font-mono">
          <p className="font-semibold">Execution Issue:</p>
          <p className="text-[11px] truncate">{task.execution_error}</p>
        </div>
      )}

      {/* Action Buttons */}
      {!isRejected && (
        <div className="flex items-center gap-2 pt-1">
          
          {/* Approve Button (when pending) */}
          {isPending && (
            <button
              onClick={handleApprove}
              disabled={isApproving || isRejecting}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-[4px] bg-[#c8f169] hover:bg-[#bde85b] text-[#000000] text-xs font-medium transition-all active:translate-y-[1px] disabled:opacity-50 cursor-pointer"
            >
              {isApproving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Check className="w-3.5 h-3.5 stroke-[2.5]" />
              )}
              <span>{isApproving ? 'Executing...' : 'Approve & Run'}</span>
            </button>
          )}

          {/* Reject / Demote Button */}
          {(isPending || isAutoApproved) && (
            <button
              onClick={handleReject}
              disabled={isApproving || isRejecting}
              className={`flex items-center justify-center gap-1 py-2 px-3 rounded-[4px] border text-xs font-medium transition-all active:translate-y-[1px] disabled:opacity-50 cursor-pointer ${
                isAutoApproved
                  ? 'flex-1 bg-[#f0e2dd] hover:bg-[#ebd3cb] border-[#7a2e1e]/40 text-[#7a2e1e]'
                  : 'bg-transparent hover:bg-[#eef2e3] border-[#043f2e]/25 text-[#043f2e]'
              }`}
              title={isAutoApproved ? 'Reject and reset class back to 0 approvals' : 'Reject task'}
            >
              {isRejecting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <X className="w-3.5 h-3.5" />
              )}
              <span>{isAutoApproved ? 'Reject & Demote' : 'Reject'}</span>
            </button>
          )}

        </div>
      )}
    </motion.div>
  );
};
