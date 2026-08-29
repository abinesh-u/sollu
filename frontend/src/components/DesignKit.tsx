import React from 'react';
import { TrustRung } from './TrustRung';
import { TaskCard } from './TaskCard';
import type { Task } from '../types';
import { Phone, ChevronRight } from 'lucide-react';
import './DesignKit.css';

interface DesignKitProps {
  onBack: () => void;
}

const PALETTE = [
  { name: '--paper', hex: '#EEF2E3', label: 'Pale Sage Canvas' },
  { name: '--card', hex: '#FCFCFC', label: 'Paper White Card' },
  { name: '--ink', hex: '#043F2E', label: 'Deep Forest — Primary Text' },
  { name: '--moss', hex: '#242423', label: 'Charcoal — Secondary Text' },
  { name: '--moss-2', hex: '#5C6B60', label: 'Tertiary / Meta' },
  { name: '--rule', hex: '#DDE4D8', label: 'Hairline Border' },
  { name: '--lime', hex: '#C8F169', label: 'Chartreuse — THE Primary Action' },
  { name: '--lime-deep', hex: '#2A6F2B', label: 'Forest Mid — Hover / Approved' },
  { name: '--sienna', hex: '#7A2E1E', label: 'Brick — Irreversible / Errors' },
  { name: '--sienna-tint', hex: '#F0E2DD', label: 'Brick Tint' },
];

const SAMPLE_PENDING_TASK: Task = {
  id: 'kit-1',
  task: 'Call Ravi regarding the quarterly project budget and confirm timeline',
  lane: 'now',
  class: 'make_call',
  status: 'pending_approval',
  evidence: 'Call Ravi about the invoice and quarterly timeline',
  created_at: Date.now() / 1000,
};

const SAMPLE_IRREVERSIBLE_TASK: Task = {
  id: 'kit-2',
  task: 'Send WhatsApp message to Priya: "Hey Priya, the design review is scheduled for 3pm today."',
  lane: 'now',
  class: 'message_person',
  status: 'pending_approval',
  evidence: 'Send Priya a message on WhatsApp about the design review',
  created_at: Date.now() / 1000,
};

const SAMPLE_AUTO_TASK: Task = {
  id: 'kit-3',
  task: 'Research global pricing index for cloud GPUs and compare provider margins',
  lane: 'next',
  class: 'research',
  status: 'auto_approved',
  execution_status: 'executed',
  artifact: 'AWS H100 instances average $3.85/hr across US regions, while GCP Cloud TPU v5e sits at $1.20/hr per chip with 48% lower total cost of ownership.',
  grounded: true,
  sources: ['aws.amazon.com', 'cloud.google.com', 'semianalysis.com'],
  evidence: 'Look up cloud GPU pricing and compare margins',
  created_at: Date.now() / 1000,
};

export const DesignKit: React.FC<DesignKitProps> = ({ onBack }) => {
  return (
    <div className="design-kit-container">
      <div className="kit-header">
        <div>
          <span className="eyebrow">Component Drift Guard</span>
          <h1 className="kit-section-title" style={{ border: 'none', margin: 0 }}>Design System Showcase (/kit)</h1>
        </div>
        <button onClick={onBack} className="btn btn-secondary">
          ← Return to App
        </button>
      </div>

      {/* Palette Tokens */}
      <section className="kit-section">
        <h2 className="kit-section-title">Design Tokens (Palette)</h2>
        <div className="kit-palette-grid">
          {PALETTE.map((p) => (
            <div key={p.name} className="kit-swatch-card">
              <div className="kit-swatch-color" style={{ backgroundColor: p.hex }} />
              <div className="kit-swatch-info">
                <span className="kit-swatch-name">{p.name}</span>
                <span className="kit-swatch-hex">{p.hex}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Trust Rung Progression */}
      <section className="kit-section">
        <h2 className="kit-section-title">The Trust Rung (Score 0 → 3)</h2>
        <div className="kit-rungs-row">
          <div>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 4 }}>Score 0 (Asks)</span>
            <TrustRung score={0} />
          </div>
          <div>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 4 }}>Score 1</span>
            <TrustRung score={1} />
          </div>
          <div>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 4 }}>Score 2</span>
            <TrustRung score={2} />
          </div>
          <div>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 4 }}>Score 3 (Earned)</span>
            <TrustRung score={3} />
          </div>
        </div>
      </section>

      {/* Button States */}
      <section className="kit-section">
        <h2 className="kit-section-title">Buttons & Interaction States</h2>
        <div className="kit-buttons-grid">
          <button className="btn btn-primary">Primary (Lime Fill)</button>
          <button className="btn btn-secondary">Secondary (Rule Border)</button>
          <button className="btn btn-ghost">
            <span>Ghost with Icon</span>
            <ChevronRight size={14} />
          </button>
          <button className="btn-icon btn-secondary" aria-label="Phone action">
            <Phone size={14} strokeWidth={1.5} />
          </button>
          <button className="btn btn-primary" disabled>Disabled State</button>
        </div>
      </section>

      {/* Card Variants */}
      <section className="kit-section">
        <h2 className="kit-section-title">Card Variants</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 6 }}>1. Pending Variant</span>
            <TaskCard
              task={SAMPLE_PENDING_TASK}
              onApprove={() => {}}
              onReject={async () => {}}
            />
          </div>

          <div>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 6 }}>2. Irreversible Variant (Expanded Payload)</span>
            <TaskCard
              task={SAMPLE_IRREVERSIBLE_TASK}
              onApprove={() => {}}
              onReject={async () => {}}
            />
          </div>

          <div>
            <span className="eyebrow" style={{ display: 'block', marginBottom: 6 }}>3. Auto-Approved Variant (Earned Autonomy + Artifact)</span>
            <TaskCard
              task={SAMPLE_AUTO_TASK}
              onApprove={() => {}}
              onReject={async () => {}}
            />
          </div>
        </div>
      </section>
    </div>
  );
};
