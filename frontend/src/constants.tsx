import React from 'react';
import { Phone, MessageSquare, Search, TrendingUp, FileText } from 'lucide-react';

export const CLASS_ICONS: Record<string, (size?: number) => React.ReactNode> = {
  make_call: (size = 16) => <Phone size={size} strokeWidth={1.5} />,
  message_person: (size = 16) => <MessageSquare size={size} strokeWidth={1.5} />,
  research: (size = 16) => <Search size={size} strokeWidth={1.5} />,
  watch_price: (size = 16) => <TrendingUp size={size} strokeWidth={1.5} />,
  task: (size = 16) => <FileText size={size} strokeWidth={1.5} />,
  other: (size = 16) => <FileText size={size} strokeWidth={1.5} />,
};

export const getClassIcon = (taskClass: string, size = 16) => {
  const renderFn = CLASS_ICONS[taskClass] || CLASS_ICONS['other'];
  return renderFn(size);
};

export const CLASS_LABELS: Record<string, string> = {
  make_call: 'Make Call',
  message_person: 'Message Person',
  research: 'Grounded Research',
  watch_price: 'Watch Condition',
  task: 'General Task',
  other: 'General Task',
};

export const CLASS_DESCRIPTIONS: Record<string, string> = {
  make_call: 'Script generated but no call placed.',
  message_person: 'Draft written but not sent.',
  research: 'Web search executed and summarized.',
  watch_price: 'Condition registered for deferred evaluation.',
  task: 'No executor — approval is recorded only.',
  other: 'No executor — approval is recorded only.',
};

export const CLASS_OUTPUT_LABELS: Record<string, string> = {
  make_call: 'Call script',
  message_person: 'Message draft',
  research: 'Research synthesis',
  watch_price: 'Condition recorded',
  task: 'Execution result',
  other: 'Execution result',
};
