import React from 'react';

interface MetricCardProps {
  title: string;
  value: number | string;
  icon?: string;
  accentColor?: 'orange' | 'amber' | 'emerald' | 'cyan' | 'slate';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  icon,
  accentColor = 'orange',
}) => {
  const colorMap = {
    orange: 'text-[#EA580C] border-[#EA580C]/20 bg-[#EA580C]/5',
    amber: 'text-[#FDBA74] border-[#FDBA74]/20 bg-[#FDBA74]/5',
    emerald: 'text-[#10B981] border-[#10B981]/20 bg-[#10B981]/5',
    cyan: 'text-[#06B6D4] border-[#06B6D4]/20 bg-[#06B6D4]/5',
    slate: 'text-[#9CA3AF] border-[#262A33] bg-[#191C21]',
  };

  return (
    <div
      className={`border rounded-lg p-3.5 flex items-center justify-between shadow-sm transition-all ${colorMap[accentColor]}`}
    >
      <div>
        <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#9CA3AF] block">
          {title}
        </span>
        <span className="text-xl font-bold font-mono text-[#F9FAFB] mt-0.5 block">{value}</span>
      </div>
      {icon && <span className="text-base opacity-70 font-mono">{icon}</span>}
    </div>
  );
};
