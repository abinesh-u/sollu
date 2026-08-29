import React from 'react';
import { X } from 'lucide-react';
import './KeyboardShortcutsModal.css';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SHORTCUTS = [
  { key: 'J / K', desc: 'Move focus down / up across the board' },
  { key: 'A', desc: 'Approve focused card' },
  { key: 'R', desc: 'Reject focused card' },
  { key: 'U', desc: 'Undo last commit' },
  { key: 'Space', desc: 'Hold to record voice note' },
  { key: '?', desc: 'Toggle keyboard shortcut overlay' },
  { key: 'Esc', desc: 'Dismiss overlay' },
];

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  return (
    <div className="shortcuts-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="shortcuts-card" onClick={(e) => e.stopPropagation()}>
        <div className="shortcuts-header">
          <h3 className="shortcuts-title">Keyboard Shortcuts</h3>
          <button onClick={onClose} className="btn-icon" aria-label="Close shortcuts">
            <X size={16} />
          </button>
        </div>

        <div className="shortcuts-table">
          {SHORTCUTS.map((s) => (
            <div key={s.key} className="shortcut-row">
              <span className="shortcut-desc">{s.desc}</span>
              <kbd className="shortcut-key">{s.key}</kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
