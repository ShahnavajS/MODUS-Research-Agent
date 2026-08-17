import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type {
  ResearchProject,
  ResearchQuestion,
  ResearchRun,
  UpdateProjectPayload,
  UpdateQuestionPayload,
} from '../types';
import { EditProjectModal } from '../components/EditProjectModal';
import { EditQuestionModal } from '../components/EditQuestionModal';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';

interface ProjectDetailPageProps {
  projectId: string;
  onBack: () => void;
  onViewRunResults: (runId: string) => void;
}

export const ProjectDetailPage: React.FC<ProjectDetailPageProps> = ({
  projectId,
  onBack,
  onViewRunResults,
}) => {
  const [project, setProject] = useState<ResearchProject | null>(null);
  const [questions, setQuestions] = useState<ResearchQuestion[]>([]);
  const [runsMap, setRunsMap] = useState<Record<string, ResearchRun[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [executingRunId, setExecutingRunId] = useState<string | null>(null);

  // Modals state
  const [isEditProjectOpen, setIsEditProjectOpen] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState<ResearchQuestion | null>(null);
  const [deleteModalConfig, setDeleteModalConfig] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    warningNote?: string;
    onConfirm: () => Promise<void>;
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: async () => {},
  });
  const [isDeleting, setIsDeleting] = useState(false);

  // New question form state
  const [newQuestionText, setNewQuestionText] = useState('');
  const [isSubmittingQuestion, setIsSubmittingQuestion] = useState(false);

  const fetchProjectData = async () => {
    try {
      setLoading(true);
      const [projData, qData] = await Promise.all([
        api.getProject(projectId),
        api.listQuestions(projectId),
      ]);
      setProject(projData);
      setQuestions(qData);

      // Fetch runs for each question
      const runsResults: Record<string, ResearchRun[]> = {};
      await Promise.all(
        qData.map(async (q) => {
          try {
            const runs = await api.listRuns(q.id);
            runs.sort(
              (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            );
            runsResults[q.id] = runs;
          } catch {
            runsResults[q.id] = [];
          }
        })
      );
      setRunsMap(runsResults);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load workspace details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjectData();
  }, [projectId]);

  const handleCreateQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newQuestionText.trim()) return;

    try {
      setIsSubmittingQuestion(true);
      await api.createQuestion(projectId, {
        question: newQuestionText.trim(),
        status: 'active',
      });
      setNewQuestionText('');
      await fetchProjectData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error adding question');
    } finally {
      setIsSubmittingQuestion(false);
    }
  };

  const handleUpdateProject = async (id: string, payload: UpdateProjectPayload) => {
    await api.updateProject(id, payload);
    await fetchProjectData();
  };

  const handleDeleteProject = () => {
    if (!project) return;
    setDeleteModalConfig({
      isOpen: true,
      title: `Delete Workspace "${project.name}"?`,
      message: `Are you sure you want to permanently delete this research workspace?`,
      warningNote: `This will permanently remove the workspace entity along with all questions, runs, and evidence links.`,
      onConfirm: async () => {
        try {
          setIsDeleting(true);
          await api.deleteProject(project.id);
          setDeleteModalConfig((prev) => ({ ...prev, isOpen: false }));
          onBack();
        } catch (err) {
          alert(err instanceof Error ? err.message : 'Failed to delete workspace');
        } finally {
          setIsDeleting(false);
        }
      },
    });
  };

  const handleUpdateQuestion = async (questionId: string, payload: UpdateQuestionPayload) => {
    await api.updateQuestion(questionId, payload);
    await fetchProjectData();
  };

  const handleDeleteQuestion = (q: ResearchQuestion) => {
    setDeleteModalConfig({
      isOpen: true,
      title: `Delete Research Question?`,
      message: `Are you sure you want to delete question: "${q.question}"?`,
      warningNote: `All execution runs and evidence links for this question will be deleted.`,
      onConfirm: async () => {
        try {
          setIsDeleting(true);
          await api.deleteQuestion(q.id);
          setDeleteModalConfig((prev) => ({ ...prev, isOpen: false }));
          await fetchProjectData();
        } catch (err) {
          alert(err instanceof Error ? err.message : 'Failed to delete question');
        } finally {
          setIsDeleting(false);
        }
      },
    });
  };

  const handleDeleteRun = (runId: string) => {
    setDeleteModalConfig({
      isOpen: true,
      title: `Delete Research Run?`,
      message: `Are you sure you want to delete run ${runId.substring(0, 8)}?`,
      warningNote: `This run's trace log and findings will be permanently removed.`,
      onConfirm: async () => {
        try {
          setIsDeleting(true);
          await api.deleteRun(runId);
          setDeleteModalConfig((prev) => ({ ...prev, isOpen: false }));
          await fetchProjectData();
        } catch (err) {
          alert(err instanceof Error ? err.message : 'Failed to delete run');
        } finally {
          setIsDeleting(false);
        }
      },
    });
  };

  const handleTriggerRunAndExecute = async (questionId: string) => {
    try {
      const newRun = await api.createRun(questionId, { triggered_by: 'frontend_user' });
      setExecutingRunId(newRun.id);
      await api.executeRun(newRun.id);
      await fetchProjectData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error executing research run');
    } finally {
      setExecutingRunId(null);
    }
  };

  if (loading && !project) {
    return <div className="py-20 text-center text-[#9CA3AF] text-xs font-mono">Loading workspace details...</div>;
  }

  if (error || !project) {
    return (
      <div className="space-y-4 max-w-2xl font-mono">
        <button onClick={onBack} className="text-xs text-[#EA580C] hover:underline cursor-pointer">
          ← Back to Workspaces
        </button>
        <div className="p-4 bg-[#EF4444]/10 border border-[#EF4444]/25 rounded text-[#EF4444] text-xs">
          {error || 'Workspace not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 font-mono">
      {/* Header Breadcrumbs & Overview */}
      <div>
        <button
          onClick={onBack}
          className="text-xs text-[#EA580C] hover:underline font-mono font-semibold transition-colors mb-3 inline-flex items-center gap-1 cursor-pointer"
        >
          ← Back to Workspaces
        </button>
        <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-6 shadow-xl space-y-3 relative overflow-hidden">
          <div className="absolute top-0 left-0 bottom-0 w-1 bg-[#EA580C]" />
          <div className="flex flex-wrap items-center justify-between gap-3 pl-2">
            <h1 className="text-2xl font-bold text-white font-sans">{project.name}</h1>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 bg-[#10B981]/10 border border-[#10B981]/25 text-[#10B981] rounded text-[10px] font-bold uppercase tracking-wider">
                {project.status}
              </span>
              <button
                onClick={() => setIsEditProjectOpen(true)}
                className="px-2.5 py-1 bg-[#12151A] hover:bg-[#262A33] border border-[#262A33] text-white rounded text-xs transition-colors cursor-pointer"
              >
                ✏️ Edit
              </button>
              <button
                onClick={handleDeleteProject}
                className="px-2.5 py-1 bg-[#EF4444]/10 hover:bg-[#EF4444]/25 border border-[#EF4444]/30 text-[#EF4444] rounded text-xs transition-colors cursor-pointer"
              >
                🗑️ Delete
              </button>
            </div>
          </div>
          <p className="text-[#FDBA74] text-xs pl-2">Topic: {project.research_topic}</p>
          {project.industry && (
            <p className="text-[#9CA3AF] text-xs pl-2">Industry Sector: {project.industry}</p>
          )}
          {project.description && (
            <p className="text-[#D1D5DB] text-xs border-t border-[#262A33] pt-3 leading-relaxed pl-2 font-sans">
              {project.description}
            </p>
          )}
        </div>
      </div>

      {/* Add New Question Section */}
      <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-6 shadow-xl space-y-4">
        <div>
          <span className="text-[10px] text-[#EA580C] uppercase font-bold tracking-wider">Research Console</span>
          <h2 className="text-base font-bold text-white font-sans mt-0.5">Submit Research Question</h2>
          <p className="text-[#9CA3AF] text-xs mt-0.5 font-sans">
            Enter an enterprise research inquiry to initialize research runs and multi-source evidence acquisition.
          </p>
        </div>
        <form onSubmit={handleCreateQuestion} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            required
            placeholder="e.g. How is AI transforming retail store operations and inventory management?"
            value={newQuestionText}
            onChange={(e) => setNewQuestionText(e.target.value)}
            className="flex-1 px-3.5 py-2.5 bg-[#12151A] border border-[#262A33] rounded focus:outline-none focus:border-[#EA580C] text-[#F9FAFB] text-xs placeholder-[#6B7280]"
          />
          <button
            type="submit"
            disabled={isSubmittingQuestion}
            className="px-4 py-2.5 bg-[#EA580C] hover:bg-[#C2410C] disabled:opacity-50 text-white text-xs font-semibold rounded transition-colors whitespace-nowrap shadow-sm cursor-pointer"
          >
            {isSubmittingQuestion ? 'Adding...' : '+ Add Question'}
          </button>
        </form>
      </div>

      {/* Research Questions & Runs List */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white tracking-tight font-sans">
            Research Questions ({questions.length})
          </h2>
          <span className="text-[11px] text-[#9CA3AF]">
            Traceable Intelligence Inquiries
          </span>
        </div>

        {questions.length === 0 ? (
          <div className="text-center py-12 bg-[#191C21] border border-[#262A33] rounded-lg text-[#9CA3AF] text-xs">
            No research questions submitted yet for this workspace.
          </div>
        ) : (
          questions.map((q) => {
            const runs = runsMap[q.id] || [];
            return (
              <div
                key={q.id}
                className="bg-[#191C21] border border-[#262A33] rounded-lg p-5 shadow-lg space-y-4 text-xs"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#262A33] pb-3">
                  <div className="space-y-1">
                    <h3 className="text-base font-bold text-white font-sans leading-snug">{q.question}</h3>
                    <p className="text-[11px] text-[#9CA3AF]">
                      Created {new Date(q.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 self-start md:self-auto">
                    <button
                      onClick={() => setEditingQuestion(q)}
                      className="px-2.5 py-1.5 bg-[#12151A] hover:bg-[#262A33] border border-[#262A33] text-white text-xs rounded transition-colors cursor-pointer"
                    >
                      ✏️ Edit
                    </button>
                    <button
                      onClick={() => handleDeleteQuestion(q)}
                      className="px-2.5 py-1.5 bg-[#EF4444]/10 hover:bg-[#EF4444]/25 border border-[#EF4444]/30 text-[#EF4444] text-xs rounded transition-colors cursor-pointer"
                    >
                      🗑️ Delete
                    </button>
                    <button
                      onClick={() => handleTriggerRunAndExecute(q.id)}
                      disabled={executingRunId !== null}
                      className="px-3.5 py-2 bg-[#EA580C] hover:bg-[#C2410C] disabled:opacity-50 text-white text-xs font-semibold rounded transition-all whitespace-nowrap shadow-sm cursor-pointer"
                    >
                      RUN RESEARCH 🚀
                    </button>
                  </div>
                </div>

                {/* Runs list */}
                <div className="space-y-3">
                  <span className="text-[10px] font-bold text-[#9CA3AF] uppercase tracking-wider block">
                    Execution Runs ({runs.length})
                  </span>

                  {runs.length === 0 ? (
                    <p className="text-xs text-[#6B7280] italic">No research runs executed yet.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {runs.map((r) => (
                        <div
                          key={r.id}
                          className="bg-[#12151A] border border-[#262A33] rounded p-3.5 space-y-2.5"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2.5">
                              <span
                                className={`w-2 h-2 rounded-full ${
                                  r.status === 'completed'
                                    ? 'bg-[#10B981]'
                                    : r.status === 'running' || executingRunId === r.id
                                    ? 'bg-[#F59E0B] animate-spin'
                                    : r.status === 'queued'
                                    ? 'bg-[#F59E0B] animate-pulse'
                                    : 'bg-[#EF4444]'
                                }`}
                              />
                              <span className="text-[#F9FAFB] font-semibold">
                                Run {r.id.substring(0, 8)}
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                                  r.status === 'completed'
                                    ? 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/25'
                                    : r.status === 'running' || executingRunId === r.id
                                    ? 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/25'
                                    : r.status === 'queued'
                                    ? 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/25'
                                    : 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/25'
                                }`}
                              >
                                {executingRunId === r.id ? 'running...' : r.status}
                              </span>
                            </div>

                            <div className="flex items-center gap-2">
                              {r.status === 'completed' && (
                                <button
                                  onClick={() => onViewRunResults(r.id)}
                                  className="px-3 py-1 bg-[#191C21] hover:bg-[#22262D] text-[#EA580C] hover:text-white rounded border border-[#262A33] text-[11px] font-semibold transition-all cursor-pointer"
                                >
                                  View Evidence Results →
                                </button>
                              )}
                              <button
                                title="Delete Run"
                                onClick={() => handleDeleteRun(r.id)}
                                className="px-2 py-1 text-[#9CA3AF] hover:text-[#EF4444] transition-colors cursor-pointer text-xs"
                              >
                                🗑️
                              </button>
                            </div>
                          </div>

                          {/* Counts summary bar */}
                          {r.counts && (
                            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 bg-[#191C21] p-2 rounded border border-[#262A33] text-center text-[10px]">
                              <div>
                                <span className="text-[#9CA3AF] block uppercase">Sub-Q</span>
                                <span className="text-[#F9FAFB] font-bold text-xs">{r.counts.sub_questions}</span>
                              </div>
                              <div>
                                <span className="text-[#9CA3AF] block uppercase">Sources</span>
                                <span className="text-[#06B6D4] font-bold text-xs">{r.counts.sources}</span>
                              </div>
                              <div>
                                <span className="text-[#9CA3AF] block uppercase">Findings</span>
                                <span className="text-[#FDBA74] font-bold text-xs">{r.counts.findings}</span>
                              </div>
                              <div>
                                <span className="text-[#9CA3AF] block uppercase">Evidence</span>
                                <span className="text-[#10B981] font-bold text-xs">{r.counts.evidence}</span>
                              </div>
                              <div>
                                <span className="text-[#9CA3AF] block uppercase">Conflicts</span>
                                <span className="text-[#F59E0B] font-bold text-xs">{r.counts.contradictions}</span>
                              </div>
                              <div>
                                <span className="text-[#9CA3AF] block uppercase">Conclusions</span>
                                <span className="text-[#EA580C] font-bold text-xs">{r.counts.conclusions}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Portaled Modals */}
      <EditProjectModal
        isOpen={isEditProjectOpen}
        project={project}
        onClose={() => setIsEditProjectOpen(false)}
        onSubmit={handleUpdateProject}
      />

      <EditQuestionModal
        isOpen={!!editingQuestion}
        question={editingQuestion}
        onClose={() => setEditingQuestion(null)}
        onSubmit={handleUpdateQuestion}
      />

      <DeleteConfirmModal
        isOpen={deleteModalConfig.isOpen}
        title={deleteModalConfig.title}
        message={deleteModalConfig.message}
        warningNote={deleteModalConfig.warningNote}
        isDeleting={isDeleting}
        onClose={() => setDeleteModalConfig((prev) => ({ ...prev, isOpen: false }))}
        onConfirm={deleteModalConfig.onConfirm}
      />
    </div>
  );
};
