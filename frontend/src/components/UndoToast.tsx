import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw } from 'lucide-react';
import './UndoToast.css';

export interface PendingCommit {
  id: string;
  taskId: string;
  taskTitle: string;
  actionVerb: string;
  createdAt: number;
}

interface UndoToastItemProps {
  commit: PendingCommit;
  onCommit: (id: string, taskId: string) => void;
  onUndo: (id: string, taskId: string) => void;
}

const UndoToastItem: React.FC<UndoToastItemProps> = ({ commit, onCommit, onUndo }) => {
  const TOTAL_MS = 7000;
  const [remainingMs, setRemainingMs] = useState(TOTAL_MS);
  const [isPaused, setIsPaused] = useState(false);
  const lastTickRef = useRef<number>(0);

  useEffect(() => {
    lastTickRef.current = Date.now();
    const interval = setInterval(() => {
      if (isPaused) {
        lastTickRef.current = Date.now();
        return;
      }
      const now = Date.now();
      const delta = now - lastTickRef.current;
      lastTickRef.current = now;

      setRemainingMs((prev) => {
        const next = prev - delta;
        if (next <= 0) {
          clearInterval(interval);
          onCommit(commit.id, commit.taskId);
          return 0;
        }
        return next;
      });
    }, 50);

    return () => clearInterval(interval);
  }, [commit.id, commit.taskId, isPaused, onCommit]);

  const progressPercent = Math.max(0, (remainingMs / TOTAL_MS) * 100);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.94 }}
      transition={{ duration: 0.18, ease: [0.2, 0.6, 0.3, 1] }}
      className="undo-toast"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="undo-toast-inner">
        <div className="undo-toast-message">
          <span>{commit.actionVerb}</span>
        </div>
        <div className="undo-toast-action">
          <button
            onClick={() => onUndo(commit.id, commit.taskId)}
            className="undo-btn"
            aria-label="Undo action"
          >
            <RotateCcw size={13} strokeWidth={2} />
            <span>Undo</span>
          </button>
          <span className="undo-key-chip">U</span>
        </div>
      </div>
      <div className="undo-drain-track">
        <div
          className="undo-drain-bar"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </motion.div>
  );
};

interface UndoToastContainerProps {
  commits: PendingCommit[];
  onCommit: (id: string, taskId: string) => void;
  onUndo: (id: string, taskId: string) => void;
}

export const UndoToastContainer: React.FC<UndoToastContainerProps> = ({
  commits,
  onCommit,
  onUndo,
}) => {
  // Global 'U' key listener to undo the most recent pending commit
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInput =
        activeEl?.tagName === 'INPUT' ||
        activeEl?.tagName === 'TEXTAREA' ||
        activeEl?.getAttribute('contenteditable') === 'true';

      if (isInput) return;

      if ((e.key === 'u' || e.key === 'U') && commits.length > 0) {
        e.preventDefault();
        const top = commits[commits.length - 1];
        onUndo(top.id, top.taskId);
      }
    },
    [commits, onUndo]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="undo-toasts-container" aria-live="polite">
      <AnimatePresence>
        {commits.map((commit) => (
          <UndoToastItem
            key={commit.id}
            commit={commit}
            onCommit={onCommit}
            onUndo={onUndo}
          />
        ))}
      </AnimatePresence>
    </div>
  );
};
