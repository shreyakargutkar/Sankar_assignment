import React from 'react';
import { Award, CheckCircle2, Mail, Users } from 'lucide-react';
import { STATUS_CONFIG, LEAD_STATUSES } from '../utils/helpers';

const STAT_CARDS = [
  {
    title: 'Creators in pipeline',
    key: 'total_leads',
    icon: Users,
    description: 'Unique creator profiles',
  },
  {
    title: 'Profiles assessed',
    key: 'ai_analyzed',
    icon: Award,
    description: 'Campaign fit scores available',
  },
  {
    title: 'Contact details',
    key: 'emails_available',
    icon: Mail,
    description: 'Public business emails',
  },
  {
    title: 'Strong matches',
    key: 'high_suitability_matches',
    icon: CheckCircle2,
    description: 'Fit score of 80 or higher',
  },
];

export default function StatsOverview({ stats, currentStatusFilter, onSelectStatusFilter }) {
  if (!stats) return null;

  return (
    <section aria-label="Creator pipeline overview" className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        {STAT_CARDS.map(({ title, key, icon: Icon, description }) => (
          <article key={key} className="rounded-lg border border-[#e8dbd4] bg-[#fffaf3] px-4 py-3.5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[13px] font-medium text-[#82757a]">{title}</p>
                <p className="mt-1 text-[26px] leading-8 font-semibold tracking-tight text-[#30262e]">
                  {(stats[key] || 0).toLocaleString()}
                </p>
                <p className="mt-1 text-xs text-[#94868a]">{description}</p>
              </div>
              <div className="rounded-md bg-[#f4e7e2] p-2 text-[#806478]">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </div>
            </div>
          </article>
        ))}
      </div>

      <div className="rounded-lg border border-[#e8dbd4] bg-[#fffaf3] p-3.5">
        <div className="flex items-center justify-between gap-3 mb-2.5">
          <h2 className="text-xs font-semibold text-[#62545d]">Pipeline status</h2>
          {currentStatusFilter && (
            <button
              onClick={() => onSelectStatusFilter(null)}
              className="text-xs text-[#806478] hover:underline"
            >
              Clear filter
            </button>
          )}
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
          {LEAD_STATUSES.map((status) => {
            const config = STATUS_CONFIG[status];
            const isSelected = currentStatusFilter === status;
            return (
              <button
                key={status}
                onClick={() => onSelectStatusFilter(isSelected ? null : status)}
                aria-pressed={isSelected}
                className={`inline-flex items-center gap-2 whitespace-nowrap rounded-md border px-2.5 py-1.5 text-xs transition-colors ${
                  isSelected
                    ? 'border-[#b99ba8] bg-[#f3e5e3] text-[#604759]'
                    : 'border-[#ecdfd9] bg-[#fffdf9] text-[#75686e] hover:bg-[#f8f0e8]'
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
                <span>{status}</span>
                <span className="rounded bg-white/80 px-1.5 py-0.5 text-[10px] font-medium text-[#75686e]">
                  {stats.status_breakdown?.[status] || 0}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
