import React from 'react';
import type { Task, TaskLane } from '../types';
import { TaskCard } from './TaskCard';
import { Zap, Compass, Clock, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface LanesBoardProps {
  tasks: Task[];
  onApprove: (taskId: string) => Promise<void>;
  onReject: (taskId: string) => Promise<void>;
  onViewArtifact: (task: Task) => void;
}

const LANES: Array<{
  id: TaskLane;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
}> = [
  {
    id: 'now',
    title: 'Now',
    subtitle: 'Urgent calls & direct message drafts',
    icon: <Zap className="w-4 h-4 text-[#043f2e]" />,
  },
  {
    id: 'next',
    title: 'Next',
    subtitle: 'Grounded web research & synthesis',
    icon: <Compass className="w-4 h-4 text-[#043f2e]" />,
  },
  {
    id: 'later',
    title: 'Later',
    subtitle: 'Deferred until condition is satisfied',
    icon: <Clock className="w-4 h-4 text-[#043f2e]" />,
  },
];

export const LanesBoard: React.FC<LanesBoardProps> = ({
  tasks,
  onApprove,
  onReject,
  onViewArtifact,
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {LANES.map((lane) => {
        const laneTasks = tasks.filter((t) => t.lane === lane.id);

        return (
          <div
            key={lane.id}
            className="flex flex-col min-h-[420px]"
          >
            {/* Lane Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-[4px] bg-[#fcfcfc] shadow-sm">
                  {lane.icon}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-serif text-2xl tracking-[-0.72px] text-[#043f2e]">{lane.title}</h3>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded-[4px] bg-[#eef2e3] text-[#043f2e] border border-[#043f2e]/15 font-semibold">
                      {laneTasks.length}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#242423]/80 font-sans">{lane.subtitle}</p>
                </div>
              </div>
            </div>

            {/* Task List (Scrollable column) */}
            <div className="flex-1 space-y-3 max-h-[600px] overflow-y-auto pr-1.5">
              <AnimatePresence mode="popLayout">
                {laneTasks.length > 0 ? (
                  laneTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onApprove={onApprove}
                      onReject={onReject}
                      onViewArtifact={onViewArtifact}
                    />
                  ))
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="h-44 flex flex-col items-center justify-center text-center p-4 border border-dashed border-[#043f2e]/20 rounded-[12px] bg-[#eef2e3]/40"
                  >
                    <CheckCircle2 className="w-5 h-5 text-[#043f2e]/40 mb-2" />
                    <p className="text-xs text-[#043f2e] font-medium">No tasks in {lane.title}</p>
                    <p className="text-[11px] text-[#242423]/70 max-w-[180px] mt-0.5">
                      Spoken notes will automatically triage here.
                    </p>
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
