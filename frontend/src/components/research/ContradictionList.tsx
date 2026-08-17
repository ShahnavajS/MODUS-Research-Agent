import React from 'react';
import type { Contradiction } from '../../types';
import { Badge } from '../common/Badge';

interface ContradictionListProps {
  contradictions: Contradiction[];
}

export const ContradictionList: React.FC<ContradictionListProps> = ({ contradictions }) => {
  if (!contradictions || contradictions.length === 0) {
    return (
      <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-6 text-center text-[#9CA3AF] text-xs font-mono">
        No evidence contradictions or conflicting claims detected in this run.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#F59E0B]">
          03. Detected Contradictions & Conflict Audit ({contradictions.length})
        </span>
        <span className="text-[11px] font-mono text-[#9CA3AF]">
          Analytical Tension Preserved
        </span>
      </div>

      <div className="space-y-4">
        {contradictions.map((c) => (
          <div
            key={c.id}
            className="bg-[#191C21] border border-[#F59E0B]/30 rounded-lg p-5 shadow-lg space-y-3 font-mono text-xs"
          >
            <div className="flex items-center justify-between gap-2 border-b border-[#262A33] pb-2.5">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#F59E0B] font-bold uppercase">
                  CONFLICT DETECTED
                </span>
                <Badge label={`SEVERITY: ${c.severity}`} variant="severity" value={c.severity} />
              </div>
              <Badge label={`STATUS: ${c.resolution_status}`} variant="status" value={c.resolution_status} />
            </div>

            <p className="text-[#F9FAFB] text-sm font-sans font-medium leading-relaxed">
              {c.description}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              {c.finding_a_statement && (
                <div className="bg-[#12151A] p-3 rounded border border-[#262A33] space-y-1">
                  <span className="text-[#EA580C] text-[10px] uppercase font-bold block">Claim A:</span>
                  <p className="text-[#D1D5DB] font-sans text-xs">{c.finding_a_statement}</p>
                </div>
              )}
              {c.finding_b_statement && (
                <div className="bg-[#12151A] p-3 rounded border border-[#262A33] space-y-1">
                  <span className="text-[#FDBA74] text-[10px] uppercase font-bold block">Claim B (Conflict):</span>
                  <p className="text-[#D1D5DB] font-sans text-xs">{c.finding_b_statement}</p>
                </div>
              )}
            </div>

            {c.resolution_notes && (
              <div className="text-[11px] text-[#9CA3AF] bg-[#12151A]/80 p-2.5 rounded border border-[#262A33]">
                <span className="font-bold text-[#F9FAFB]">Resolution Note:</span> {c.resolution_notes}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
