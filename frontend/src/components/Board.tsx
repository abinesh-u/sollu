import React from 'react';
import type { Task, TaskLane, ClassInfo } from '../types';
import { TaskCard } from './TaskCard';
import { Zap, Compass, Clock, CheckCircle2 } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import './Board.css';

interface BoardProps {
  tasks: Task[];
  classes: ClassInfo[];
  focusedTaskId: string | null;
  onApproveTask: (task: Task, actionVerb: string) => void;
  onRejectTask: (taskId: string) => Promise<void>;
  onViewArtifact: (task: Task) => void;
}

const LANES: Array<{ id: TaskLane; title: string; subtitle: string; icon: React.ReactNode }> = [
  { id: 'now', title: 'Now', subtitle: 'Calls and messages, drafted and ready to send', icon: <Zap size={16} /> },
  { id: 'next', title: 'Next', subtitle: 'Requires web research or synthesis first', icon: <Compass size={16} /> },
  { id: 'later', title: 'Later', subtitle: 'Parked until a specific condition is met', icon: <Clock size={16} /> },
];

export const Board: React.FC<BoardProps> = ({
  tasks,
  classes,
  focusedTaskId,
  onApproveTask,
  onRejectTask,
  onViewArtifact,
}) => {
  return (
    <div className="board-feed">
      {LANES.map((lane) => {
        const laneTasks = tasks.filter((t) => t.lane === lane.id);

        return (
          <div key={lane.id} className="lane-section" data-lane={lane.id}>
            <div className="lane-header sticky">
              <div className="lane-icon-chip">{lane.icon}</div>
              <div>
                <div className="lane-title-row">
                  <h3 className="lane-title">{lane.title}</h3>
                  <span className="lane-count-chip">{laneTasks.length}</span>
                </div>
                <p className="lane-subtitle">{lane.subtitle}</p>
              </div>
            </div>

            <div className="lane-cards-grid" role="feed">
              <AnimatePresence mode="popLayout">
                {laneTasks.length > 0 ? (
                  laneTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      classes={classes}
                      isFocused={focusedTaskId === task.id}
                      onApprove={onApproveTask}
                      onReject={onRejectTask}
                      onViewArtifact={onViewArtifact}
                    />
                  ))
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="lane-empty"
                  >
                    <CheckCircle2 size={18} strokeWidth={1.5} />
                    <p className="lane-empty-title">Inbox Zero</p>
                    <p className="lane-empty-sub">No tasks pending in this triage lane.</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        );
      })}
    </div>
  );
};
