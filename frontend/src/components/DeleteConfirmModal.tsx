import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

interface Props {
  isOpen: boolean;
  title: string;
  message: string;
  warningNote?: string;
  isDeleting?: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export const DeleteConfirmModal: React.FC<Props> = ({
  isOpen,
  title,
  message,
  warningNote,
  isDeleting = false,
  onClose,
  onConfirm,
}) => {
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

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-[#0E1013]/85 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isDeleting) onClose();
      }}
    >
      <div className="bg-[#191C21] border border-[#EF4444]/40 rounded-lg shadow-2xl max-w-md w-full p-6 text-[#F9FAFB] space-y-4 my-auto relative z-10 font-mono">
        <div className="flex justify-between items-center pb-2 border-b border-[#262A33]">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444] animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#EF4444]">
              Confirm Action
            </span>
          </div>
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="text-[#9CA3AF] hover:text-white transition-colors text-sm cursor-pointer p-1"
          >
            ✕
          </button>
        </div>

        <div className="space-y-2">
          <h3 className="text-base font-bold text-white font-sans">{title}</h3>
          <p className="text-xs text-[#9CA3AF] leading-relaxed font-sans">{message}</p>
          {warningNote && (
            <div className="p-3 bg-[#EF4444]/10 border border-[#EF4444]/25 rounded text-[#EF4444] text-[11px] font-mono leading-normal">
              ⚠️ {warningNote}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 pt-3 border-t border-[#262A33] text-xs">
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="px-3.5 py-1.5 text-[#9CA3AF] hover:text-white transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 bg-[#EF4444] hover:bg-[#DC2626] disabled:opacity-50 text-white font-bold rounded transition-colors shadow-sm cursor-pointer"
          >
            {isDeleting ? 'Deleting...' : 'Delete Permanently'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};
