import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ResearchRunDetail } from '../types';
import { formatLocalDateTime, formatRelativeTime } from '../utils/date';
import { MetricCard } from '../components/common/MetricCard';
import { ConclusionPanel } from '../components/research/ConclusionPanel';
import { FindingCard } from '../components/research/FindingCard';
import { ContradictionList } from '../components/research/ContradictionList';
import { SourceList } from '../components/research/SourceList';

interface ResearchResultsPageProps {
  runId: string;
  onBack: () => void;
}

export const ResearchResultsPage: React.FC<ResearchResultsPageProps> = ({ runId, onBack }) => {
  const [detail, setDetail] = useState<ResearchRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'findings' | 'contradictions' | 'sources' | 'subquestions'>('overview');

  useEffect(() => {
    setLoading(true);
    api
      .getRunDetails(runId)
      .then((data) => {
        setDetail(data);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to fetch research run details');
      })
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) {
    return (
      <div className="py-20 text-center space-y-3 font-mono">
        <div className="w-6 h-6 border-2 border-[#EA580C] border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-[#9CA3AF] text-xs">Fetching research knowledge graph & evidence links...</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="space-y-4 max-w-2xl mx-auto py-12 font-mono">
        <button onClick={onBack} className="text-xs text-[#EA580C] hover:underline">
          ← Back to Workspace
        </button>
        <div className="p-4 bg-[#EF4444]/10 border border-[#EF4444]/25 rounded text-[#EF4444] text-xs">
          {error || 'Research run not found'}
        </div>
      </div>
    );
  }

  const meta = detail.metadata_json || {};
  const aiProviderStr = meta.ai_provider ? String(meta.ai_provider) : null;
  const aiModelStr = meta.ai_model ? String(meta.ai_model) : null;
  const researchProviderStr = meta.research_provider ? String(meta.research_provider) : null;
  const durationStr = meta.duration_seconds ? String(meta.duration_seconds) : null;

  return (
    <div className="space-y-8">
      {/* Top Header & Breadcrumb */}
      <div>
        <button
          onClick={onBack}
          className="text-xs text-[#EA580C] hover:underline font-mono font-semibold transition-colors mb-3 inline-flex items-center gap-1"
        >
          ← Back to Workspace
        </button>

        <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-6 shadow-xl space-y-3 relative overflow-hidden">
          <div className="absolute top-0 left-0 bottom-0 w-1 bg-[#EA580C]" />

          <div className="flex flex-wrap items-center justify-between gap-3 pl-2 font-mono">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 bg-[#10B981]/10 border border-[#10B981]/25 text-[#10B981] rounded text-[10px] font-bold uppercase tracking-wider">
                {detail.status}
              </span>
              <span className="text-xs text-[#9CA3AF]">
                RUN ID: {detail.id}
              </span>
            </div>
            <span className="text-[11px] text-[#9CA3AF]">
              Completed {detail.completed_at ? `${formatRelativeTime(detail.completed_at)} (${formatLocalDateTime(detail.completed_at)})` : ''}
            </span>
          </div>

          <div className="pl-2 space-y-1">
            <span className="text-[10px] font-mono text-[#EA580C] uppercase tracking-wider font-bold block">
              Workspace: {detail.project_name}
            </span>
            <h1 className="text-2xl font-extrabold text-white tracking-tight leading-snug">
              {detail.question_text}
            </h1>
          </div>

          {/* Real Provider Execution Metadata Bar */}
          <div className="pl-2 pt-2 border-t border-[#262A33] flex flex-wrap items-center gap-4 text-[10px] font-mono text-[#9CA3AF]">
            {aiProviderStr && (
              <span>AI Provider: <strong className="text-[#F9FAFB]">{aiProviderStr}</strong> ({aiModelStr || 'default'})</span>
            )}
            {researchProviderStr && (
              <span>Search Engine: <strong className="text-[#F9FAFB]">{researchProviderStr}</strong></span>
            )}
            {durationStr && (
              <span>Execution Time: <strong className="text-[#10B981]">{durationStr}s</strong></span>
            )}
          </div>
        </div>
      </div>

      {/* Metrics Summary Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <MetricCard title="Sub-Questions" value={detail.counts.sub_questions} icon="📋" accentColor="orange" />
        <MetricCard title="Sources" value={detail.counts.sources} icon="🌐" accentColor="cyan" />
        <MetricCard title="Findings" value={detail.counts.findings} icon="🔍" accentColor="amber" />
        <MetricCard title="Evidence" value={detail.counts.evidence} icon="🔗" accentColor="emerald" />
        <MetricCard title="Conflicts" value={detail.counts.contradictions} icon="⚠️" accentColor="amber" />
        <MetricCard title="Conclusions" value={detail.counts.conclusions} icon="✨" accentColor="orange" />
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-[#262A33] flex flex-wrap gap-2 pb-1 font-mono text-xs">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-3.5 py-1.5 rounded transition-all font-semibold ${
            activeTab === 'overview'
              ? 'bg-[#EA580C] text-white shadow-sm'
              : 'text-[#9CA3AF] hover:text-white hover:bg-[#191C21]'
          }`}
        >
          ✨ Conclusion
        </button>
        <button
          onClick={() => setActiveTab('findings')}
          className={`px-3.5 py-1.5 rounded transition-all font-semibold ${
            activeTab === 'findings'
              ? 'bg-[#EA580C] text-white shadow-sm'
              : 'text-[#9CA3AF] hover:text-white hover:bg-[#191C21]'
          }`}
        >
          🔍 Findings & Evidence ({detail.findings.length})
        </button>
        <button
          onClick={() => setActiveTab('contradictions')}
          className={`px-3.5 py-1.5 rounded transition-all font-semibold ${
            activeTab === 'contradictions'
              ? 'bg-[#EA580C] text-white shadow-sm'
              : 'text-[#9CA3AF] hover:text-white hover:bg-[#191C21]'
          }`}
        >
          ⚠️ Contradictions ({detail.contradictions.length})
        </button>
        <button
          onClick={() => setActiveTab('sources')}
          className={`px-3.5 py-1.5 rounded transition-all font-semibold ${
            activeTab === 'sources'
              ? 'bg-[#EA580C] text-white shadow-sm'
              : 'text-[#9CA3AF] hover:text-white hover:bg-[#191C21]'
          }`}
        >
          🌐 Sources ({detail.sources.length})
        </button>
        <button
          onClick={() => setActiveTab('subquestions')}
          className={`px-3.5 py-1.5 rounded transition-all font-semibold ${
            activeTab === 'subquestions'
              ? 'bg-[#EA580C] text-white shadow-sm'
              : 'text-[#9CA3AF] hover:text-white hover:bg-[#191C21]'
          }`}
        >
          📋 Sub-Questions ({detail.sub_questions.length})
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === 'overview' && (
        <div className="space-y-8">
          <ConclusionPanel conclusions={detail.conclusions} />
          
          <div className="space-y-4 font-mono">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-[#EA580C]">
                02. Member Findings & Traceable Evidence Preview
              </span>
              <button
                onClick={() => setActiveTab('findings')}
                className="text-xs text-[#EA580C] hover:underline font-semibold"
              >
                View all {detail.findings.length} findings →
              </button>
            </div>
            <div className="space-y-4">
              {detail.findings.slice(0, 2).map((f, idx) => (
                <FindingCard key={f.id} finding={f} index={idx} />
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'findings' && (
        <div className="space-y-4 font-mono">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#EA580C]">
              Traceable Findings & Evidence Excerpts
            </span>
            <span className="text-xs text-[#9CA3AF]">
              Total Evidence Links: {detail.counts.evidence}
            </span>
          </div>
          {detail.findings.length === 0 ? (
            <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-8 text-center text-[#9CA3AF] text-xs font-mono">
              No findings extracted for this run.
            </div>
          ) : (
            <div className="space-y-4">
              {detail.findings.map((f, idx) => (
                <FindingCard key={f.id} finding={f} index={idx} />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'contradictions' && (
        <ContradictionList contradictions={detail.contradictions} />
      )}

      {activeTab === 'sources' && (
        <SourceList sources={detail.sources} />
      )}

      {activeTab === 'subquestions' && (
        <div className="space-y-4 font-mono">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#EA580C]">
              Decomposed Sub-Inquiries ({detail.sub_questions.length})
            </span>
          </div>
          <div className="space-y-2.5">
            {detail.sub_questions.map((sq) => (
              <div
                key={sq.id}
                className="bg-[#191C21] border border-[#262A33] rounded-lg p-3.5 flex items-center justify-between gap-4 text-xs"
              >
                <div className="flex items-center gap-3">
                  <span className="w-5 h-5 rounded bg-[#EA580C]/10 text-[#EA580C] font-bold flex items-center justify-center border border-[#EA580C]/20 text-[11px]">
                    {sq.sequence_number}
                  </span>
                  <span className="text-[#F9FAFB] font-sans font-medium">{sq.question}</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/25">
                  {sq.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
