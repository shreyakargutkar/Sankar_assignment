import React, { useState } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { STATUS_CONFIG, LEAD_STATUSES } from '../utils/helpers';

export default function StatusBadge({ status, onStatusChange, isEditable = true }) {
  const [isOpen, setIsOpen] = useState(false);
  const config = STATUS_CONFIG[status] || STATUS_CONFIG['New Lead'];

  if (!isEditable) {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg} ${config.text} ${config.border}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`}></span>
        {status}
      </span>
    );
  }

  return (
    <div className="relative inline-block text-left">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors hover:brightness-[0.98] ${config.bg} ${config.text} ${config.border}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`}></span>
        <span>{status}</span>
        <ChevronDown className="w-3 h-3 opacity-60 ml-0.5" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(false);
            }}
          />
          <div className="absolute right-0 z-50 mt-1 w-52 rounded-lg bg-white border border-[#e1e7e3] shadow-xl p-1.5 text-xs focus:outline-none">
            <div className="px-2 py-1 text-[11px] font-semibold text-[#87928b] uppercase tracking-wide border-b border-[#edf0ee] mb-1">
              Change Lead Status
            </div>
            {LEAD_STATUSES.map((item) => {
              const itemConfig = STATUS_CONFIG[item];
              const isCurrent = item === status;
              return (
                <button
                  key={item}
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsOpen(false);
                    onStatusChange(item);
                  }}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left transition-colors ${
                    isCurrent
                      ? 'bg-[#edf4ef] text-[#315840] font-semibold'
                      : 'text-[#58665d] hover:bg-[#f4f7f5] hover:text-[#26342d]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${itemConfig.dot}`}></span>
                    <span>{item}</span>
                  </div>
                  {isCurrent && <Check className="w-3.5 h-3.5 text-[#52735f]" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
