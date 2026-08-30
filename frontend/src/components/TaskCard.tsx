import React, { useState } from 'react';
import type { Task, ClassInfo } from '../types';
import { getClassIcon } from '../constants';
import { Check, CheckCheck, X, Sparkles, Clock, Loader2, Globe, ExternalLink, ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';
import './TaskCard.css';

interface TaskCardProps {
  task: Task;
  classes: ClassInfo[];
  isFocused?: boolean;
  onApprove: (task: Task, actionVerb: string) => void;
  onReject: (taskId: string) => Promise<void>;
  onDelete?: (taskId: string) => Promise<void>;
  onViewArtifact?: (task: Task) => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({
  task,
  classes,
  isFocused = false,
  onApprove,
  onReject,
  onDelete,
  onViewArtifact,
}) => {
  const isAutoApproved = task.status === 'auto_approved';
  const isPending = task.status === 'pending_approval';
  const isApproved = task.status === 'approved';
  const isRejected = task.status === 'rejected';
  const isExecuting = task.execution_status === 'executing';

  const [isExpanded, setIsExpanded] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  
  const cls = classes.find(c => c.class === task.class);
  const uiLabel = cls?.ui_label || task.class;
  const uiOutputLabel = cls?.ui_output_label || 'Execution result';

  const handleApprove = () => {
    setIsApproving(true);
    onApprove(task, 'Authorizing task...');
  };

  const handleReject = async () => {
    setIsRejecting(true);
    try {
      await onReject(task.id);
    } finally {
      setIsRejecting(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.2 }}
      className={`task-card ${isRejected ? 'variant-rejected' : isAutoApproved ? 'variant-auto' : 'variant-pending'} ${isFocused ? 'is-focused' : ''}`}
      data-task-id={task.id}
    >
      {/* Top: class chip + status badge */}
      <div className="task-card-header">
        <div className="task-class-chip">
          {getClassIcon(task.class, classes, 14)}
          <span>{uiLabel}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {onDelete && (
            <button 
              onClick={(e) => { e.stopPropagation(); onDelete(task.id); }}
              className="task-delete-btn"
              title="Delete task"
            >
              <Trash2 size={14} />
            </button>
          )}
          {isAutoApproved && (
            <span className="status-badge badge-auto">
              <CheckCheck size={12} strokeWidth={2} />
              <span>Auto-executed</span>
            </span>
          )}
          {isPending && (
            <span className="status-badge badge-pending">
              <Clock size={11} strokeWidth={1.5} />
              <span>Pending Approval</span>
            </span>
          )}
          {isApproved && (
            <span className="status-badge badge-approved">
              <Check size={11} strokeWidth={2} />
              <span>Approved</span>
            </span>
          )}
          {isRejected && (
            <span className="status-badge badge-rejected">
              <X size={11} strokeWidth={2} />
              <span>Rejected (class demoted)</span>
            </span>
          )}
        </div>
      </div>

      {/* Title */}
      <h3 className={`task-title ${isRejected ? 'text-strike' : ''}`}>
        {task.task}
      </h3>

      {/* Deferred wake condition */}
      {task.lane === 'later' && task.condition && (
        <div className="task-condition-block">
          <div className="task-condition-label">
            <Clock size={14} />
            <span>Wake Condition:</span>
          </div>
          <p className="task-condition-text">Waiting until {task.condition}.</p>
        </div>
      )}

      {/* Executing indicator */}
      {isExecuting && (
        <div className="task-executing-block">
          <div className="task-executing-status">
            <Loader2 size={14} className="animate-spin" />
            <span>Executing grounded research...</span>
          </div>
          <span className="task-executing-tag">Autonomous</span>
        </div>
      )}

      {/* Artifact / execution output */}
      {task.artifact && (
        <div className="task-payload">
          <div className="task-payload-header">
            <div className="task-payload-heading">
              <Sparkles size={13} />
              <span>{uiOutputLabel}</span>
            </div>
            {onViewArtifact && (
              <button type="button" onClick={() => onViewArtifact(task)} className="task-payload-expand">
                <span>Expand</span>
                <ExternalLink size={11} />
              </button>
            )}
          </div>

          <div className="task-payload-body">
            <p className={!isExpanded ? 'line-clamp-3' : ''}>{task.artifact}</p>
            {task.artifact.length > 180 && (
              <button type="button" onClick={() => setIsExpanded(!isExpanded)} className="task-payload-toggle">
                {isExpanded ? (
                  <>Show less <ChevronUp size={12} /></>
                ) : (
                  <>Show more <ChevronDown size={12} /></>
                )}
              </button>
            )}
          </div>

          {task.grounded && task.sources && task.sources.length > 0 && (
            <div className="task-sources">
              <span className="task-sources-label">
                <Globe size={11} /> Sources:
              </span>
              {task.sources.slice(0, 3).map((s, idx) => (
                <span key={idx} className="task-source-chip">{s}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Execution error */}
      {task.execution_error && (
        <div className="task-error-block">
          <p className="task-error-title">Execution Issue:</p>
          <p className="task-error-text">{task.execution_error}</p>
        </div>
      )}

      {/* Actions */}
      {!isRejected && (
        <div className="task-actions">
          {isPending && (
            <button
              onClick={handleApprove}
              disabled={isApproving || isRejecting}
              className="btn btn-primary task-approve-btn"
            >
              {isApproving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} strokeWidth={2.5} />}
              <span>{isApproving ? 'Executing...' : 'Approve & Run'}</span>
            </button>
          )}

          {(isPending || isAutoApproved) && (
            <button
              onClick={handleReject}
              disabled={isApproving || isRejecting}
              className={`btn task-reject-btn ${isAutoApproved ? 'reject-demote' : 'btn-secondary'}`}
              title={isAutoApproved ? 'Reject and reset class back to 0 approvals' : 'Reject task'}
            >
              {isRejecting ? <Loader2 size={14} className="animate-spin" /> : <X size={14} />}
              <span>{isAutoApproved ? 'Reject & Demote' : 'Reject'}</span>
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
};
