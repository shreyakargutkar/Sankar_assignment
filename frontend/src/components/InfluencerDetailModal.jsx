import React, { useState } from 'react';
import { X, ExternalLink, Mail, Copy, Check, Sparkles, MapPin, Users, Award, ShieldAlert, RefreshCw, Loader2 } from 'lucide-react';
import { formatFollowers, getScoreBadge } from '../utils/helpers';
import StatusBadge from './StatusBadge';
import { api } from '../services/api';

export default function InfluencerDetailModal({
  influencer,
  isOpen,
  onClose,
  onStatusUpdate,
  onInfluencerUpdated
}) {
  const [copied, setCopied] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [brandName, setBrandName] = useState(influencer?.campaign_name || 'My Brand');
  const [campaignDesc, setCampaignDesc] = useState('Product launch and authentic influencer partnership outreach.');

  if (!isOpen || !influencer) return null;

  const scoreBadge = getScoreBadge(influencer.suitability_score);

  const copyEmail = () => {
    if (influencer.email) {
      navigator.clipboard.writeText(influencer.email);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRunAIAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const response = await api.batchAnalyzeAI({
        influencer_ids: [influencer.id],
        brand_name: brandName,
        campaign_description: campaignDesc,
        relevant_keywords: influencer.niche,
      });

      if (response?.results?.[0]) {
        const updated = await api.getInfluencer(influencer.id);
        if (onInfluencerUpdated) {
          onInfluencerUpdated(updated);
        }
      }
    } catch (err) {
      alert(`AI Analysis failed: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        
        {/* Top Header */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-slate-800 bg-slate-850">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-purple-600 via-pink-600 to-amber-500 p-0.5 shadow-lg shadow-purple-500/20">
              <div className="w-full h-full rounded-2xl bg-slate-900 flex items-center justify-center text-xl font-bold text-white">
                {influencer.name.charAt(0)}
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-white tracking-tight">{influencer.name}</h2>
                <a
                  href={influencer.profile_url}
                  target="_blank"
                  rel="noreferrer"
                  className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                  title="View Instagram Profile"
                >
                  <ExternalLink className="w-4 h-4 text-purple-400" />
                </a>
              </div>
              <p className="text-sm text-purple-400 font-mono">@{influencer.instagram_username}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <StatusBadge
              status={influencer.status}
              onStatusChange={(newStatus) => onStatusUpdate(influencer.id, newStatus)}
            />
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          
          {/* Key Metrics Strip */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Followers</span>
              <div className="flex items-center gap-1.5 mt-1">
                <Users className="w-4 h-4 text-purple-400" />
                <span className="text-base font-bold text-white">{formatFollowers(influencer.followers_count)}</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Niche</span>
              <span className="text-sm font-semibold text-white mt-1 block truncate">{influencer.niche}</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-800/70 border border-slate-700/60">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Location</span>
              <div className="flex items-center gap-1.5 mt-1">
                <MapPin className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-semibold text-white truncate">{influencer.location}</span>
              </div>
            </div>
          </div>

          {/* Business Email Outreach Section */}
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/80 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-sky-950/60 text-sky-400 border border-sky-800/50">
                <Mail className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs text-slate-400 uppercase tracking-wider font-medium">Public Business Email</span>
                <p className="text-sm font-mono text-white font-medium">
                  {influencer.email ? influencer.email : <span className="text-slate-500 italic">No public email provided</span>}
                </p>
              </div>
            </div>

            {influencer.email && (
              <button
                onClick={copyEmail}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}
          </div>

          {/* Claude AI Suitability & Analysis Card */}
          <div className="rounded-xl border border-purple-500/40 bg-gradient-to-br from-purple-950/30 via-slate-900 to-slate-900 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-400" />
                <h3 className="text-base font-bold text-white">Claude AI Evaluation</h3>
                {influencer.category && (
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-900/50 text-purple-300 border border-purple-700/50 font-medium">
                    {influencer.category}
                  </span>
                )}
              </div>

              {influencer.suitability_score !== null && (
                <div className={`px-3 py-1 rounded-full text-xs font-bold ${scoreBadge.class}`}>
                  {scoreBadge.text}
                </div>
              )}
            </div>

            {/* Score progress bar */}
            {influencer.suitability_score !== null ? (
              <div className="space-y-1">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Match Suitability Score</span>
                  <span className="font-bold text-white">{influencer.suitability_score} / 100</span>
                </div>
                <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${scoreBadge.barColor}`}
                    style={{ width: `${influencer.suitability_score}%` }}
                  ></div>
                </div>
              </div>
            ) : null}

            {/* AI Summary */}
            {influencer.profile_summary ? (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Creator Summary</span>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/70 p-3 rounded-lg border border-slate-800">
                  {influencer.profile_summary}
                </p>
              </div>
            ) : null}

            {/* Match Reason */}
            {influencer.match_reason ? (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Campaign Fit Rationale</span>
                <p className="text-xs text-purple-200/90 leading-relaxed bg-purple-950/20 p-3 rounded-lg border border-purple-800/40">
                  {influencer.match_reason}
                </p>
              </div>
            ) : null}

            {/* Run AI Analysis Form / Re-run */}
            <div className="pt-2 border-t border-slate-800/80">
              <button
                onClick={handleRunAIAnalysis}
                disabled={isAnalyzing}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-md shadow-purple-600/20 transition-all disabled:opacity-50"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Analyzing with Claude AI...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>{influencer.suitability_score ? 'Re-Analyze with Claude AI' : 'Run Claude AI Profile Analysis'}</span>
                  </>
                )}
              </button>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}

