import React, { useEffect, useState } from 'react';

interface ResearchCountdownWidgetProps {
  active: boolean;
  currentStepName: string;
  currentStepIndex: number;
  totalSteps: number;
}

export const ResearchCountdownWidget: React.FC<ResearchCountdownWidgetProps> = ({
  active,
  currentStepName,
  currentStepIndex,
  totalSteps,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  useEffect(() => {
    if (!active) {
      setElapsedSeconds(0);
      return;
    }

    setElapsedSeconds(0);
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [active]);

  if (!active) return null;

  const progressPercent = Math.min(
    100,
    Math.round(((currentStepIndex + 1) / totalSteps) * 100)
  );

  const formatElapsed = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const remainingSec = sec % 60;
    return `${mins.toString().padStart(2, '0')}:${remainingSec.toString().padStart(2, '0')}s`;
  };

  return (
    <div className="fixed bottom-6 left-6 z-50 font-mono text-xs animate-slide-up">
      <div className="bg-[#191C21]/95 border border-[#EA580C]/40 rounded-lg p-4 shadow-2xl backdrop-blur-md w-80 space-y-3.5 relative overflow-hidden">
        {/* Animated Top Shimmer Bar */}
        <div
          className="absolute top-0 left-0 h-0.5 bg-gradient-to-r from-[#EA580C] via-[#FDBA74] to-[#EA580C] transition-all duration-500"
          style={{ width: `${progressPercent}%` }}
        />

        {/* Header with Live Pulse and Elapsed Timer */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#EA580C] opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#EA580C]" />
            </span>
            <span className="text-[#EA580C] font-bold text-[11px] uppercase tracking-wider">
              DEEP RESEARCH ACTIVE
            </span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#12151A] px-2 py-0.5 rounded border border-[#262A33]">
            <span className="text-[10px] text-[#9CA3AF]">⏱</span>
            <span className="text-[#FDBA74] font-bold text-xs">
              {formatElapsed(elapsedSeconds)}
            </span>
          </div>
        </div>

        {/* Current Active Stage & Radar Animation */}
        <div className="space-y-1 bg-[#12151A] p-2.5 rounded border border-[#262A33]">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-[#9CA3AF] uppercase tracking-wider font-semibold">
              STAGE {currentStepIndex + 1} OF {totalSteps}
            </span>
            <span className="text-[#10B981] font-bold flex items-center gap-1 text-[9px]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse" />
              PROCESSING
            </span>
          </div>

          <div className="text-[#F9FAFB] font-semibold text-[11px] truncate leading-snug pt-0.5">
            {currentStepName || 'Initializing research engine...'}
          </div>
        </div>

        {/* Dynamic Progress Bar */}
        <div className="space-y-1.5">
          <div className="h-1.5 w-full bg-[#12151A] rounded-full overflow-hidden border border-[#262A33] relative">
            <div
              className="h-full bg-gradient-to-r from-[#EA580C] to-[#F97316] transition-all duration-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-[10px] text-[#9CA3AF]">
            <span className="text-[#FDBA74] font-semibold">{progressPercent}% Completed</span>
            <span className="text-[9px] text-[#6B7280]">Multi-Stage Pipeline</span>
          </div>
        </div>
      </div>
    </div>
  );
};
