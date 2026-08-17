import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ResearchProject, CreateProjectPayload } from '../types';
import { CreateProjectModal } from '../components/CreateProjectModal';

interface DashboardPageProps {
  onSelectProject: (projectId: string) => void;
  onOpenWorkspace: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onSelectProject,
  onOpenWorkspace,
}) => {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await api.listProjects();
      const seen = new Set<string>();
      const unique: ResearchProject[] = [];
      for (const p of data) {
        const key = p.name.trim().toLowerCase();
        if (!seen.has(key)) {
          seen.add(key);
          unique.push(p);
        }
      }
      setProjects(unique);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch workspaces');
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

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.research_topic.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.industry && p.industry.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="space-y-8">
      {/* Auralis-Inspired Editorial Header Banner */}
      <div className="bg-[#191C21] border border-[#262A33] rounded-lg p-8 shadow-xl space-y-6 relative overflow-hidden">
        <div className="absolute top-0 left-0 bottom-0 w-1 bg-[#EA580C]" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pl-2">
          <div className="max-w-2xl space-y-3 font-mono">
            <span className="text-[10px] font-bold uppercase tracking-widest text-[#EA580C] bg-[#EA580C]/10 px-2.5 py-1 rounded border border-[#EA580C]/20">
              MODUS RESEARCH AGENT • ENTERPRISE CONSOLE
            </span>
            <h1 className="text-3xl font-extrabold text-white tracking-tight font-sans sm:text-4xl">
              Research that can be traced.
            </h1>
            <p className="text-[#9CA3AF] text-xs font-sans leading-relaxed max-w-xl">
              Conduct enterprise research at scale with multi-source acquisition, atomic finding extraction, evidence linkage, and contradiction auditing.
            </p>
            <div className="flex items-center gap-2 text-[11px] text-[#FDBA74] pt-1">
              <span>Question</span>
              <span>→</span>
              <span>Evidence</span>
              <span>→</span>
              <span className="font-bold text-[#EA580C]">Intelligence</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 font-mono text-xs">
            <button
              onClick={onOpenWorkspace}
              className="px-4 py-2.5 bg-[#EA580C] hover:bg-[#C2410C] text-white font-semibold rounded transition-colors text-center shadow-sm"
            >
              LAUNCH RESEARCH PIPELINE
            </button>
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2.5 bg-[#12151A] hover:bg-[#22262D] border border-[#262A33] text-[#F9FAFB] font-semibold rounded transition-colors text-center"
            >
              + CREATE WORKSPACE
            </button>
          </div>
        </div>
      </div>

      {/* Filter and Search Section */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-[#262A33] pb-4 font-mono">
        <div>
          <h2 className="text-base font-bold text-white tracking-tight font-sans">
            Active Research Workspaces ({projects.length})
          </h2>
          <p className="text-[#9CA3AF] text-xs mt-0.5">Select a workspace entity to manage questions and research runs.</p>
        </div>

        <div className="w-full sm:w-72">
          <input
            type="text"
            placeholder="Search topic or industry..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-2 bg-[#12151A] border border-[#262A33] rounded text-[#F9FAFB] placeholder-[#6B7280] text-xs focus:outline-none focus:border-[#EA580C]"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-[#EF4444]/10 border border-[#EF4444]/25 rounded text-[#EF4444] text-xs font-mono">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-[#9CA3AF] text-xs font-mono">
          Loading enterprise research workspaces...
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="text-center py-16 bg-[#191C21] border border-[#262A33] rounded-lg p-8 space-y-3 font-mono">
          <div className="text-2xl">📁</div>
          <h3 className="text-sm font-bold text-white font-sans">No Workspaces Found</h3>
          <p className="text-[#9CA3AF] text-xs max-w-md mx-auto font-sans">
            {searchTerm ? 'No workspaces matching your search filter.' : 'Create your first enterprise research workspace to begin.'}
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 bg-[#EA580C] hover:bg-[#C2410C] text-white text-xs font-semibold rounded transition-colors"
          >
            Create Workspace
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              onClick={() => onSelectProject(project.id)}
              className="group bg-[#191C21] hover:bg-[#1E222A] border border-[#262A33] hover:border-[#EA580C]/40 rounded-lg p-5 shadow-md transition-all cursor-pointer flex flex-col justify-between space-y-4"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2 font-mono text-[10px]">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                      project.status === 'active'
                        ? 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/25'
                        : 'bg-[#262A33] text-[#9CA3AF] border border-[#363C4A]'
                    }`}
                  >
                    {project.status}
                  </span>
                  {project.industry && (
                    <span className="text-[#9CA3AF] truncate max-w-[130px]">
                      {project.industry}
                    </span>
                  )}
                </div>

                <h3 className="text-base font-bold text-white group-hover:text-[#EA580C] transition-colors">
                  {project.name}
                </h3>
                <p className="text-xs text-[#FDBA74] font-mono">
                  Topic: {project.research_topic}
                </p>
                {project.description && (
                  <p className="text-[#9CA3AF] text-xs line-clamp-2 leading-relaxed">
                    {project.description}
                  </p>
                )}
              </div>

              <div className="pt-3 border-t border-[#262A33] flex items-center justify-between text-xs text-[#9CA3AF] font-mono">
                <span>Created {new Date(project.created_at).toLocaleDateString()}</span>
                <span className="text-[#EA580C] font-semibold group-hover:translate-x-0.5 transition-transform">
                  Questions →
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
