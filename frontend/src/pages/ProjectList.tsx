import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ResearchProject, CreateProjectPayload } from '../types';
import { CreateProjectModal } from '../components/CreateProjectModal';

interface Props {
  onSelectProject: (projectId: string) => void;
}

export const ProjectList: React.FC<Props> = ({ onSelectProject }) => {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await api.listProjects();
      setProjects(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = async (payload: CreateProjectPayload) => {
    await api.createProject(payload);
    await fetchProjects();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Research Workspaces</h1>
          <p className="text-slate-400 text-sm mt-1">
            Enterprise research projects, traceable domain entities, and active knowledge runs.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg shadow-lg shadow-indigo-600/20 transition-colors"
        >
          <span>+</span> New Project
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-slate-500">
          Loading research workspaces...
        </div>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/50 border border-slate-800 rounded-xl p-8">
          <h3 className="text-lg font-medium text-slate-300">No Research Workspaces Found</h3>
          <p className="text-slate-500 text-sm mt-1 max-w-md mx-auto">
            Get started by creating your first enterprise research project or seed sample data.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Create First Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((project) => (
            <div
              key={project.id}
              onClick={() => onSelectProject(project.id)}
              className="group bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-5 shadow-lg transition-all cursor-pointer flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium uppercase tracking-wider ${
                      project.status === 'active'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : project.status === 'completed'
                        ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}
                  >
                    {project.status}
                  </span>
                  {project.industry && (
                    <span className="text-xs text-slate-500 truncate max-w-[120px]">
                      {project.industry}
                    </span>
                  )}
                </div>

                <h2 className="text-lg font-semibold text-white group-hover:text-indigo-400 transition-colors">
                  {project.name}
                </h2>
                <p className="text-xs text-indigo-300/80 font-medium mt-1">
                  Topic: {project.research_topic}
                </p>
                {project.description && (
                  <p className="text-slate-400 text-xs mt-2.5 line-clamp-2 leading-relaxed">
                    {project.description}
                  </p>
                )}
              </div>

              <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                <span>Created {new Date(project.created_at).toLocaleDateString()}</span>
                <span className="text-indigo-400 group-hover:translate-x-0.5 transition-transform">
                  View Questions →
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateProject}
      />
    </div>
  );
};
