import { useState } from 'react';
import { MainLayout } from './layouts/MainLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { ResearchWorkspacePage } from './pages/ResearchWorkspacePage';
import { ResearchResultsPage } from './pages/ResearchResultsPage';
import { ResearchHistoryPage } from './pages/ResearchHistoryPage';

export function App() {
  const [activeTab, setActiveTab] = useState<'projects' | 'workspace' | 'history' | 'results'>('projects');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const handleSelectProject = (projectId: string) => {
    setSelectedProjectId(projectId);
    setSelectedRunId(null);
    setActiveTab('projects');
  };

  const handleViewRunResults = (runId: string) => {
    setSelectedRunId(runId);
    setActiveTab('results');
  };

  return (
    <MainLayout activeTab={activeTab} setActiveTab={setActiveTab}>
      {activeTab === 'projects' && (
        selectedProjectId ? (
          <ProjectDetailPage
            projectId={selectedProjectId}
            onBack={() => setSelectedProjectId(null)}
            onViewRunResults={handleViewRunResults}
          />
        ) : (
          <DashboardPage
            onSelectProject={handleSelectProject}
            onOpenWorkspace={() => setActiveTab('workspace')}
          />
        )
      )}

      {activeTab === 'workspace' && (
        <ResearchWorkspacePage onViewRunResults={handleViewRunResults} />
      )}

      {activeTab === 'results' && selectedRunId && (
        <ResearchResultsPage
          runId={selectedRunId}
          onBack={() => {
            if (selectedProjectId) {
              setActiveTab('projects');
            } else {
              setActiveTab('history');
            }
          }}
        />
      )}

      {activeTab === 'history' && (
        <ResearchHistoryPage onViewRunResults={handleViewRunResults} />
      )}
    </MainLayout>
  );
}

export default App;
