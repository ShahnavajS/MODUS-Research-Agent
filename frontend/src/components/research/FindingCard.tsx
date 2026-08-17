import React, { useState } from 'react';
import type { Finding } from '../../types';
import { Badge } from '../common/Badge';

interface FindingCardProps {
  finding: Finding;
  index: number;
}

export const FindingCard: React.FC<FindingCardProps> = ({ finding, index }) => {
  const [showEvidence, setShowEvidence] = useState(true);

  return (
    <div className="bg-[#191C21] border border-[#262A33] hover:border-[#EA580C]/40 rounded-lg p-5 shadow-lg space-y-3.5 transition-all">
      {/* Header Badges */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#262A33] pb-2.5">
        <div className="flex items-center gap-2 font-mono">
          <span className="text-[11px] text-[#EA580C] bg-[#EA580C]/10 px-2 py-0.5 rounded border border-[#EA580C]/20 font-bold">
            FINDING #{index + 1}
          </span>
          <Badge label={finding.finding_type} variant="type" />
          <Badge label={`IMPORTANCE: ${finding.importance}`} variant="importance" value={finding.importance} />
        </div>

        <div className="flex items-center gap-2 text-[11px] font-mono">
          <span className="text-[#9CA3AF]">Confidence:</span>
          <span className="font-bold text-[#10B981]">
            {Math.round(finding.confidence * 100)}%
          </span>
        </div>
      </div>

      {/* Finding Statement */}
      <p className="text-[#F9FAFB] text-sm leading-relaxed font-medium">
        {finding.statement}
      </p>

      {/* Traceable Evidence Accordion */}
      {finding.evidences && finding.evidences.length > 0 && (
        <div className="pt-2.5 border-t border-[#262A33] space-y-2">
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="flex items-center justify-between w-full text-[11px] font-mono font-semibold text-[#EA580C] hover:text-[#FDBA74] transition-colors"
          >
            <span>
              🔗 TRACEABLE SUPPORTING EVIDENCE ({finding.evidences.length})
            </span>
            <span>{showEvidence ? '▲ HIDE EXCERPTS' : '▼ VIEW EXCERPTS'}</span>
          </button>

          {showEvidence && (
            <div className="space-y-2 pt-1 font-mono text-xs">
              {finding.evidences.map((ev) => (
                <div
                  key={ev.id}
                  className="bg-[#12151A] border border-[#262A33] rounded p-3 space-y-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-[#9CA3AF]">
                    <span className="text-[#10B981] uppercase font-bold">
                      [{ev.evidence_type}] RELEVANCE: {Math.round(ev.relevance_score * 100)}%
                    </span>
                    {ev.source_title && (
                      <span className="truncate max-w-[240px] text-[#F9FAFB]">
                        Source: {ev.source_title}
                      </span>
                    )}
                  </div>

                  <p className="text-[#D1D5DB] italic bg-[#191C21] p-2.5 rounded border border-[#262A33] leading-relaxed font-sans text-xs">
                    "{ev.excerpt}"
                  </p>

                  {ev.source_url && (
                    <div className="text-right">
                      <a
                        href={ev.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[#EA580C] hover:underline text-[10px] uppercase font-bold inline-flex items-center gap-1"
                      >
                        Inspect Source Document ↗
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
