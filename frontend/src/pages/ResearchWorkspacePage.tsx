import React, { useEffect, useState, useRef } from 'react';
import { api } from '../services/api';
import type { ResearchProject, CreateProjectPayload } from '../types';
import { ResearchCountdownWidget } from '../components/ResearchCountdownWidget';
import { CreateProjectModal } from '../components/CreateProjectModal';

interface ResearchWorkspacePageProps {
  onViewRunResults: (runId: string) => void;
}

export const ResearchWorkspacePage: React.FC<ResearchWorkspacePageProps> = ({
  onViewRunResults,
}) => {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [questionText, setQuestionText] = useState('');
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState<number>(-1);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pipelineSteps = [
    '01 QUESTION • INITIALIZING RESEARCH BOUNDARY',
    '02 DECOMPOSITION • GENERATING TARGETED SUB-INQUIRIES',
    '03 SOURCE DISCOVERY • INDEXING & DEDUPLICATING DOMAIN SOURCES',
    '04 CONTENT ANALYSIS • EXTRACTING DOCUMENT TEXT & SHA256 HASHES',
    '05 FINDINGS • STRUCTURING ATOMIC INSIGHT CANDIDATES',
    '06 EVIDENCE • LINKING DIRECT TEXT EXCERPTS & RELEVANCE SCORES',
    '07 CONTRADICTIONS • AUDITING CONFLICTING EVIDENCE & SEVERITY',
    '08 SYNTHESIS • GENERATING TRACEABLE CONCLUSION GRAPH',
  ];

  const loadProjects = async () => {
    try {
      const data = await api.listProjects();
      // Deduplicate projects by unique name to ensure no duplicate workspace options appear
      const seenNames = new Set<string>();
      const uniqueProjects: ResearchProject[] = [];
      for (const p of data) {
        const key = p.name.trim().toLowerCase();
        if (!seenNames.has(key)) {
          seenNames.add(key);
          uniqueProjects.push(p);
        }
      }
      setProjects(uniqueProjects);
      if (uniqueProjects.length > 0 && !selectedProjectId) {
        setSelectedProjectId(uniqueProjects[0].id);
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  useEffect(() => {
    loadProjects();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleCreateProject = async (payload: CreateProjectPayload) => {
    const newProj = await api.createProject(payload);
    await loadProjects();
    setSelectedProjectId(newProj.id);
  };

  const handleStartPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!questionText.trim() || !selectedProjectId) {
      setError('Please select a workspace and enter a research question.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setStepIndex(0);

      // 1. Create question
      const qObj = await api.createQuestion(selectedProjectId, {
        question: questionText.trim(),
        status: 'active',
      });

      // 2. Trigger run
      setStepIndex(1);
      const runObj = await api.createRun(qObj.id, { mode: 'workspace_console' });

      // Smooth simulated progress timer that advances active stages smoothly during live LLM research
      const stageSchedule = [
        { step: 1, atMs: 1500 },
        { step: 2, atMs: 7000 },
        { step: 3, atMs: 18000 },
        { step: 4, atMs: 38000 },
        { step: 5, atMs: 58000 },
        { step: 6, atMs: 75000 },
        { step: 7, atMs: 90000 },
      ];

      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startTime;
        for (let i = stageSchedule.length - 1; i >= 0; i--) {
          if (elapsed >= stageSchedule[i].atMs) {
            setStepIndex((prev) => Math.max(prev, stageSchedule[i].step));
            break;
          }
        }
      }, 1000);

      // 3. Initiate backend execution in parallel
      const executionPromise = api.executeRun(runObj.id);

      // 4. Poll status in parallel
      pollRef.current = setInterval(async () => {
        try {
          const updatedRun = await api.getRun(runObj.id);
          if (updatedRun.status === 'completed') {
            if (pollRef.current) clearInterval(pollRef.current);
            if (timerRef.current) clearInterval(timerRef.current);
            setStepIndex(pipelineSteps.length - 1);
            setTimeout(() => {
              onViewRunResults(runObj.id);
            }, 700);
          } else if (updatedRun.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current);
            if (timerRef.current) clearInterval(timerRef.current);
            setError(updatedRun.error_message || 'Pipeline execution failed.');
            setLoading(false);
            setStepIndex(-1);
          }
        } catch {
          // Ignore transient poll errors
        }
      }, 2000);

      // Await execution completion
      const completedRun = await executionPromise;

      if (pollRef.current) clearInterval(pollRef.current);
      if (timerRef.current) clearInterval(timerRef.current);

      if (completedRun.status === 'completed') {
        setStepIndex(pipelineSteps.length - 1);
        setTimeout(() => {
          onViewRunResults(runObj.id);
        }, 700);
      } else if (completedRun.status === 'failed') {
        setError(completedRun.error_message || 'Pipeline execution failed.');
        setLoading(false);
        setStepIndex(-1);
      }
    } catch (err: unknown) {
      if (pollRef.current) clearInterval(pollRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
      setError(err instanceof Error ? err.message : 'Pipeline execution failed.');
      setStepIndex(-1);
      setLoading(false);
    }
  };

  const progressPercent = stepIndex >= 0 ? Math.min(100, Math.round(((stepIndex + 1) / pipelineSteps.length) * 100)) : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Bottom-Left Live Deep Research Radar HUD */}
      <ResearchCountdownWidget
        active={loading}
        currentStepName={stepIndex >= 0 ? pipelineSteps[stepIndex] : ''}
        currentStepIndex={Math.max(0, stepIndex)}
        totalSteps={pipelineSteps.length}
      />

      {/* Workspace Header */}
      <div className="text-center space-y-2 font-mono">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[#EA580C] bg-[#EA580C]/10 px-2.5 py-1 rounded border border-[#EA580C]/20">
          MODUS RESEARCH CONSOLE
        </span>
        <h1 className="text-3xl font-extrabold text-white tracking-tight font-sans">
          Research Execution Launcher
        </h1>
        <p className="text-[#9CA3AF] text-xs font-sans max-w-xl mx-auto">
          Enter an enterprise research question to initiate multi-stage source discovery, content extraction, evidence linking, and conclusion synthesis.
        </p>
      </div>

      {/* Launcher Console Form */}
      <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-7 shadow-2xl space-y-6">
        {error && (
          <div className="p-3 bg-[#EF4444]/10 border border-[#EF4444]/25 rounded text-[#EF4444] text-xs font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleStartPipeline} className="space-y-5 font-mono text-xs">
          {/* Target Workspace Select & Create Button */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block font-semibold text-[#9CA3AF] uppercase tracking-wider text-[10px]">
                Target Workspace Entity *
              </label>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(true)}
                disabled={loading}
                className="text-[10px] text-[#EA580C] hover:text-[#FDBA74] transition-colors font-mono cursor-pointer flex items-center gap-1"
              >
                + New Workspace
              </button>
            </div>

            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              disabled={loading}
              className="w-full px-3.5 py-2.5 bg-[#12151A] border border-[#262A33] rounded text-[#F9FAFB] text-xs focus:outline-none focus:border-[#EA580C] cursor-pointer"
            >
              {projects.length === 0 ? (
                <option value="">No workspaces found (click + New Workspace)</option>
              ) : (
                projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {p.research_topic} {p.industry ? `(${p.industry})` : ''}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Research Question Textarea */}
          <div>
            <label className="block font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1.5 text-[10px]">
              Research Question *
            </label>
            <textarea
              rows={4}
              required
              disabled={loading}
              placeholder="e.g. How are large banks deploying generative AI in fraud detection, compliance, and customer service, and what evidence justifies the operational and regulatory risks?"
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-[#12151A] border border-[#262A33] rounded text-[#F9FAFB] placeholder-[#6B7280] text-xs leading-relaxed font-sans focus:outline-none focus:border-[#EA580C]"
            />
          </div>

          {/* Demonstration Preset Shortcuts */}
          <div className="space-y-1.5">
            <span className="text-[10px] text-[#9CA3AF] uppercase tracking-wider block">
              ENTERPRISE DEMO PRESETS:
            </span>
            <div className="flex flex-wrap gap-2 text-[11px]">
              <button
                type="button"
                onClick={() =>
                  setQuestionText('How is AI transforming retail store operations and inventory management?')
                }
                className="px-2.5 py-1 bg-[#12151A] hover:bg-[#22262D] border border-[#262A33] rounded text-[#FDBA74] transition-colors font-mono cursor-pointer"
              >
                Retail AI Operations
              </button>
              <button
                type="button"
                onClick={() =>
                  setQuestionText('What computer vision models optimize assembly line quality control in manufacturing?')
                }
                className="px-2.5 py-1 bg-[#12151A] hover:bg-[#22262D] border border-[#262A33] rounded text-[#FDBA74] transition-colors font-mono cursor-pointer"
              >
                Manufacturing Quality Control
              </button>
              <button
                type="button"
                onClick={() =>
                  setQuestionText('What is the ROI and implementation timeline for generative AI in banking compliance and fraud detection?')
                }
                className="px-2.5 py-1 bg-[#12151A] hover:bg-[#22262D] border border-[#262A33] rounded text-[#FDBA74] transition-colors font-mono cursor-pointer"
              >
                Banking AI Compliance
              </button>
            </div>
          </div>

          {/* Action Button */}
          <button
            type="submit"
            disabled={loading || projects.length === 0}
            className="w-full py-3.5 bg-[#EA580C] hover:bg-[#C2410C] disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider rounded transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                EXECUTING PIPELINE STAGES...
              </>
            ) : (
              <>RUN RESEARCH PIPELINE 🚀</>
            )}
          </button>
        </form>

        {/* Real-time Technical Stage Monitor & Progress Bar */}
        {stepIndex >= 0 && (
          <div className="pt-5 border-t border-[#262A33] space-y-4 animate-fade-in font-mono">
            {/* Top Progress Bar */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-[#EA580C] font-bold uppercase tracking-wider flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#EA580C] animate-ping" />
                  PIPELINE PROGRESS
                </span>
                <span className="text-[#FDBA74] font-bold">{progressPercent}% • STEP {stepIndex + 1} OF {pipelineSteps.length}</span>
              </div>
              <div className="h-2 w-full bg-[#12151A] rounded-full overflow-hidden border border-[#262A33]">
                <div
                  className="h-full bg-gradient-to-r from-[#EA580C] to-[#F97316] transition-all duration-700 rounded-full"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            {/* Stepper list */}
            <div className="space-y-1.5">
              {pipelineSteps.map((stepName, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-3 p-2.5 rounded border text-[11px] font-mono transition-all ${
                    i === stepIndex
                      ? 'bg-[#EA580C]/10 border-[#EA580C]/50 text-[#FDBA74] font-semibold'
                      : i < stepIndex
                      ? 'bg-[#10B981]/5 border-[#10B981]/25 text-[#10B981]'
                      : 'bg-[#12151A] border-[#262A33] text-[#6B7280] opacity-40'
                  }`}
                >
                  <span className="w-4 h-4 flex items-center justify-center rounded text-[10px] font-bold">
                    {i < stepIndex ? '✓' : i === stepIndex ? '⚙' : '○'}
                  </span>
                  <span className="truncate">{stepName}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateProject}
      />
    </div>
  );
};
