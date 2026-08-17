import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { HealthStatus } from '../types';

export const HealthIndicator: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Offline');
      setHealth(null);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded border border-[#262A33] bg-[#191C21] text-[11px] font-mono tracking-wider">
      <div
        className={`w-2 h-2 rounded-full ${
          health && health.database.status === 'ok'
            ? 'bg-[#10B981] animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]'
            : 'bg-[#EF4444]'
        }`}
      />
      <span className="text-[#9CA3AF]">
        {health ? (
          <>
            API: <span className="text-[#F9FAFB] font-semibold">ONLINE</span> ({health.database.dialect})
          </>
        ) : (
          <span className="text-[#EF4444]">API: DISCONNECTED ({error || 'Failed to fetch'})</span>
        )}
      </span>
    </div>
  );
};
