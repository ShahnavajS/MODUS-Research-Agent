import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import type { ResearchProject, UpdateProjectPayload } from '../types';

interface Props {
  isOpen: boolean;
  project: ResearchProject | null;
  onClose: () => void;
  onSubmit: (projectId: string, payload: UpdateProjectPayload) => Promise<void>;
}

export const EditProjectModal: React.FC<Props> = ({ isOpen, project, onClose, onSubmit }) => {
  const [name, setName] = useState('');
  const [researchTopic, setResearchTopic] = useState('');
  const [industry, setIndustry] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (project) {
      setName(project.name);
      setResearchTopic(project.research_topic);
      setIndustry(project.industry || '');
      setDescription(project.description || '');
      setError(null);
    }
  }, [project]);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen || !project) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !researchTopic.trim()) {
      setError('Workspace Name and Research Topic are required.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmit(project.id, {
        name: name.trim(),
        research_topic: researchTopic.trim(),
        industry: industry.trim() || undefined,
        description: description.trim() || undefined,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update workspace.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-[#0E1013]/85 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-[#191C21] border border-[#262A33] rounded-lg shadow-2xl max-w-lg w-full p-6 text-[#F9FAFB] space-y-5 my-auto relative z-10">
        <div className="flex justify-between items-center pb-3 border-b border-[#262A33]">
          <div>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#EA580C]">
              Edit Workspace Entity
            </span>
            <h3 className="text-base font-bold text-white mt-0.5 font-sans">Edit Research Workspace</h3>
          </div>
          <button
            onClick={onClose}
            className="text-[#9CA3AF] hover:text-white transition-colors text-sm font-mono cursor-pointer p-1"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="p-3 bg-[#EF4444]/10 border border-[#EF4444]/25 rounded text-[#EF4444] text-xs font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs font-mono">
          <div>
            <label className="block font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1 text-[10px]">
              Workspace Name *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-[#12151A] border border-[#262A33] rounded focus:outline-none focus:border-[#EA580C] text-[#F9FAFB] placeholder-[#6B7280]"
            />
          </div>

          <div>
            <label className="block font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1 text-[10px]">
              Core Research Topic *
            </label>
            <input
              type="text"
              required
              value={researchTopic}
              onChange={(e) => setResearchTopic(e.target.value)}
              className="w-full px-3 py-2 bg-[#12151A] border border-[#262A33] rounded focus:outline-none focus:border-[#EA580C] text-[#F9FAFB] placeholder-[#6B7280]"
            />
          </div>

          <div>
            <label className="block font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1 text-[10px]">
              Industry Sector
            </label>
            <input
              type="text"
              placeholder="e.g. Finance & Banking"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="w-full px-3 py-2 bg-[#12151A] border border-[#262A33] rounded focus:outline-none focus:border-[#EA580C] text-[#F9FAFB] placeholder-[#6B7280]"
            />
          </div>

          <div>
            <label className="block font-semibold text-[#9CA3AF] uppercase tracking-wider mb-1 text-[10px]">
              Description
            </label>
            <textarea
              rows={3}
              placeholder="Brief summary of enterprise research goals..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-[#12151A] border border-[#262A33] rounded focus:outline-none focus:border-[#EA580C] text-[#F9FAFB] placeholder-[#6B7280] leading-relaxed font-sans text-xs"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-[#262A33]">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs text-[#9CA3AF] hover:text-white transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-xs bg-[#EA580C] hover:bg-[#C2410C] disabled:opacity-50 text-white font-semibold rounded transition-colors shadow-sm cursor-pointer"
            >
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
};
