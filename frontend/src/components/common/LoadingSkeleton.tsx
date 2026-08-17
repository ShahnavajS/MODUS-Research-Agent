import React from 'react';

export const LoadingSkeleton: React.FC<{ count?: number }> = ({ count = 3 }) => {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-20 bg-[#191C21] border border-[#262A33] rounded-lg p-4 flex flex-col justify-between"
        >
          <div className="h-3.5 bg-[#262A33] rounded w-1/3" />
          <div className="h-3 bg-[#262A33]/70 rounded w-3/4" />
          <div className="h-2.5 bg-[#262A33]/40 rounded w-1/4" />
        </div>
      ))}
    </div>
  );
};
