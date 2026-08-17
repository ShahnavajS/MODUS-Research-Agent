import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { api } from '../services/api';

export const PIPELINE_STEPS = [
  '01 QUESTION • INITIALIZING RESEARCH BOUNDARY',
  '02 DECOMPOSITION • GENERATING TARGETED SUB-INQUIRIES',
  '03 SOURCE DISCOVERY • INDEXING & DEDUPLICATING DOMAIN SOURCES',
  '04 CONTENT ANALYSIS • EXTRACTING DOCUMENT TEXT & SHA256 HASHES',
  '05 FINDINGS • STRUCTURING ATOMIC INSIGHT CANDIDATES',
  '06 EVIDENCE • LINKING DIRECT TEXT EXCERPTS & RELEVANCE SCORES',
  '07 CONTRADICTIONS • AUDITING CONFLICTING EVIDENCE & SEVERITY',
  '08 SYNTHESIS • GENERATING TRACEABLE CONCLUSION GRAPH',
];

const STAGE_SCHEDULE = [
  { step: 1, atMs: 1500 },
  { step: 2, atMs: 7000 },
  { step: 3, atMs: 18000 },
  { step: 4, atMs: 38000 },
  { step: 5, atMs: 58000 },
  { step: 6, atMs: 75000 },
  { step: 7, atMs: 90000 },
];

interface ResearchContextType {
  isRunning: boolean;
  activeRunId: string | null;
  activeQuestionId: string | null;
  activeProjectId: string | null;
  activeQuestionText: string;
  activeProjectName: string;
  stepIndex: number;
  elapsedSeconds: number;
  error: string | null;
  isCompleted: boolean;
  completedRunId: string | null;
  pipelineSteps: string[];
  startResearch: (projectId: string, questionText: string, projectName?: string) => Promise<string | null>;
  resetResearch: () => void;
  dismissCompleted: () => void;
}

const ResearchContext = createContext<ResearchContextType | undefined>(undefined);

export const ResearchProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeQuestionText, setActiveQuestionText] = useState('');
  const [activeProjectName, setActiveProjectName] = useState('');
  const [stepIndex, setStepIndex] = useState<number>(-1);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [completedRunId, setCompletedRunId] = useState<string | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number | null>(null);

  const cleanupTimers = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  useEffect(() => {
    return () => cleanupTimers();
  }, []);

  const resetResearch = () => {
    cleanupTimers();
    setIsRunning(false);
    setActiveRunId(null);
    setActiveQuestionId(null);
    setStepIndex(-1);
    setElapsedSeconds(0);
    setError(null);
    setIsCompleted(false);
    setCompletedRunId(null);
  };

  const dismissCompleted = () => {
    setIsCompleted(false);
  };

  const startResearch = async (
    projectId: string,
    questionText: string,
    projectName: string = ''
  ): Promise<string | null> => {
    try {
      cleanupTimers();
      setIsRunning(true);
      setError(null);
      setIsCompleted(false);
      setCompletedRunId(null);
      setActiveProjectId(projectId);
      setActiveProjectName(projectName);
      setActiveQuestionText(questionText);
      setStepIndex(0);
      setElapsedSeconds(0);
      startTimeRef.current = Date.now();

      // 1. Create question in backend
      const qObj = await api.createQuestion(projectId, {
        question: questionText.trim(),
        status: 'active',
      });
      setActiveQuestionId(qObj.id);

      // 2. Create run in backend
      setStepIndex(1);
      const runObj = await api.createRun(qObj.id, { mode: 'workspace_console' });
      setActiveRunId(runObj.id);

      // 3. Start elapsed timer and stage advancement timer
      timerRef.current = setInterval(() => {
        if (startTimeRef.current) {
          const elapsed = Date.now() - startTimeRef.current;
          setElapsedSeconds(Math.floor(elapsed / 1000));
          for (let i = STAGE_SCHEDULE.length - 1; i >= 0; i--) {
            if (elapsed >= STAGE_SCHEDULE[i].atMs) {
              setStepIndex((prev) => Math.max(prev, STAGE_SCHEDULE[i].step));
              break;
            }
          }
        }
      }, 1000);

      // 4. Fire execution API in background
      api.executeRun(runObj.id).then((completedRun) => {
        if (completedRun.status === 'completed') {
          cleanupTimers();
          setStepIndex(PIPELINE_STEPS.length - 1);
          setIsRunning(false);
          setIsCompleted(true);
          setCompletedRunId(runObj.id);
        } else if (completedRun.status === 'failed') {
          cleanupTimers();
          setIsRunning(false);
          setError(completedRun.error_message || 'Pipeline execution failed.');
          setStepIndex(-1);
        }
      }).catch(() => {
        // If direct execution connection timed out or dropped, let the polling check backend status
      });

      // 5. Setup polling in parallel to track run progress
      pollRef.current = setInterval(async () => {
        try {
          const updatedRun = await api.getRun(runObj.id);
          if (updatedRun.status === 'completed') {
            cleanupTimers();
            setStepIndex(PIPELINE_STEPS.length - 1);
            setIsRunning(false);
            setIsCompleted(true);
            setCompletedRunId(runObj.id);
          } else if (updatedRun.status === 'failed') {
            cleanupTimers();
            setIsRunning(false);
            setError(updatedRun.error_message || 'Pipeline execution failed.');
            setStepIndex(-1);
          }
        } catch {
          // Ignore transient network errors during poll
        }
      }, 2000);

      return runObj.id;
    } catch (err: unknown) {
      cleanupTimers();
      setIsRunning(false);
      setStepIndex(-1);
      const msg = err instanceof Error ? err.message : 'Failed to start research';
      setError(msg);
      throw err;
    }
  };

  return (
    <ResearchContext.Provider
      value={{
        isRunning,
        activeRunId,
        activeQuestionId,
        activeProjectId,
        activeQuestionText,
        activeProjectName,
        stepIndex,
        elapsedSeconds,
        error,
        isCompleted,
        completedRunId,
        pipelineSteps: PIPELINE_STEPS,
        startResearch,
        resetResearch,
        dismissCompleted,
      }}
    >
      {children}
    </ResearchContext.Provider>
  );
};

export const useResearch = () => {
  const context = useContext(ResearchContext);
  if (!context) {
    throw new Error('useResearch must be used within a ResearchProvider');
  }
  return context;
};
