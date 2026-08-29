import React, { useState } from 'react';
import type { Task } from '../types';
import { X, Copy, Check, Globe } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './ArtifactModal.css';

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
      <div className="modal-overlay" role="dialog" aria-modal="true">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="modal-backdrop"
        />

        <motion.div
          initial={{ opacity: 0, scale: 0.97, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.97, y: 8 }}
          transition={{ duration: 0.18, ease: [0.2, 0.6, 0.3, 1] }}
          className="modal-window"
        >
          {/* Header */}
          <div className="modal-header">
            <div className="modal-title-group">
              <h3 className="modal-title">Execution Artifact</h3>
            </div>
            <button onClick={onClose} className="btn-icon" aria-label="Close dialog">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="modal-body">
            <div className="modal-section">
              <span className="modal-section-label">Original Task</span>
              <p className="modal-task-text">{task.task}</p>
            </div>

            <div className="modal-artifact-group">
              <div className="modal-artifact-header">
                <span className="modal-section-label">Output</span>
                <button onClick={handleCopy} className="btn btn-ghost" style={{ fontSize: 'var(--text-xs)' }}>
                  {copied ? (
                    <>
                      <Check size={12} style={{ color: 'var(--lime-deep)' }} />
                      <span style={{ color: 'var(--lime-deep)' }}>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy size={12} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>

              <div className="modal-artifact-content">
                {task.artifact || 'No output generated.'}
              </div>
            </div>

            {/* Grounding Sources */}
            {task.grounded && task.sources && task.sources.length > 0 && (
              <div className="modal-section">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Globe size={13} strokeWidth={1.5} style={{ color: 'var(--moss)' }} />
                  <span className="modal-section-label">Grounding Sources</span>
                </div>
                <div className="modal-sources-list">
                  {task.sources.map((src, i) => (
                    <span key={i} className="modal-source-tag">
                      {src}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="modal-footer">
            <button onClick={onClose} className="btn btn-secondary">
              Close
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
