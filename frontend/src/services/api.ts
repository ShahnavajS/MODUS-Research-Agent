import type {
  HealthStatus,
  ResearchProject,
  CreateProjectPayload,
  UpdateProjectPayload,
  ResearchQuestion,
  CreateQuestionPayload,
  UpdateQuestionPayload,
  ResearchRun,
  ResearchRunDetail,
  RunTraceability,
} from '../types';

function getApiBaseUrl(): string {
  let url = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').trim();
  url = url.replace(/\/+$/, '');
  if (!url.endsWith('/api/v1')) {
    url = `${url}/api/v1`;
  }
  return url;
}

const API_BASE_URL = getApiBaseUrl();

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail || `HTTP Error ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Health
  getHealth: (): Promise<HealthStatus> => request<HealthStatus>('/health'),

  // Projects
  listProjects: (): Promise<ResearchProject[]> => request<ResearchProject[]>('/projects'),
  getProject: (id: string): Promise<ResearchProject> => request<ResearchProject>(`/projects/${id}`),
  createProject: (payload: CreateProjectPayload): Promise<ResearchProject> =>
    request<ResearchProject>('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateProject: (id: string, payload: UpdateProjectPayload): Promise<ResearchProject> =>
    request<ResearchProject>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteProject: (id: string): Promise<void> =>
    request<void>(`/projects/${id}`, {
      method: 'DELETE',
    }),

  // Questions
  listQuestions: (projectId: string): Promise<ResearchQuestion[]> =>
    request<ResearchQuestion[]>(`/projects/${projectId}/questions`),
  getQuestion: (questionId: string): Promise<ResearchQuestion> =>
    request<ResearchQuestion>(`/questions/${questionId}`),
  createQuestion: (projectId: string, payload: CreateQuestionPayload): Promise<ResearchQuestion> =>
    request<ResearchQuestion>(`/projects/${projectId}/questions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateQuestion: (questionId: string, payload: UpdateQuestionPayload): Promise<ResearchQuestion> =>
    request<ResearchQuestion>(`/questions/${questionId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteQuestion: (questionId: string): Promise<void> =>
    request<void>(`/questions/${questionId}`, {
      method: 'DELETE',
    }),

  // Research Runs
  listRuns: (questionId: string): Promise<ResearchRun[]> =>
    request<ResearchRun[]>(`/questions/${questionId}/runs`),
  createRun: (questionId: string, metadata?: Record<string, unknown>): Promise<ResearchRun> =>
    request<ResearchRun>(`/questions/${questionId}/runs`, {
      method: 'POST',
      body: JSON.stringify({ metadata_json: metadata || {} }),
    }),
  getRun: (runId: string): Promise<ResearchRun> => request<ResearchRun>(`/runs/${runId}`),
  getRunDetails: (runId: string): Promise<ResearchRunDetail> =>
    request<ResearchRunDetail>(`/runs/${runId}/details`),
  getRunTraceability: (runId: string): Promise<RunTraceability> =>
    request<RunTraceability>(`/runs/${runId}/traceability`),
  executeRun: (runId: string): Promise<ResearchRun> =>
    request<ResearchRun>(`/runs/${runId}/execute`, {
      method: 'POST',
    }),
  deleteRun: (runId: string): Promise<void> =>
    request<void>(`/runs/${runId}`, {
      method: 'DELETE',
    }),
};
