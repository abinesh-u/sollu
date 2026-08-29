import React from 'react';
import { Volume2, VolumeX, ShieldCheck } from 'lucide-react';

interface HeaderProps {
  speakOn: boolean;
  onToggleSpeak: () => void;
  onOpenLadderModal: () => void;
  taskCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  speakOn,
  onToggleSpeak,
  onOpenLadderModal,
  taskCount,
}) => {
  return (
    <header className="border-b border-[#043f2e]/10 bg-[#fcfcfc] sticky top-0 z-40">
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        
        {/* Left: Branding & Model Split */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-[4px] bg-[#c8f169] flex items-center justify-center text-[#000000] font-serif font-bold text-lg">
            S
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <span className="font-serif text-2xl tracking-[-0.72px] text-[#043f2e]">Sollu</span>
              <span className="text-[11px] font-mono tracking-wider uppercase px-2 py-0.5 rounded-[4px] bg-[#eef2e3] text-[#043f2e] font-medium border border-[#043f2e]/10">
                Gemini 3.5 Flash
              </span>
            </div>
          </div>
        </div>

        {/* Right: Controls & Actions */}
        <div className="flex items-center gap-2.5">
          
          {/* Active Tasks Pill */}
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-[4px] bg-[#eef2e3] text-xs font-mono text-[#043f2e]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#2a6f2b]" />
            <span>{taskCount} Active {taskCount === 1 ? 'Task' : 'Tasks'}</span>
          </div>

          {/* Trust Ladder Button */}
          <button
            onClick={onOpenLadderModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] border border-[#043f2e]/30 bg-[#fcfcfc] hover:bg-[#eef2e3] text-xs font-medium text-[#043f2e] transition-all cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4 text-[#043f2e]" />
            <span className="hidden sm:inline">Trust Ladder</span>
          </button>

          {/* Voice Confirmation Button */}
          <button
            onClick={onToggleSpeak}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] text-xs font-medium transition-all cursor-pointer border ${
              speakOn
                ? 'bg-[#043f2e] text-[#fcfcfc] border-[#043f2e] hover:bg-[#065b43]'
                : 'bg-transparent border-[#043f2e]/30 text-[#043f2e] hover:bg-[#eef2e3]'
            }`}
            title="Toggle Gemini 2.5 Flash TTS confirmation"
          >
            {speakOn ? (
              <>
                <Volume2 className="w-4 h-4 text-[#fcfcfc]" />
                <span className="hidden sm:inline">Voice Confirmation On</span>
              </>
            ) : (
              <>
                <VolumeX className="w-4 h-4 text-[#043f2e]/60" />
                <span className="hidden sm:inline">Voice Muted</span>
              </>
            )}
          </button>

        </div>
      </div>
    </header>
  );
};
