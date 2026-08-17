import React, { useState } from 'react';
import type { ResearchSource } from '../../types';

interface SourceListProps {
  sources: ResearchSource[];
}

export const SourceList: React.FC<SourceListProps> = ({ sources }) => {
  const [selectedSource, setSelectedSource] = useState<ResearchSource | null>(null);

  if (!sources || sources.length === 0) {
    return (
      <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-6 text-center text-[#9CA3AF] text-xs font-mono">
        No external research sources acquired for this run.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between font-mono">
        <span className="text-xs font-bold uppercase tracking-wider text-[#06B6D4]">
          04. Acquired External Research Sources ({sources.length})
        </span>
        <span className="text-[11px] text-[#9CA3AF]">
          Verified Domain Index References
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono">
        {sources.map((src) => {
          const credibilityPct = src.credibility_score ? Math.round(src.credibility_score * 100) : 80;
          const meta = (src.metadata_json || {}) as Record<string, any>;
          const rawState = String(
            meta.lifecycle_state ||
            (src.content?.extraction_status === 'success'
              ? 'EVIDENCE_ELIGIBLE'
              : (src.content?.extraction_status === 'failed' ? 'FETCH_FAILED' : 'REJECTED'))
          ).toUpperCase();

          const isRejected = rawState === 'REJECTED' || rawState === 'HARD_EXCLUDED' || rawState === 'REJECTED_IRRELEVANT';
          const isFailed = rawState === 'FETCH_FAILED' || src.content?.extraction_status === 'failed';
          const isEvidenceEligible = (rawState === 'EVIDENCE_ELIGIBLE' || meta.is_evidence_eligible === true) && src.content?.extraction_status === 'success';

          const statusBadgeText = isRejected
            ? 'REJECTED'
            : isFailed
            ? 'FETCH_FAILED'
            : isEvidenceEligible
            ? 'EVIDENCE_ELIGIBLE'
            : 'DISCOVERED';

          const statusBadgeClass = isRejected
            ? 'bg-red-500/10 text-red-400 border-red-500/20'
            : isFailed
            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            : isEvidenceEligible
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';

          const rejectionReason = meta.rejection_reason || (isRejected ? 'INSUFFICIENT_RELEVANCE' : (isFailed ? 'FETCH_FAILED' : null));

          return (
            <div
              key={src.id}
              className={`bg-[#191C21] border rounded-lg p-4 shadow-md flex flex-col justify-between space-y-3 transition-all ${
                isRejected
                  ? 'border-red-900/30 opacity-85'
                  : isFailed
                  ? 'border-amber-900/30 opacity-90'
                  : 'border-[#262A33] hover:border-[#EA580C]/40'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-1.5">
                    <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-[#EA580C]/10 text-[#EA580C] border border-[#EA580C]/20">
                      {src.source_type}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold border ${statusBadgeClass}`}>
                      {statusBadgeText}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px]">
                    <span className="text-[#9CA3AF]">Credibility:</span>
                    <span className="font-bold text-[#10B981]">{credibilityPct}%</span>
                  </div>
                </div>

                <h4 className="text-sm font-bold text-[#F9FAFB] font-sans line-clamp-2 leading-snug">
                  {src.title}
                </h4>

                {/* Audit & Eligibility Information Banner */}
                {isRejected && (
                  <div className="p-2 rounded bg-red-950/20 border border-red-900/30 text-[10px] space-y-0.5">
                    <div className="text-red-300 font-bold">
                      Reason: <span className="font-mono text-red-200">{rejectionReason}</span>
                    </div>
                    <div className="text-[#9CA3AF]">
                      Evidence eligible: <span className="text-red-400 font-bold">NO</span>
                    </div>
                  </div>
                )}

                {isFailed && (
                  <div className="p-2 rounded bg-amber-950/20 border border-amber-900/30 text-[10px] space-y-0.5">
                    <div className="text-amber-300 font-bold">
                      Fetch Status: <span className="font-mono text-amber-200">{rejectionReason || 'FETCH_FAILED'}</span>
                    </div>
                    <div className="text-[#9CA3AF]">
                      Evidence eligible: <span className="text-amber-400 font-bold">NO</span>
                    </div>
                  </div>
                )}

                {isEvidenceEligible && (
                  <div className="p-1.5 rounded bg-emerald-950/20 border border-emerald-900/30 text-[10px] flex items-center justify-between">
                    <span className="text-[#9CA3AF]">Evidence eligible: <span className="text-emerald-400 font-bold">YES</span></span>
                    {src.content?.word_count && (
                      <span className="text-emerald-300 font-mono">{src.content.word_count} words extracted</span>
                    )}
                  </div>
                )}

                {src.publisher && (
                  <p className="text-[11px] text-[#9CA3AF]">
                    Publisher: <span className="text-[#F9FAFB]">{src.publisher}</span> {src.author ? `• ${src.author}` : ''}
                  </p>
                )}
              </div>

              <div className="pt-2.5 border-t border-[#262A33] flex items-center justify-between text-xs">
                {src.url ? (
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[#EA580C] hover:underline text-[11px] truncate max-w-[180px]"
                  >
                    {src.url} ↗
                  </a>
                ) : (
                  <span className="text-[#6B7280] text-[11px]">No URL</span>
                )}

                {src.content && src.content.extraction_status === 'success' && (
                  <button
                    onClick={() => setSelectedSource(src)}
                    className="px-2.5 py-1 bg-[#12151A] hover:bg-[#22262D] text-[#F9FAFB] rounded border border-[#262A33] text-[11px] font-semibold transition-colors"
                  >
                    Inspect Text
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Extracted Text Content Modal */}
      {selectedSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0E1013]/80 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-[#191C21] border border-[#262A33] rounded-lg shadow-2xl max-w-2xl w-full p-6 text-[#F9FAFB] space-y-4 max-h-[85vh] flex flex-col font-mono text-xs">
            <div className="flex justify-between items-center pb-3 border-b border-[#262A33]">
              <div>
                <span className="text-[10px] text-[#EA580C] uppercase font-bold tracking-wider">Source Document Reader</span>
                <h3 className="text-sm font-bold text-white font-sans mt-0.5">{selectedSource.title}</h3>
                <p className="text-[11px] text-[#06B6D4] truncate mt-0.5">{selectedSource.url}</p>
              </div>
              <button
                onClick={() => setSelectedSource(null)}
                className="text-[#9CA3AF] hover:text-white text-base font-bold"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto bg-[#12151A] p-4 rounded border border-[#262A33] text-[11px] leading-relaxed text-[#D1D5DB] whitespace-pre-wrap">
              {selectedSource.content?.content || 'No text extracted.'}
            </div>

            <div className="flex justify-between items-center pt-2.5 border-t border-[#262A33] text-[11px] text-[#9CA3AF]">
              <span>Word Count: {selectedSource.content?.word_count || 0}</span>
              <button
                onClick={() => setSelectedSource(null)}
                className="px-4 py-1.5 bg-[#EA580C] hover:bg-[#C2410C] text-white rounded font-semibold text-xs transition-colors"
              >
                Close Reader
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
