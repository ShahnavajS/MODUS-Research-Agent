import React from 'react';
import { HealthIndicator } from '../components/HealthIndicator';

interface MainLayoutProps {
  children: React.ReactNode;
  activeTab: 'projects' | 'workspace' | 'history' | 'results';
  setActiveTab: (tab: 'projects' | 'workspace' | 'history' | 'results') => void;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children, activeTab, setActiveTab }) => {
  return (
    <div className="min-h-screen bg-[#12151A] text-[#F9FAFB] flex flex-col font-sans selection:bg-[#EA580C] selection:text-white bg-tech-grid">
      {/* Top Header Navigation */}
      <header className="sticky top-0 z-40 bg-[#191C21]/95 backdrop-blur-md border-b border-[#262A33] px-6 py-3.5 flex items-center justify-between shadow-lg">
        <div
          onClick={() => setActiveTab('projects')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="w-8 h-8 rounded bg-[#EA580C] flex items-center justify-center font-extrabold text-white text-base shadow-sm group-hover:bg-[#C2410C] transition-colors">
            M
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-[#F9FAFB] leading-none">
              MODUS <span className="text-[#EA580C] font-semibold">Research Agent</span>
            </h1>
            <p className="text-[10px] text-[#9CA3AF] font-mono tracking-widest mt-0.5 uppercase font-semibold">
              ENTERPRISE AI INTELLIGENCE
            </p>
          </div>
        </div>

        {/* Navigation Controls */}
        <nav className="hidden md:flex items-center gap-1 bg-[#12151A] p-1 rounded border border-[#262A33] text-xs font-mono">
          <button
            onClick={() => setActiveTab('projects')}
            className={`px-3.5 py-1.5 rounded text-[11px] font-semibold transition-all ${
              activeTab === 'projects'
                ? 'bg-[#EA580C] text-white shadow-sm'
                : 'text-[#9CA3AF] hover:text-[#F9FAFB] hover:bg-[#191C21]'
            }`}
          >
            WORKSPACES
          </button>
          <button
            onClick={() => setActiveTab('workspace')}
            className={`px-3.5 py-1.5 rounded text-[11px] font-semibold transition-all ${
              activeTab === 'workspace'
                ? 'bg-[#EA580C] text-white shadow-sm'
                : 'text-[#9CA3AF] hover:text-[#F9FAFB] hover:bg-[#191C21]'
            }`}
          >
            RESEARCH LAUNCHER
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3.5 py-1.5 rounded text-[11px] font-semibold transition-all ${
              activeTab === 'history'
                ? 'bg-[#EA580C] text-white shadow-sm'
                : 'text-[#9CA3AF] hover:text-[#F9FAFB] hover:bg-[#191C21]'
            }`}
          >
            AUDIT HISTORY
          </button>
        </nav>

        {/* Backend Health Status */}
        <HealthIndicator />
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 animate-fade-in">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#262A33] bg-[#191C21] py-3.5 px-6 text-center text-[11px] text-[#9CA3AF] font-mono flex items-center justify-between">
        <span>MODUS RESEARCH AGENT • ENTERPRISE AI INTELLIGENCE</span>
        <span>MODUS BUILD CHALLENGE ASSIGNMENT 9</span>
      </footer>
    </div>
  );
};
