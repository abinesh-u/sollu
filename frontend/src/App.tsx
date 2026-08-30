import React, { useState, useEffect, useCallback } from 'react';
import type { Task, ClassInfo } from './types';
import { fetchTasks, fetchClasses, processAudio, speakSummary, approveTask, rejectTask } from './services/api';
import { AudioInputBar } from './components/AudioInputBar';
import { Board } from './components/Board';
import { TrustLadderMatrix } from './components/TrustLadderMatrix';
import { UndoToastContainer, type PendingCommit } from './components/UndoToast';
import { ArtifactModal } from './components/ArtifactModal';
import './App.css';

export const App: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedArtifactTask, setSelectedArtifactTask] = useState<Task | null>(null);

  const [pendingCommits, setPendingCommits] = useState<PendingCommit[]>([]);

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

  const refreshData = useCallback(async () => {
    try {
      const [tasksData, classesData] = await Promise.all([
        fetchTasks().catch(() => []),
        fetchClasses().catch(() => []),
      ]);
      const pendingIds = new Set(pendingCommits.map((c) => c.taskId));
      const mergedTasks: Task[] = pendingIds.size === 0
        ? tasksData
        : tasksData.map((t) => (pendingIds.has(t.id) ? { ...t, status: 'approved' as const } : t));
      setTasks(mergedTasks);
      setClasses(classesData);
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  }, [pendingCommits]);

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 5000);
    return () => clearInterval(interval);
  }, [refreshData]);

  const handleProcessAudio = async (audioBlob: Blob, filename: string, imageFile?: File | null) => {
    setIsProcessing(true);
    try {
      const res = await processAudio(audioBlob, filename, imageFile);
      if (res.tasks) {
        setTasks(res.tasks);
        await refreshData();
      }

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
    } finally {
      setIsProcessing(false);
      refreshData();
    }
  };

  const handleApproveWithUndo = (task: Task, actionVerb: string) => {
    const commitId = `commit-${Date.now()}-${Math.random()}`;
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, status: 'approved' } : t))
    );
    setPendingCommits((prev) => [
      ...prev,
      {
        id: commitId,
        taskId: task.id,
        taskTitle: task.task,
        actionVerb,
        createdAt: Date.now(),
      },
    ]);
  };

  const handleFinalCommit = async (commitId: string, taskId: string) => {
    setPendingCommits((prev) => prev.filter((c) => c.id !== commitId));
    try {
      await approveTask(taskId);
      await refreshData();
    } catch (err) {
      console.error(`Final commit failed for task ${taskId}:`, err);
    }
  };

  const handleUndoCommit = (commitId: string, taskId: string) => {
    setPendingCommits((prev) => prev.filter((c) => c.id !== commitId));
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: 'pending_approval' } : t))
    );
  };

  const handleRejectTask = useCallback(async (taskId: string) => {
    try {
      await rejectTask(taskId);
      await refreshData();
    } catch (err) {
      console.error(`Reject failed:`, err);
    }
  }, [refreshData]);


  return (
    <div className="app-layout">
      <main className="app-content">
        {/* HERO SECTION */}
        <div className="section-container cream-canvas" style={{ position: 'relative', overflow: 'hidden' }}>
          
          {/* Background Animation Layer */}
          <div className="hero-ambient-bg">
            <div className="ambient-orb orb-1"></div>
            <div className="ambient-orb orb-2"></div>
            <div className="ambient-orb orb-3"></div>
          </div>

          <div className="section-content hero-section" style={{ position: 'relative', zIndex: 2 }}>
            <h1 className="hero-wordmark">
              Speak your mind,<br />
              <span style={{ fontStyle: 'italic' }}>we'll do the rest.</span>
            </h1>
            <p className="hero-tagline">
              Delegate tasks with your voice.<br />
              One note in, actionable results out.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', width: '100%', maxWidth: '600px', margin: '0 auto' }}>
              <AudioInputBar
                onProcessAudio={handleProcessAudio}
                isProcessing={isProcessing}
                speakOn={speakOn}
                onToggleSpeak={toggleSpeak}
              />
              <span style={{ fontFamily: 'var(--font-figtree)', fontSize: 'var(--text-caption)', color: 'var(--color-fog)' }}>
                Available on Mac, Windows, iPhone, and Android
              </span>
            </div>
          </div>
        </div>

        {/* Dark Section: Activity Feed & Ladder */}
        <div className="section-container dark-chamber">
          <div className="section-content">
            <div className="activity-header">
              <div>
                <h2 className="activity-heading">One note, sorted <span style={{ fontStyle: 'italic' }}>tasks</span></h2>
                <p style={{ marginTop: '16px', fontSize: 'var(--text-body)', color: 'var(--color-pale-sage)', opacity: 0.9 }}>
                  Deployed to Cloud Run with Gemini 3.5 Flash, Sollu hits 6.5s end-to-end.<br />
                  Watch tasks extract and sort automatically.
                </p>
              </div>
            </div>
            
            <div style={{ marginTop: '64px' }}>
              <Board
                tasks={tasks}
                classes={classes}
                focusedTaskId={null}
                onApproveTask={handleApproveWithUndo}
                onRejectTask={handleRejectTask}
                onViewArtifact={(task) => setSelectedArtifactTask(task)}
              />
            </div>
          </div>
        </div>

        {/* Cream Section: Matrix */}
        <div className="section-container cream-canvas">
          <div className="section-content">
            <h2 className="activity-heading" style={{ marginBottom: '32px' }}>Trust <span style={{ fontStyle: 'italic' }}>ladder</span></h2>
            <TrustLadderMatrix classes={classes} />
          </div>
        </div>

      </main>

      <UndoToastContainer
        commits={pendingCommits}
        onCommit={handleFinalCommit}
        onUndo={handleUndoCommit}
      />

      <ArtifactModal
        task={selectedArtifactTask}
        onClose={() => setSelectedArtifactTask(null)}
      />
    </div>
  );
};

export default App;
