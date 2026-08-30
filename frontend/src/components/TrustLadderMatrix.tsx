import React from 'react';
import type { ClassInfo } from '../types';
import { getClassIcon } from '../constants';
import { TrustRung } from './TrustRung';
import { ShieldCheck, CheckCheck } from 'lucide-react';
import './TrustLadderMatrix.css';

interface TrustLadderMatrixProps {
  classes: ClassInfo[];
}

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
            <span>Asks first</span>
          </span>
          <span className="legend-item legend-item-strong">
            <span className="legend-dot dot-lime" />
            <span>Runs on its own</span>
          </span>
        </div>
      </div>

      <div className="ladder-carousel-wrapper">
        <div className="ladder-carousel">
          {classes.map((cls) => {
            const approvals = cls.approvals || 0;
            const threshold = cls.threshold !== undefined ? cls.threshold : 3;
            const isAuto = cls.auto;
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
                    {threshold === 'never' ? (
                       <span style={{ opacity: 0.6 }}>Always asks</span>
                    ) : threshold === 0 ? (
                       <span className="is-max">Instant Auto</span>
                    ) : (
                       <span className={isAuto ? 'is-max' : ''}>{approvals} / {threshold}</span>
                    )}
                  </div>
                  {threshold === 'never' ? (
                     <TrustRung score={0} max={3} />
                  ) : threshold === 0 ? (
                     <TrustRung score={3} max={3} />
                  ) : (
                     <TrustRung score={approvals} max={threshold as number} />
                  )}
                  
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
