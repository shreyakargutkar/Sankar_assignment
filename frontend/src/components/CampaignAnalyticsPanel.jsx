import React, { useEffect, useState } from 'react';
import { BarChart3, Loader2, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

const METRICS = [
  ['total_influencers_researched', 'Influencers researched'],
  ['qualified_influencers', 'Qualified influencers'],
  ['emails_sent', 'Emails sent'],
  ['emails_delivered', 'Emails delivered'],
  ['replies_received', 'Replies received'],
  ['interested_influencers', 'Interested'],
  ['not_interested_influencers', 'Not interested'],
  ['collaboration_confirmations', 'Collaborations confirmed'],
];

export default function CampaignAnalyticsPanel({ campaignId }) {
  const [analytics, setAnalytics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError('');
    api.getCampaignAnalytics(campaignId)
      .then((result) => {
        if (active) setAnalytics(result);
      })
      .catch((loadError) => {
        if (active) setError(loadError.message || 'Could not load campaign analytics.');
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => { active = false; };
  }, [campaignId]);

  if (isLoading) {
    return <div className="flex-1 flex items-center justify-center text-indigo-300"><Loader2 className="w-5 h-5 animate-spin" /></div>;
  }

  if (error) {
    return <div role="alert" className="flex-1 p-6 text-sm text-rose-300">{error}</div>;
  }

  return (
    <div className="flex-1 overflow-y-auto p-5">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-4 h-4 text-indigo-300" />
        <div>
          <h3 className="text-sm font-bold text-white">Campaign analytics</h3>
          <p className="text-[11px] text-slate-400">{campaignId ? 'Selected campaign' : 'All campaigns'}</p>
        </div>
        <button
          onClick={() => {
            setIsLoading(true);
            api.getCampaignAnalytics(campaignId)
              .then(setAnalytics)
              .catch((loadError) => setError(loadError.message || 'Could not refresh analytics.'))
              .finally(() => setIsLoading(false));
          }}
          className="ml-auto p-2 rounded-lg bg-slate-800 text-slate-300"
          aria-label="Refresh campaign analytics"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {METRICS.map(([key, label]) => {
          const value = analytics?.[key];
          return (
            <div key={key} className="rounded-xl border border-slate-800 bg-slate-800/40 p-4">
              <p className="text-xs text-slate-400">{label}</p>
              <p className="text-2xl font-bold text-white mt-1">
                {value === null || value === undefined ? '—' : Number(value).toLocaleString()}
              </p>
              {key === 'emails_delivered' && (
                <p className="text-[10px] text-slate-500 mt-1">
                  {analytics?.delivery_information_available
                    ? 'Reported by available mail delivery events'
                    : 'Gmail API does not expose a delivery receipt for this send'}
                </p>
              )}
            </div>
          );
        })}
        <div className="rounded-xl border border-indigo-900/70 bg-indigo-950/30 p-4">
          <p className="text-xs text-indigo-200">Reply rate</p>
          <p className="text-2xl font-bold text-white mt-1">
            {((analytics?.reply_rate || 0) * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] text-slate-500 mt-1">Influencers who replied ÷ initial emails sent</p>
        </div>
      </div>
      <p className="mt-4 text-[11px] text-slate-500">
        Qualified means a Claude suitability score of 70 or higher. Delivery is reported as unavailable unless the mail provider supplies delivery events.
      </p>
    </div>
  );
}
