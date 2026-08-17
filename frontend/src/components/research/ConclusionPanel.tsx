import React from 'react';
import type { Conclusion } from '../../types';

interface ConclusionPanelProps {
  conclusions: Conclusion[];
}

export const ConclusionPanel: React.FC<ConclusionPanelProps> = ({ conclusions }) => {
  if (!conclusions || conclusions.length === 0) {
    return (
      <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-6 text-center text-[#9CA3AF] text-xs font-mono">
        No synthesized conclusions generated yet for this research run.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#EA580C]">
          01. Executive Synthesis & Conclusion
        </span>
        <span className="text-[11px] font-mono text-[#9CA3AF]">
          Deterministic Knowledge Graph Output
        </span>
      </div>

      <div className="space-y-4">
        {conclusions.map((conc) => {
          const confidencePct = Math.round(conc.confidence * 100);
          return (
            <div
              key={conc.id}
              className="relative overflow-hidden bg-[#191C21] border border-[#262A33] hover:border-[#EA580C]/40 rounded-lg p-6 shadow-xl space-y-4 transition-all"
            >
              {/* Left hairline accent bar */}
              <div className="absolute top-0 bottom-0 left-0 w-1 bg-[#EA580C]" />

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pl-2">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#FDBA74]">
                  SYNTHESIZED RESULT STATEMENT
                </span>
                <div className="flex items-center gap-2 bg-[#12151A] px-2.5 py-1 rounded border border-[#262A33] text-[11px] font-mono">
                  <span className="text-[#9CA3AF]">Confidence Meter:</span>
                  <span className="font-bold text-[#10B981]">{confidencePct}%</span>
                </div>
              </div>

              <p className="text-[#F9FAFB] text-base leading-relaxed font-medium pl-2">
                {conc.statement}
              </p>

              <div className="pt-3 border-t border-[#262A33] flex flex-wrap items-center justify-between text-[11px] font-mono text-[#9CA3AF] gap-2 pl-2">
                <span className="text-[#EA580C] font-semibold">
                  Backed by {conc.finding_ids?.length || 0} Traceable Findings
                </span>
                <span>Generated {new Date(conc.created_at).toLocaleTimeString()}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
