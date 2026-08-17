import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type {
  ResearchProject,
  ResearchQuestion,
  ResearchRun,
  UpdateProjectPayload,
  UpdateQuestionPayload,
  CreateProjectPayload,
} from '../types';
import { CreateProjectModal } from '../components/CreateProjectModal';
import { EditProjectModal } from '../components/EditProjectModal';
import { EditQuestionModal } from '../components/EditQuestionModal';
import { DeleteConfirmModal } from '../components/DeleteConfirmModal';

interface ResearchHistoryPageProps {
  onViewRunResults: (runId: string) => void;
}

interface QuestionWithRuns {
  question: ResearchQuestion;
  runs: ResearchRun[];
}

interface WorkspaceHierarchy {
  project: ResearchProject;
  questions: QuestionWithRuns[];
  totalRuns: number;
}

export const ResearchHistoryPage: React.FC<ResearchHistoryPageProps> = ({
  onViewRunResults,
}) => {
  const [workspaces, setWorkspaces] = useState<WorkspaceHierarchy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedWorkspaces, setExpandedWorkspaces] = useState<Record<string, boolean>>({});

  // Modals state
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<ResearchProject | null>(null);
  const [editingQuestion, setEditingQuestion] = useState<ResearchQuestion | null>(null);

  // New question inside workspace
  const [activeNewQuestionProjectId, setActiveNewQuestionProjectId] = useState<string | null>(null);
  const [newQuestionInput, setNewQuestionInput] = useState('');
  const [isCreatingQuestion, setIsCreatingQuestion] = useState(false);

  // Delete modal state
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

  const fetchHierarchy = async () => {
    try {
      setLoading(true);
      const projects = await api.listProjects();

      // Deduplicate projects by unique name
      const seenNames = new Set<string>();
      const uniqueProjects: ResearchProject[] = [];
      for (const p of projects) {
        const key = p.name.trim().toLowerCase();
        if (!seenNames.has(key)) {
          seenNames.add(key);
          uniqueProjects.push(p);
        }
      }

      const hierarchy: WorkspaceHierarchy[] = [];

      await Promise.all(
        uniqueProjects.map(async (project) => {
          try {
            const questions = await api.listQuestions(project.id);
            const questionsWithRuns: QuestionWithRuns[] = [];
            let projRunCount = 0;

            await Promise.all(
              questions.map(async (q) => {
                try {
                  const runs = await api.listRuns(q.id);
                  // Sort runs newest first
                  runs.sort(
                    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                  );
                  projRunCount += runs.length;
                  questionsWithRuns.push({ question: q, runs });
                } catch {
                  questionsWithRuns.push({ question: q, runs: [] });
                }
              })
            );

            // Sort questions newest first
            questionsWithRuns.sort(
              (a, b) =>
                new Date(b.question.created_at).getTime() -
                new Date(a.question.created_at).getTime()
            );

            hierarchy.push({
              project,
              questions: questionsWithRuns,
              totalRuns: projRunCount,
            });
          } catch {
            hierarchy.push({
              project,
              questions: [],
              totalRuns: 0,
            });
          }
        })
      );

      // Sort workspaces newest first
      hierarchy.sort(
        (a, b) =>
          new Date(b.project.created_at).getTime() - new Date(a.project.created_at).getTime()
      );

      setWorkspaces(hierarchy);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load research history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHierarchy();
  }, []);

  const toggleWorkspace = (projectId: string) => {
    setExpandedWorkspaces((prev) => ({
      ...prev,
      [projectId]: !prev[projectId],
    }));
  };

  const handleCreateProject = async (payload: CreateProjectPayload) => {
    await api.createProject(payload);
    await fetchHierarchy();
  };

  const handleUpdateProject = async (projectId: string, payload: UpdateProjectPayload) => {
    await api.updateProject(projectId, payload);
    await fetchHierarchy();
  };

  const handleDeleteProject = (project: ResearchProject) => {
    setDeleteModalConfig({
      isOpen: true,
      title: `Delete Workspace "${project.name}"?`,
      message: `Are you sure you want to permanently delete this research workspace?`,
      warningNote: `This will permanently remove the workspace entity along with all associated research questions, pipeline runs, findings, and evidence links.`,
      onConfirm: async () => {
        try {
          setIsDeleting(true);
          await api.deleteProject(project.id);
          setDeleteModalConfig((prev) => ({ ...prev, isOpen: false }));
          await fetchHierarchy();
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
    await fetchHierarchy();
  };

  const handleDeleteQuestion = (q: ResearchQuestion) => {
    setDeleteModalConfig({
      isOpen: true,
      title: `Delete Research Question?`,
      message: `Are you sure you want to delete this question: "${q.question}"?`,
      warningNote: `All associated research runs, extracted findings, and evidence links for this question will be permanently deleted.`,
      onConfirm: async () => {
        try {
          setIsDeleting(true);
          await api.deleteQuestion(q.id);
          setDeleteModalConfig((prev) => ({ ...prev, isOpen: false }));
          await fetchHierarchy();
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
      warningNote: `This run's trace log, extracted findings, and conclusion graph will be permanently removed.`,
      onConfirm: async () => {
        try {
          setIsDeleting(true);
          await api.deleteRun(runId);
          setDeleteModalConfig((prev) => ({ ...prev, isOpen: false }));
          await fetchHierarchy();
        } catch (err) {
          alert(err instanceof Error ? err.message : 'Failed to delete run');
        } finally {
          setIsDeleting(false);
        }
      },
    });
  };

  const handleAddQuestionSubmit = async (projectId: string) => {
    if (!newQuestionInput.trim()) return;
    try {
      setIsCreatingQuestion(true);
      await api.createQuestion(projectId, {
        question: newQuestionInput.trim(),
        status: 'active',
      });
      setNewQuestionInput('');
      setActiveNewQuestionProjectId(null);
      await fetchHierarchy();
      // Ensure workspace is expanded
      setExpandedWorkspaces((prev) => ({ ...prev, [projectId]: true }));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add question');
    } finally {
      setIsCreatingQuestion(false);
    }
  };

  // Filter workspaces by search term
  const filteredWorkspaces = workspaces.filter(({ project, questions }) => {
    const term = searchTerm.toLowerCase();
    const matchProj =
      project.name.toLowerCase().includes(term) ||
      project.research_topic.toLowerCase().includes(term) ||
      (project.industry && project.industry.toLowerCase().includes(term));
    const matchQ = questions.some((q) => q.question.question.toLowerCase().includes(term));
    return matchProj || matchQ;
  });

  const totalQuestionsCount = workspaces.reduce((acc, w) => acc + w.questions.length, 0);
  const totalRunsCount = workspaces.reduce((acc, w) => acc + w.totalRuns, 0);

  return (
    <div className="space-y-7 font-mono">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#262A33] pb-5">
        <div>
          <span className="text-[10px] text-[#EA580C] uppercase font-bold tracking-wider block">
            AUDIT TRAIL & WORKSPACE MANAGEMENT
          </span>
          <h1 className="text-2xl font-bold text-white tracking-tight font-sans mt-0.5">
            Traceability Audit History
          </h1>
          <p className="text-[#9CA3AF] text-xs font-sans mt-0.5">
            Hierarchical audit history organized by workspace entities, inquiry questions, and execution runs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-full sm:w-64">
            <input
              type="text"
              placeholder="Search workspaces & questions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 bg-[#12151A] border border-[#262A33] rounded text-[#F9FAFB] placeholder-[#6B7280] text-xs focus:outline-none focus:border-[#EA580C]"
            />
          </div>

          <button
            onClick={() => setIsCreateProjectOpen(true)}
            className="px-3.5 py-2 bg-[#EA580C] hover:bg-[#C2410C] text-white text-xs font-semibold rounded transition-colors whitespace-nowrap shadow-sm cursor-pointer"
          >
            + Create Workspace
          </button>
        </div>
      </div>

      {/* Summary Metrics Banner */}
      <div className="grid grid-cols-3 gap-3 bg-[#191C21] p-3.5 rounded-lg border border-[#262A33] text-center text-xs">
        <div>
          <span className="text-[#9CA3AF] text-[10px] block uppercase">Workspaces</span>
          <span className="text-white font-bold text-base font-sans">{workspaces.length}</span>
        </div>
        <div className="border-x border-[#262A33]">
          <span className="text-[#9CA3AF] text-[10px] block uppercase">Total Questions</span>
          <span className="text-[#FDBA74] font-bold text-base font-sans">{totalQuestionsCount}</span>
        </div>
        <div>
          <span className="text-[#9CA3AF] text-[10px] block uppercase">Execution Runs</span>
          <span className="text-[#10B981] font-bold text-base font-sans">{totalRunsCount}</span>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-[#EF4444]/10 border border-[#EF4444]/25 rounded text-[#EF4444] text-xs">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center text-[#9CA3AF] text-xs">
          Loading hierarchical workspace audit history...
        </div>
      ) : filteredWorkspaces.length === 0 ? (
        <div className="text-center py-16 bg-[#191C21] border border-[#262A33] rounded-lg p-8 space-y-3">
          <div className="text-2xl">📁</div>
          <h3 className="text-sm font-bold text-white font-sans">No Workspaces Found</h3>
          <p className="text-[#9CA3AF] text-xs font-sans max-w-md mx-auto">
            {searchTerm
              ? 'No workspaces or questions matching your search filter.'
              : 'Create your first research workspace to begin tracking questions and audit runs.'}
          </p>
          <button
            onClick={() => setIsCreateProjectOpen(true)}
            className="px-4 py-2 bg-[#EA580C] hover:bg-[#C2410C] text-white text-xs font-semibold rounded transition-colors cursor-pointer"
          >
            Create Workspace
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredWorkspaces.map(({ project, questions, totalRuns }) => {
            const isExpanded = !!expandedWorkspaces[project.id];
            return (
              <div
                key={project.id}
                className="bg-[#191C21] border border-[#262A33] hover:border-[#EA580C]/40 rounded-lg shadow-md transition-all overflow-hidden"
              >
                {/* Workspace Header Card */}
                <div
                  onClick={() => toggleWorkspace(project.id)}
                  className="p-4.5 cursor-pointer bg-[#191C21] hover:bg-[#1E222A] transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4 select-none"
                >
                  <div className="flex items-start gap-3.5">
                    {/* Expand/Collapse Chevron */}
                    <span className="w-5 h-5 flex items-center justify-center rounded bg-[#12151A] border border-[#262A33] text-[#EA580C] text-xs font-bold mt-0.5">
                      {isExpanded ? '▼' : '▶'}
                    </span>

                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2 text-[10px]">
                        <span className="text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded font-bold uppercase tracking-wider border border-[#10B981]/20">
                          {project.status}
                        </span>
                        {project.industry && (
                          <span className="text-[#9CA3AF] bg-[#12151A] px-2 py-0.5 rounded border border-[#262A33]">
                            {project.industry}
                          </span>
                        )}
                        <span className="text-[#6B7280]">•</span>
                        <span className="text-[#FDBA74] font-semibold">
                          Topic: {project.research_topic}
                        </span>
                      </div>

                      <h2 className="text-base font-bold text-white font-sans leading-snug">
                        {project.name}
                      </h2>

                      {project.description && (
                        <p className="text-[#9CA3AF] text-xs font-sans line-clamp-1">
                          {project.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Badges & Actions */}
                  <div className="flex items-center gap-3 self-end md:self-auto" onClick={(e) => e.stopPropagation()}>
                    {/* Question & Run Badges */}
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="px-2.5 py-1 rounded bg-[#12151A] border border-[#262A33] text-[#F9FAFB] font-semibold">
                        {questions.length} {questions.length === 1 ? 'Question' : 'Questions'}
                      </span>
                      <span className="px-2.5 py-1 rounded bg-[#12151A] border border-[#262A33] text-[#06B6D4] font-semibold">
                        {totalRuns} {totalRuns === 1 ? 'Run' : 'Runs'}
                      </span>
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center gap-1.5">
                      <button
                        title="Edit Workspace"
                        onClick={() => setEditingProject(project)}
                        className="px-2.5 py-1.5 bg-[#12151A] hover:bg-[#262A33] border border-[#262A33] text-[#F9FAFB] rounded text-xs transition-colors cursor-pointer"
                      >
                        ✏️ Edit
                      </button>
                      <button
                        title="Delete Workspace"
                        onClick={() => handleDeleteProject(project)}
                        className="px-2.5 py-1.5 bg-[#EF4444]/10 hover:bg-[#EF4444]/25 border border-[#EF4444]/30 text-[#EF4444] rounded text-xs transition-colors cursor-pointer"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded Question-Wise Tree */}
                {isExpanded && (
                  <div className="border-t border-[#262A33] bg-[#12151A]/60 p-5 space-y-4 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-[#EA580C] uppercase tracking-wider">
                        RESEARCH INQUIRIES ({questions.length})
                      </span>
                      <button
                        onClick={() => {
                          setActiveNewQuestionProjectId(
                            activeNewQuestionProjectId === project.id ? null : project.id
                          );
                        }}
                        className="text-[11px] text-[#FDBA74] hover:text-white transition-colors cursor-pointer flex items-center gap-1"
                      >
                        + Add Question to Workspace
                      </button>
                    </div>

                    {/* Inline Add Question Form */}
                    {activeNewQuestionProjectId === project.id && (
                      <div className="p-3.5 bg-[#191C21] border border-[#EA580C]/40 rounded-lg space-y-3 animate-fade-in">
                        <label className="block text-[10px] text-[#9CA3AF] uppercase font-bold tracking-wider">
                          New Research Question for {project.name}
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            placeholder="Enter enterprise research inquiry..."
                            value={newQuestionInput}
                            onChange={(e) => setNewQuestionInput(e.target.value)}
                            className="flex-1 px-3 py-2 bg-[#12151A] border border-[#262A33] rounded text-xs text-[#F9FAFB] placeholder-[#6B7280] focus:outline-none focus:border-[#EA580C]"
                          />
                          <button
                            onClick={() => handleAddQuestionSubmit(project.id)}
                            disabled={isCreatingQuestion || !newQuestionInput.trim()}
                            className="px-3.5 py-2 bg-[#EA580C] hover:bg-[#C2410C] disabled:opacity-50 text-white font-semibold text-xs rounded transition-colors cursor-pointer whitespace-nowrap"
                          >
                            {isCreatingQuestion ? 'Adding...' : 'Submit Question'}
                          </button>
                          <button
                            onClick={() => setActiveNewQuestionProjectId(null)}
                            className="px-3 py-2 bg-[#12151A] hover:bg-[#262A33] text-[#9CA3AF] text-xs rounded transition-colors cursor-pointer"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Questions List */}
                    {questions.length === 0 ? (
                      <div className="text-center py-6 text-[#9CA3AF] text-xs italic bg-[#191C21] rounded border border-[#262A33]">
                        No research questions in this workspace yet. Click "+ Add Question to Workspace" above.
                      </div>
                    ) : (
                      <div className="space-y-3.5">
                        {questions.map(({ question: q, runs }) => (
                          <div
                            key={q.id}
                            className="bg-[#191C21] border border-[#262A33] rounded-lg p-4 space-y-3 shadow-sm text-xs"
                          >
                            {/* Question Header */}
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#262A33] pb-2.5">
                              <div className="space-y-1">
                                <div className="flex items-center gap-2 text-[10px] text-[#9CA3AF]">
                                  <span className="text-[#10B981] font-semibold uppercase">{q.status}</span>
                                  <span>•</span>
                                  <span>Created {new Date(q.created_at).toLocaleDateString()}</span>
                                </div>
                                <h3 className="text-sm font-bold text-white font-sans leading-snug">
                                  {q.question}
                                </h3>
                              </div>

                              <div className="flex items-center gap-2">
                                <button
                                  title="Edit Question"
                                  onClick={() => setEditingQuestion(q)}
                                  className="px-2.5 py-1 bg-[#12151A] hover:bg-[#262A33] border border-[#262A33] text-[#F9FAFB] rounded text-[11px] transition-colors cursor-pointer"
                                >
                                  ✏️ Edit
                                </button>
                                <button
                                  title="Delete Question"
                                  onClick={() => handleDeleteQuestion(q)}
                                  className="px-2.5 py-1 bg-[#EF4444]/10 hover:bg-[#EF4444]/25 border border-[#EF4444]/30 text-[#EF4444] rounded text-[11px] transition-colors cursor-pointer"
                                >
                                  🗑️ Delete
                                </button>
                              </div>
                            </div>

                            {/* Runs list inside question */}
                            <div className="space-y-2">
                              <div className="text-[10px] text-[#9CA3AF] uppercase font-bold tracking-wider">
                                Execution Runs ({runs.length})
                              </div>

                              {runs.length === 0 ? (
                                <p className="text-[11px] text-[#6B7280] italic">No execution runs for this question yet.</p>
                              ) : (
                                <div className="space-y-2">
                                  {runs.map((r) => (
                                    <div
                                      key={r.id}
                                      className="bg-[#12151A] border border-[#262A33] rounded p-3 space-y-2"
                                    >
                                      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                                        <div className="flex items-center gap-2">
                                          <span className="text-[#F9FAFB] font-semibold">
                                            RUN {r.id.substring(0, 8)}
                                          </span>
                                          <span
                                            className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold tracking-wider ${
                                              r.status === 'completed'
                                                ? 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/25'
                                                : r.status === 'running'
                                                ? 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/25'
                                                : 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/25'
                                            }`}
                                          >
                                            {r.status}
                                          </span>
                                          <span className="text-[10px] text-[#9CA3AF]">
                                            {new Date(r.created_at).toLocaleString()}
                                          </span>
                                        </div>

                                        <div className="flex items-center gap-2">
                                          {r.status === 'completed' && (
                                            <button
                                              onClick={() => onViewRunResults(r.id)}
                                              className="px-3 py-1 bg-[#EA580C] hover:bg-[#C2410C] text-white rounded font-semibold text-[11px] transition-colors whitespace-nowrap shadow-sm cursor-pointer"
                                            >
                                              View Results →
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

                                      {/* Metrics row */}
                                      {r.counts && (
                                        <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5 bg-[#191C21] p-1.5 rounded border border-[#262A33] text-center text-[9px]">
                                          <div>
                                            <span className="text-[#9CA3AF] block">Sub-Q</span>
                                            <span className="text-[#F9FAFB] font-bold">{r.counts.sub_questions}</span>
                                          </div>
                                          <div>
                                            <span className="text-[#9CA3AF] block">Sources</span>
                                            <span className="text-[#06B6D4] font-bold">{r.counts.sources}</span>
                                          </div>
                                          <div>
                                            <span className="text-[#9CA3AF] block">Findings</span>
                                            <span className="text-[#FDBA74] font-bold">{r.counts.findings}</span>
                                          </div>
                                          <div>
                                            <span className="text-[#9CA3AF] block">Evidence</span>
                                            <span className="text-[#10B981] font-bold">{r.counts.evidence}</span>
                                          </div>
                                          <div>
                                            <span className="text-[#9CA3AF] block">Conflicts</span>
                                            <span className="text-[#F59E0B] font-bold">{r.counts.contradictions}</span>
                                          </div>
                                          <div>
                                            <span className="text-[#9CA3AF] block">Conclusion</span>
                                            <span className="text-[#EA580C] font-bold">{r.counts.conclusions}</span>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Portaled Modals */}
      <CreateProjectModal
        isOpen={isCreateProjectOpen}
        onClose={() => setIsCreateProjectOpen(false)}
        onSubmit={handleCreateProject}
      />

      <EditProjectModal
        isOpen={!!editingProject}
        project={editingProject}
        onClose={() => setEditingProject(null)}
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
