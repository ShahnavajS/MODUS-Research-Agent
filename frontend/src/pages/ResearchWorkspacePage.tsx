import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ResearchProject, CreateProjectPayload } from '../types';
import { CreateProjectModal } from '../components/CreateProjectModal';
import { useResearch } from '../context/ResearchContext';

interface ResearchWorkspacePageProps {
  onViewRunResults: (runId: string) => void;
}

export const ResearchWorkspacePage: React.FC<ResearchWorkspacePageProps> = ({
  onViewRunResults,
}) => {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [questionText, setQuestionText] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const {
    isRunning,
    stepIndex,
    error: contextError,
    activeProjectId,
    activeQuestionText,
    pipelineSteps,
    startResearch,
    isCompleted,
    completedRunId,
    dismissCompleted,
  } = useResearch();

  // Load and deduplicate projects
  const loadProjects = async () => {
    try {
      const data = await api.listProjects();
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
      if (uniqueProjects.length > 0) {
        if (activeProjectId) {
          setSelectedProjectId(activeProjectId);
        } else if (!selectedProjectId) {
          setSelectedProjectId(uniqueProjects[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  // Sync active question text if research is running
  useEffect(() => {
    if (isRunning && activeQuestionText) {
      setQuestionText(activeQuestionText);
    }
    if (activeProjectId) {
      setSelectedProjectId(activeProjectId);
    }
  }, [isRunning, activeQuestionText, activeProjectId]);

  // Navigate to results immediately when research is complete
  useEffect(() => {
    if (isCompleted && completedRunId) {
      onViewRunResults(completedRunId);
    }
  }, [isCompleted, completedRunId, onViewRunResults]);

  const handleCreateProject = async (payload: CreateProjectPayload) => {
    const newProj = await api.createProject(payload);
    await loadProjects();
    setSelectedProjectId(newProj.id);
  };

  const handleStartPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!questionText.trim() || !selectedProjectId) {
      setLocalError('Please select a workspace and enter a research question.');
      return;
    }

    try {
      setLocalError(null);
      const proj = projects.find((p) => p.id === selectedProjectId);
      const projName = proj ? proj.name : '';
      const runId = await startResearch(selectedProjectId, questionText.trim(), projName);
      if (runId) {
        // Run initiated
      }
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : 'Pipeline execution failed.');
    }
  };

  const currentError = localError || contextError;
  const progressPercent =
    stepIndex >= 0 ? Math.min(100, Math.round(((stepIndex + 1) / pipelineSteps.length) * 100)) : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
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

      {/* Completion Banner (Guaranteed Fallback) */}
      {completedRunId && (
        <div className="p-4 bg-[#10B981]/15 border border-[#10B981]/40 rounded-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-fade-in">
          <div className="space-y-0.5">
            <div className="text-[#10B981] font-bold text-xs flex items-center gap-1.5 font-mono">
              <span>✓</span> RESEARCH PIPELINE COMPLETED SUCCESSFULLY
            </div>
            <p className="text-[#9CA3AF] text-[11px] font-sans">
              All 8 pipeline stages, evidence linking, and conclusion graphs generated.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              dismissCompleted();
              onViewRunResults(completedRunId);
            }}
            className="px-4 py-2 bg-[#10B981] hover:bg-[#059669] text-white font-bold text-xs rounded transition-colors shadow-lg cursor-pointer whitespace-nowrap"
          >
            View Research Results →
          </button>
        </div>
      )}

      {/* Launcher Console Form */}
      <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-7 shadow-2xl space-y-6">
        {currentError && (
          <div className="p-3 bg-[#EF4444]/10 border border-[#EF4444]/25 rounded text-[#EF4444] text-xs font-mono">
            {currentError}
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
                disabled={isRunning}
                className="text-[10px] text-[#EA580C] hover:text-[#FDBA74] transition-colors font-mono cursor-pointer flex items-center gap-1 disabled:opacity-50"
              >
                + New Workspace
              </button>
            </div>

            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              disabled={isRunning}
              className="w-full px-3.5 py-2.5 bg-[#12151A] border border-[#262A33] rounded text-[#F9FAFB] text-xs focus:outline-none focus:border-[#EA580C] cursor-pointer disabled:opacity-60"
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
              disabled={isRunning}
              placeholder="e.g. How are large banks deploying generative AI in fraud detection, compliance, and customer service, and what evidence justifies the operational and regulatory risks?"
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-[#12151A] border border-[#262A33] rounded text-[#F9FAFB] placeholder-[#6B7280] text-xs leading-relaxed font-sans focus:outline-none focus:border-[#EA580C] disabled:opacity-60"
            />
          </div>

          {/* Demonstration Preset Shortcuts */}
          {!isRunning && (
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
          )}

          {/* Action Button */}
          <button
            type="submit"
            disabled={isRunning || projects.length === 0}
            className="w-full py-3.5 bg-[#EA580C] hover:bg-[#C2410C] disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider rounded transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
          >
            {isRunning ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                EXECUTING PIPELINE STAGES IN BACKGROUND...
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
                  <span className={`w-2 h-2 rounded-full ${isCompleted ? 'bg-[#10B981]' : 'bg-[#EA580C] animate-ping'}`} />
                  {isCompleted ? 'PIPELINE COMPLETE' : 'PIPELINE PROGRESS (ACTIVE)'}
                </span>
                <span className="text-[#FDBA74] font-bold">
                  {progressPercent}% • STEP {Math.min(pipelineSteps.length, stepIndex + 1)} OF {pipelineSteps.length}
                </span>
              </div>
              <div className="h-2 w-full bg-[#12151A] rounded-full overflow-hidden border border-[#262A33]">
                <div
                  className={`h-full transition-all duration-700 rounded-full ${
                    isCompleted
                      ? 'bg-gradient-to-r from-[#10B981] to-[#34D399]'
                      : 'bg-gradient-to-r from-[#EA580C] to-[#F97316]'
                  }`}
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
                    isCompleted || i < stepIndex
                      ? 'bg-[#10B981]/5 border-[#10B981]/25 text-[#10B981]'
                      : i === stepIndex
                      ? 'bg-[#EA580C]/10 border-[#EA580C]/50 text-[#FDBA74] font-semibold'
                      : 'bg-[#12151A] border-[#262A33] text-[#6B7280] opacity-40'
                  }`}
                >
                  <span className="w-4 h-4 flex items-center justify-center rounded text-[10px] font-bold">
                    {isCompleted || i < stepIndex ? '✓' : i === stepIndex ? '⚙' : '○'}
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
