import React from 'react';
import { PhoneCall, MessageSquare, Search, TrendingUp, FileText } from 'lucide-react';

export const CLASS_ICONS: Record<string, React.ReactNode> = {
  make_call: <PhoneCall className="w-3.5 h-3.5 text-[#043f2e]" />,
  message_person: <MessageSquare className="w-3.5 h-3.5 text-[#043f2e]" />,
  research: <Search className="w-3.5 h-3.5 text-[#043f2e]" />,
  watch_price: <TrendingUp className="w-3.5 h-3.5 text-[#043f2e]" />,
  other: <FileText className="w-3.5 h-3.5 text-[#043f2e]" />,
};

export const CLASS_LABELS: Record<string, string> = {
  make_call: 'Make Call',
  message_person: 'Message Person',
  research: 'Grounded Research',
  watch_price: 'Watch Condition',
  other: 'General Task',
};
