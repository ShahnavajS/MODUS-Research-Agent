import React from 'react';
import { createPortal } from 'react-dom';

interface ResearchCountdownWidgetProps {
  active: boolean;
  currentStepName: string;
  currentStepIndex: number;
  totalSteps: number;
  elapsedSeconds?: number;
  questionText?: string;
  projectName?: string;
  isCompleted?: boolean;
  onJumpToWorkspace?: () => void;
  onViewResults?: () => void;
  onDismiss?: () => void;
}

export const ResearchCountdownWidget: React.FC<ResearchCountdownWidgetProps> = ({
  active,
  currentStepName,
  currentStepIndex,
  totalSteps,
  elapsedSeconds = 0,
  questionText = '',
  isCompleted = false,
  onJumpToWorkspace,
  onViewResults,
  onDismiss,
}) => {
  if (!active && !isCompleted) return null;
  if (typeof document === 'undefined') return null;

  const progressPercent = isCompleted
    ? 100
    : Math.min(100, Math.round(((currentStepIndex + 1) / totalSteps) * 100));

  const formatElapsed = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const remainingSec = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${remainingSec.toString().padStart(2, '0')}s`;
  };

  const widgetContent = (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        left: '24px',
        zIndex: 9999,
      }}
      className="font-mono text-xs animate-slide-up pointer-events-auto"
    >
      <div className="bg-[#191C21]/95 border border-[#EA580C]/50 hover:border-[#EA580C] rounded-lg p-4 shadow-2xl backdrop-blur-md w-84 space-y-3.5 relative overflow-hidden transition-all">
        {/* Animated Top Shimmer Bar */}
        <div
          className={`absolute top-0 left-0 h-1 transition-all duration-500 ${
            isCompleted
              ? 'bg-gradient-to-r from-[#10B981] to-[#34D399]'
              : 'bg-gradient-to-r from-[#EA580C] via-[#FDBA74] to-[#EA580C]'
          }`}
          style={{ width: `${progressPercent}%` }}
        />

        {/* Header with Live Pulse and Elapsed Timer */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isCompleted ? (
              <span className="w-2.5 h-2.5 rounded-full bg-[#10B981] flex items-center justify-center text-[8px] text-white font-bold">
                ✓
              </span>
            ) : (
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#EA580C] opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#EA580C]" />
              </span>
            )}
            <span
              className={`font-bold text-[11px] uppercase tracking-wider ${
                isCompleted ? 'text-[#10B981]' : 'text-[#EA580C]'
              }`}
            >
              {isCompleted ? 'RESEARCH COMPLETED' : 'BACKGROUND RESEARCH ACTIVE'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#12151A] px-2 py-0.5 rounded border border-[#262A33]">
            <span className="text-[10px] text-[#9CA3AF]">⏱</span>
            <span className="text-[#FDBA74] font-bold text-xs font-mono">
              {formatElapsed(elapsedSeconds)}
            </span>
          </div>
        </div>

        {/* Question Snippet */}
        {questionText && (
          <div className="text-[#9CA3AF] text-[10px] font-sans line-clamp-1 italic">
            "{questionText}"
          </div>
        )}

        {/* Current Active Stage & Radar Animation */}
        <div className="space-y-1 bg-[#12151A] p-2.5 rounded border border-[#262A33]">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-[#9CA3AF] uppercase tracking-wider font-semibold">
              {isCompleted
                ? 'ALL 8 STAGES COMPLETE'
                : `STAGE ${Math.min(totalSteps, currentStepIndex + 1)} OF ${totalSteps}`}
            </span>
            <span
              className={`font-bold flex items-center gap-1 text-[9px] ${
                isCompleted ? 'text-[#10B981]' : 'text-[#EA580C]'
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isCompleted ? 'bg-[#10B981]' : 'bg-[#EA580C] animate-pulse'
                }`}
              />
              {isCompleted ? 'READY' : 'PROCESSING'}
            </span>
          </div>

          <div className="text-[#F9FAFB] font-semibold text-[11px] truncate leading-snug pt-0.5">
            {isCompleted
              ? 'Traceable conclusions & evidence grounded.'
              : currentStepName || 'Executing pipeline stages...'}
          </div>
        </div>

        {/* Dynamic Progress Bar */}
        <div className="space-y-1.5">
          <div className="h-1.5 w-full bg-[#12151A] rounded-full overflow-hidden border border-[#262A33] relative">
            <div
              className={`h-full transition-all duration-500 rounded-full ${
                isCompleted
                  ? 'bg-gradient-to-r from-[#10B981] to-[#34D399]'
                  : 'bg-gradient-to-r from-[#EA580C] to-[#F97316]'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-[10px] text-[#9CA3AF]">
            <span className="text-[#FDBA74] font-semibold">{progressPercent}% Completed</span>
            <span className="text-[9px] text-[#6B7280]">MODUS Engine</span>
          </div>
        </div>

        {/* Quick Action Navigation Button */}
        <div className="flex items-center gap-2 pt-1">
          {isCompleted && onViewResults ? (
            <button
              onClick={onViewResults}
              className="flex-1 py-1.5 bg-[#10B981] hover:bg-[#059669] text-white font-bold rounded text-[11px] transition-colors cursor-pointer text-center shadow-sm"
            >
              View Research Results →
            </button>
          ) : onJumpToWorkspace ? (
            <button
              onClick={onJumpToWorkspace}
              className="flex-1 py-1.5 bg-[#EA580C] hover:bg-[#C2410C] text-white font-bold rounded text-[11px] transition-colors cursor-pointer text-center shadow-sm"
            >
              Return to Research Launcher →
            </button>
          ) : null}

          {onDismiss && isCompleted && (
            <button
              onClick={onDismiss}
              title="Dismiss notification"
              className="px-2 py-1.5 bg-[#12151A] hover:bg-[#22262D] text-[#9CA3AF] hover:text-white rounded border border-[#262A33] text-[11px] transition-colors cursor-pointer"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(widgetContent, document.body);
};
