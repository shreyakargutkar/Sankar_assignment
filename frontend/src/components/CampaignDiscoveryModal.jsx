import React, { useState } from 'react';
import { X, Sparkles, Search, Sliders, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { NICHES } from '../utils/helpers';
import { api } from '../services/api';

export default function CampaignDiscoveryModal({ isOpen, onClose, onDiscoveryComplete }) {
  const [formData, setFormData] = useState({
    brand_name: 'FlowAI Systems',
    campaign_description: 'Launch of our automated workflow suite for creators and tech startups.',
    influencer_niche: 'Tech & AI',
    target_location: 'United States',
    min_followers: 10000,
    max_followers: 350000,
    relevant_keywords: 'ai tools, workflow automation, saas, productivity',
    auto_analyze_with_ai: true,
    limit: 6,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resultSummary, setResultSummary] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setResultSummary(null);

    try {
      const response = await api.discoverInfluencers({
        ...formData,
        min_followers: parseInt(formData.min_followers, 10),
        max_followers: parseInt(formData.max_followers, 10),
        limit: parseInt(formData.limit, 10),
      });

      setResultSummary(response);
      if (onDiscoveryComplete) {
        onDiscoveryComplete(response);
      }
    } catch (err) {
      setError(err.message || 'Discovery failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-850">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-600 text-white">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Influencer Research & Discovery</h2>
              <p className="text-xs text-slate-400">Identify, score and match high-performing creators for your campaign</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {resultSummary && (
            <div className="p-4 rounded-xl bg-purple-950/40 border border-purple-800/60 text-purple-200 text-xs space-y-2">
              <div className="flex items-center gap-2 font-semibold text-purple-300 text-sm">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                <span>Discovery Completed Successfully!</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center pt-2 border-t border-purple-800/40">
                <div className="bg-slate-900/60 p-2 rounded-lg">
                  <div className="text-lg font-bold text-white">{resultSummary.newly_added}</div>
                  <div className="text-[10px] text-slate-400">Newly Added Leads</div>
                </div>
                <div className="bg-slate-900/60 p-2 rounded-lg">
                  <div className="text-lg font-bold text-amber-400">{resultSummary.duplicates_skipped}</div>
                  <div className="text-[10px] text-slate-400">Duplicates Filtered</div>
                </div>
                <div className="bg-slate-900/60 p-2 rounded-lg">
                  <div className="text-lg font-bold text-emerald-400">{resultSummary.influencers?.length || 0}</div>
                  <div className="text-[10px] text-slate-400">Scored by Claude AI</div>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Brand Name */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Brand / Client Name *
              </label>
              <input
                type="text"
                required
                value={formData.brand_name}
                onChange={(e) => setFormData({ ...formData, brand_name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                placeholder="e.g. Acme Corp"
              />
            </div>

            {/* Influencer Niche */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Influencer Niche *
              </label>
              <select
                value={formData.influencer_niche}
                onChange={(e) => setFormData({ ...formData, influencer_niche: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-purple-500"
              >
                {NICHES.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Campaign Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Campaign Description & Goals *
            </label>
            <textarea
              required
              rows={2}
              value={formData.campaign_description}
              onChange={(e) => setFormData({ ...formData, campaign_description: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              placeholder="Explain the product, campaign message, target demographic, and key call-to-action..."
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Location */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Target Location *
              </label>
              <input
                type="text"
                value={formData.target_location}
                onChange={(e) => setFormData({ ...formData, target_location: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-purple-500"
                placeholder="e.g. United States or Global"
              />
            </div>

            {/* Min Followers */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Min Followers
              </label>
              <input
                type="number"
                min="1000"
                step="5000"
                value={formData.min_followers}
                onChange={(e) => setFormData({ ...formData, min_followers: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-purple-500"
              />
            </div>

            {/* Max Followers */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Max Followers
              </label>
              <input
                type="number"
                min="5000"
                step="10000"
                value={formData.max_followers}
                onChange={(e) => setFormData({ ...formData, max_followers: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          {/* Keywords */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Relevant Keywords (Comma-separated) *
            </label>
            <input
              type="text"
              required
              value={formData.relevant_keywords}
              onChange={(e) => setFormData({ ...formData, relevant_keywords: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              placeholder="e.g. ai tools, saas, workflow automation, python"
            />
          </div>

          {/* Options */}
          <div className="flex flex-wrap items-center justify-between pt-2 border-t border-slate-800 gap-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="auto_analyze"
                checked={formData.auto_analyze_with_ai}
                onChange={(e) => setFormData({ ...formData, auto_analyze_with_ai: e.target.checked })}
                className="w-4 h-4 rounded text-purple-600 bg-slate-800 border-slate-700 focus:ring-purple-500"
              />
              <label htmlFor="auto_analyze" className="text-xs text-slate-300 cursor-pointer">
                Automatically run <span className="text-purple-400 font-semibold">Claude AI analysis</span> & suitability scoring
              </label>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Discover batch:</span>
              <select
                value={formData.limit}
                onChange={(e) => setFormData({ ...formData, limit: e.target.value })}
                className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-white"
              >
                <option value="4">4 creators</option>
                <option value="6">6 creators</option>
                <option value="10">10 creators</option>
                <option value="15">15 creators</option>
              </select>
            </div>
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-sm font-semibold shadow-lg shadow-purple-600/30 transition-all disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Researching & Scoring...</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>Execute Research Run</span>
                </>
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}

