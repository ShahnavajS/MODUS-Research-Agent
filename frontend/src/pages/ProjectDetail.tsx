import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ResearchProject, ResearchQuestion, ResearchRun } from '../types';

interface Props {
  projectId: string;
  onBack: () => void;
}

export const ProjectDetail: React.FC<Props> = ({ projectId, onBack }) => {
  const [project, setProject] = useState<ResearchProject | null>(null);
  const [questions, setQuestions] = useState<ResearchQuestion[]>([]);
  const [runsMap, setRunsMap] = useState<Record<string, ResearchRun[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [executingRunId, setExecutingRunId] = useState<string | null>(null);

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
            runsResults[q.id] = runs;
          } catch {
            runsResults[q.id] = [];
          }
        })
      );
      setRunsMap(runsResults);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load project details');
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

  const handleTriggerRun = async (questionId: string) => {
    try {
      const newRun = await api.createRun(questionId, { triggered_by: 'frontend_user' });
      // Automatically execute the queued run
      setExecutingRunId(newRun.id);
      await api.executeRun(newRun.id);
      await fetchProjectData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error executing research run');
    } finally {
      setExecutingRunId(null);
    }
  };

  const handleExecuteExistingRun = async (runId: string) => {
    try {
      setExecutingRunId(runId);
      await api.executeRun(runId);
      await fetchProjectData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error executing research run');
    } finally {
      setExecutingRunId(null);
    }
  };

  if (loading && !project) {
    return <div className="py-16 text-center text-slate-500">Loading project detail...</div>;
  }

  if (error || !project) {
    return (
      <div className="space-y-4">
        <button onClick={onBack} className="text-sm text-indigo-400 hover:underline">
          ← Back to Workspaces
        </button>
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300">
          {error || 'Project not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header & Navigation */}
      <div>
        <button
          onClick={onBack}
          className="text-sm text-indigo-400 hover:text-indigo-300 font-medium transition-colors mb-3 inline-flex items-center gap-1"
        >
          ← Back to Workspaces
        </button>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-2xl font-bold text-white">{project.name}</h1>
            <span className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full text-xs font-semibold uppercase">
              {project.status}
            </span>
          </div>
          <p className="text-indigo-400 text-sm font-medium mt-1">Topic: {project.research_topic}</p>
          {project.industry && (
            <p className="text-slate-400 text-xs mt-0.5">Industry: {project.industry}</p>
          )}
          {project.description && (
            <p className="text-slate-300 text-sm mt-3 leading-relaxed border-t border-slate-800 pt-3">
              {project.description}
            </p>
          )}
        </div>
      </div>

      {/* Add New Question Section */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-2">Submit Research Question</h2>
        <p className="text-slate-400 text-xs mb-4">
          Enter an enterprise research inquiry to trigger the multi-stage research pipeline.
        </p>
        <form onSubmit={handleCreateQuestion} className="flex gap-3">
          <input
            type="text"
            required
            placeholder="e.g. How is AI transforming retail store operations and inventory management?"
            value={newQuestionText}
            onChange={(e) => setNewQuestionText(e.target.value)}
            className="flex-1 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-lg focus:outline-none focus:border-indigo-500 text-slate-100 text-sm"
          />
          <button
            type="submit"
            disabled={isSubmittingQuestion}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
          >
            {isSubmittingQuestion ? 'Adding...' : 'Add Question'}
          </button>
        </form>
      </div>

      {/* Research Questions & Runs List */}
      <div className="space-y-6">
        <h2 className="text-xl font-bold text-white">Research Questions ({questions.length})</h2>

        {questions.length === 0 ? (
          <div className="text-center py-10 bg-slate-900/30 border border-slate-800/60 rounded-xl text-slate-500 text-sm">
            No research questions created yet for this project.
          </div>
        ) : (
          questions.map((q) => {
            const runs = runsMap[q.id] || [];
            return (
              <div
                key={q.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-base font-semibold text-white">{q.question}</h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Created {new Date(q.created_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleTriggerRun(q.id)}
                    disabled={executingRunId !== null}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-md transition-all self-start sm:self-auto"
                  >
                    🚀 Start & Execute Pipeline
                  </button>
                </div>

                {/* Research Runs List */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Pipeline Execution Runs ({runs.length})
                  </h4>
                  {runs.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No research runs executed yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {runs.map((r) => (
                        <div
                          key={r.id}
                          className="bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs space-y-3"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-3">
                              <span
                                className={`w-2.5 h-2.5 rounded-full ${
                                  r.status === 'completed'
                                    ? 'bg-emerald-400'
                                    : r.status === 'running' || executingRunId === r.id
                                    ? 'bg-blue-400 animate-spin'
                                    : r.status === 'queued'
                                    ? 'bg-amber-400 animate-pulse'
                                    : 'bg-rose-500'
                                }`}
                              />
                              <span className="font-mono text-slate-300 font-medium">Run {r.id.substring(0, 8)}</span>
                              <span
                                className={`px-2.5 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wider ${
                                  r.status === 'completed'
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : r.status === 'running' || executingRunId === r.id
                                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                    : r.status === 'queued'
                                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                }`}
                              >
                                {executingRunId === r.id ? 'running...' : r.status}
                              </span>
                            </div>

                            {r.status === 'queued' && executingRunId !== r.id && (
                              <button
                                onClick={() => handleExecuteExistingRun(r.id)}
                                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded border border-slate-700 font-medium text-[11px]"
                              >
                                Execute Now
                              </button>
                            )}
                          </div>

                          {/* Pipeline Entity Counts Badge Bar */}
                          {r.counts && (
                            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 bg-slate-900/80 p-2.5 rounded-md border border-slate-800/60 text-center font-mono">
                              <div>
                                <div className="text-slate-400 text-[10px]">Sub-Q</div>
                                <div className="text-indigo-400 font-bold text-sm">{r.counts.sub_questions}</div>
                              </div>
                              <div>
                                <div className="text-slate-400 text-[10px]">Sources</div>
                                <div className="text-indigo-400 font-bold text-sm">{r.counts.sources}</div>
                              </div>
                              <div>
                                <div className="text-slate-400 text-[10px]">Findings</div>
                                <div className="text-indigo-400 font-bold text-sm">{r.counts.findings}</div>
                              </div>
                              <div>
                                <div className="text-slate-400 text-[10px]">Evidence</div>
                                <div className="text-indigo-400 font-bold text-sm">{r.counts.evidence}</div>
                              </div>
                              <div>
                                <div className="text-slate-400 text-[10px]">Conflicts</div>
                                <div className="text-amber-400 font-bold text-sm">{r.counts.contradictions}</div>
                              </div>
                              <div>
                                <div className="text-slate-400 text-[10px]">Conclusions</div>
                                <div className="text-emerald-400 font-bold text-sm">{r.counts.conclusions}</div>
                              </div>
                            </div>
                          )}

                          {r.error_message && (
                            <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded text-rose-300 text-xs">
                              Failure Error: {r.error_message}
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
    </div>
  );
};
