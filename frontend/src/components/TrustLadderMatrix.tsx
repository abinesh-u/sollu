import React from 'react';
import type { ClassInfo } from '../types';
import { getClassIcon } from '../constants';
import { TrustRung } from './TrustRung';
import { ShieldCheck, CheckCheck } from 'lucide-react';
import './TrustLadderMatrix.css';

interface TrustLadderMatrixProps {
  classes: ClassInfo[];
}

const THRESHOLD = 3;

export const TrustLadderMatrix: React.FC<TrustLadderMatrixProps> = ({ classes }) => {
  return (
    <div className="trust-ladder-container">
      <div className="ladder-header">
        <div className="ladder-header-left">
          <div className="ladder-icon-chip">
            <ShieldCheck size={18} />
          </div>
          <div>
            <h3 className="ladder-heading">Trust Ladder</h3>
          </div>
        </div>

        <div className="ladder-legend">
          <span className="legend-item">
            <span className="legend-dot dot-muted" />
            <span>Under 3 approvals: asks first</span>
          </span>
          <span className="legend-item legend-item-strong">
            <span className="legend-dot dot-lime" />
            <span>3+ approvals: runs on its own</span>
          </span>
        </div>
      </div>

      <div className="ladder-carousel-wrapper">
        <div className="ladder-carousel">
          {classes.map((cls) => {
            const approvals = cls.approvals || 0;
            const isAuto = approvals >= THRESHOLD;
            const label = cls.ui_label || cls.label || cls.class;

            return (
              <div key={cls.class} className="ladder-card">
                <div className="ladder-card-header">
                  <div className="ladder-card-icon">{getClassIcon(cls.class, classes, 16)}</div>
                  <span className="ladder-card-name">{label}</span>
                </div>

                <p className="ladder-card-desc">{cls.ui_description || cls.description}</p>

                <div className="ladder-card-footer">
                  <div className="ladder-progress-row">
                    <span>Approvals:</span>
                    <span className={isAuto ? 'is-max' : ''}>{approvals} / {THRESHOLD}</span>
                  </div>
                  <TrustRung score={approvals} max={THRESHOLD} />
                  
                  <div className="ladder-status-row">
                    {isAuto ? (
                      <span className="ladder-status-badge badge-auto">
                        <CheckCheck size={11} strokeWidth={2} />
                        <span>Auto-executes</span>
                      </span>
                    ) : (
                      <span className="ladder-status-badge badge-asking">Asks First</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
