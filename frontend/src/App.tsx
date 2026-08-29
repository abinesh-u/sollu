import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { AudioInputBar } from './components/AudioInputBar';
import { LanesBoard } from './components/LanesBoard';
import { TrustLadderMatrix } from './components/TrustLadderMatrix';
import { CostStats } from './components/CostStats';
import { ArtifactModal } from './components/ArtifactModal';
import type { Task, ClassInfo } from './types';
import { fetchTasks, fetchClasses, processAudio, speakSummary, approveTask, rejectTask } from './services/api';

export const App: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedArtifactTask, setSelectedArtifactTask] = useState<Task | null>(null);
  
  // Voice confirmation TTS state
  const [speakOn, setSpeakOn] = useState<boolean>(() => {
    try {
      return localStorage.getItem('sollu.speak') === 'on';
    } catch {
      return false;
    }
  });

  const toggleSpeak = () => {
    setSpeakOn((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('sollu.speak', next ? 'on' : 'off');
      } catch {}
      return next;
    });
  };

  // Data fetching
  const refreshData = useCallback(async () => {
    try {
      const [tasksData, classesData] = await Promise.all([
        fetchTasks().catch(() => []),
        fetchClasses().catch(() => []),
      ]);
      setTasks(tasksData);
      setClasses(classesData);
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  }, []);

  // Initial load and 5s polling
  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 5000);
    return () => clearInterval(interval);
  }, [refreshData]);

  // Audio processing handler
  const handleProcessAudio = async (audioBlob: Blob, filename: string, imageFile?: File | null) => {
    setIsProcessing(true);
    try {
      const res = await processAudio(audioBlob, filename, imageFile);
      if (res.tasks) {
        setTasks(res.tasks);
        await refreshData();
      }

      // Voice confirmation playback if enabled
      if (speakOn && res.summary) {
        const audioData = await speakSummary(res.summary);
        if (audioData) {
          const audioUrl = URL.createObjectURL(audioData);
          const audioEl = new Audio(audioUrl);
          audioEl.onended = () => URL.revokeObjectURL(audioUrl);
          await audioEl.play().catch(() => {});
        }
      }
    } catch (err) {
      console.error('Failed to process voice note:', err);
      alert(`Processing error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsProcessing(false);
      refreshData();
    }
  };

  // Task approval handler
  const handleApprove = async (taskId: string) => {
    try {
      await approveTask(taskId);
      await refreshData();
    } catch (err) {
      console.error('Approval failed:', err);
    }
  };

  // Task rejection handler
  const handleReject = async (taskId: string) => {
    try {
      await rejectTask(taskId);
      await refreshData();
    } catch (err) {
      console.error('Rejection failed:', err);
    }
  };

  const handleOpenLadderModal = () => {
    const el = document.getElementById('trust-ladder-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-[100dvh] flex flex-col bg-[#eef2e3] text-[#043f2e] selection:bg-[#c8f169] selection:text-[#000000]">
      
      {/* Header */}
      <Header
        speakOn={speakOn}
        onToggleSpeak={toggleSpeak}
        onOpenLadderModal={handleOpenLadderModal}
        taskCount={tasks.length}
      />

      {/* Main Container - 1200px max-width per DESIGN.md */}
      <main className="flex-1 max-w-[1200px] w-full mx-auto px-4 sm:px-6 py-8 space-y-8">
        
        {/* Top: Audio Input & Errand Recorder */}
        <section>
          <AudioInputBar
            onProcessAudio={handleProcessAudio}
            isProcessing={isProcessing}
          />
        </section>

        {/* Middle: 3-Lane Kanban (Now, Next, Later) */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[11px] font-mono tracking-[0.06em] uppercase text-[#043f2e]/70 block">
                Triaged Workflow
              </span>
              <h2 className="text-2xl font-serif text-[#043f2e] tracking-[-0.72px]">
                Execution Lanes
              </h2>
            </div>
            <span className="text-xs font-mono text-[#043f2e]/60">
              Live updates every 5s
            </span>
          </div>
          <LanesBoard
            tasks={tasks}
            onApprove={handleApprove}
            onReject={handleReject}
            onViewArtifact={(task) => setSelectedArtifactTask(task)}
          />
        </section>

        {/* Trust Ladder */}
        <section id="trust-ladder-section" className="space-y-6 pt-2">
          <TrustLadderMatrix classes={classes} />
        </section>

        {/* Dashboard Stats */}
        <section className="space-y-6 pt-8 pb-8 border-t border-[#043f2e]/10">
          <CostStats tasks={tasks} />
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-[#043f2e]/10 bg-[#fcfcfc] py-6 mt-12">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 text-center text-xs text-[#242423]/70 space-y-1">
          <p className="font-serif text-sm text-[#043f2e]">Sollu &middot; Sunlit Greenhouse Editorial</p>
          <p className="font-mono text-[11px] text-[#242423]/60">
            Primary: Gemini 3.5 Flash &middot; Spoken Confirmation: Gemini 2.5 Flash TTS &middot; Firestore Native
          </p>
        </div>
      </footer>

      {/* Artifact Modal */}
      <ArtifactModal
        task={selectedArtifactTask}
        onClose={() => setSelectedArtifactTask(null)}
      />

    </div>
  );
};

export default App;
