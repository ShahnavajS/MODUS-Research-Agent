import React from 'react';

interface BadgeProps {
  label: string;
  variant?: 'status' | 'type' | 'importance' | 'severity';
  value?: string | number;
}

export const Badge: React.FC<BadgeProps> = ({ label, variant = 'status', value }) => {
  let colorStyle = 'bg-[#262A33] text-[#9CA3AF] border-[#363C4A]';
  const valStr = String(value || label).toLowerCase();

  if (variant === 'status') {
    if (valStr === 'completed' || valStr === 'active' || valStr === 'resolved') {
      colorStyle = 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/25';
    } else if (valStr === 'running' || valStr === 'queued' || valStr === 'pending' || valStr === 'reviewed') {
      colorStyle = 'bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/25';
    } else if (valStr === 'failed' || valStr === 'unresolved') {
      colorStyle = 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/25';
    }
  } else if (variant === 'importance' || variant === 'severity') {
    if (valStr === 'high' || valStr === 'critical') {
      colorStyle = 'bg-[#EA580C]/15 text-[#EA580C] border-[#EA580C]/30';
    } else if (valStr === 'medium') {
      colorStyle = 'bg-[#FDBA74]/10 text-[#FDBA74] border-[#FDBA74]/25';
    } else {
      colorStyle = 'bg-[#9CA3AF]/10 text-[#9CA3AF] border-[#9CA3AF]/20';
    }
  } else if (variant === 'type') {
    if (valStr === 'fact') colorStyle = 'bg-[#06B6D4]/10 text-[#06B6D4] border-[#06B6D4]/25';
    else if (valStr === 'risk') colorStyle = 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/25';
    else if (valStr === 'opportunity' || valStr === 'trend') colorStyle = 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/25';
    else colorStyle = 'bg-[#FDBA74]/10 text-[#FDBA74] border-[#FDBA74]/25';
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase tracking-wider border ${colorStyle}`}
    >
      {label}
    </span>
  );
};
