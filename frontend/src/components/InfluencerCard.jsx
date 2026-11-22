import React from 'react';
import { ExternalLink, Mail, Users, MapPin, Sparkles, Trash2, Eye } from 'lucide-react';
import { formatFollowers, getScoreBadge } from '../utils/helpers';
import StatusBadge from './StatusBadge';

export default function InfluencerCard({
  influencer,
  isSelected,
  onToggleSelect,
  onViewDetails,
  onStatusChange,
  onDelete
}) {
  const scoreBadge = getScoreBadge(influencer.suitability_score);

  return (
    <div
      onClick={() => onViewDetails(influencer)}
      className={`relative p-5 rounded-xl border transition-all cursor-pointer overflow-hidden backdrop-blur-sm ${
        isSelected
          ? 'bg-[#f0f6f1] border-[#9cb4a2]'
            : 'bg-white hover:bg-[#fcfdfc] border-[#e1e7e3] hover:border-[#cbd6ce]'
      }`}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#e8f0eb] flex items-center justify-center font-semibold text-[#35644f]">
            {influencer.name.charAt(0)}
          </div>
          <div>
            <h4 className="font-semibold text-[#2e3b34] text-sm hover:text-[#35644f] transition-colors leading-tight">
              {influencer.name}
            </h4>
            <div className="flex items-center gap-1 text-xs text-[#829087] mt-0.5">
              <span>@{influencer.instagram_username}</span>
              <a
                href={influencer.profile_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-[#9aa49e] hover:text-[#35644f]"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>

        <div onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(influencer.id)}
            className="w-4 h-4 rounded text-[#35644f] border-[#cad4cd] focus:ring-[#52735f]"
          />
        </div>
      </div>

      {/* Meta Specs */}
      <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-[#edf0ee] text-xs">
        <div className="flex items-center gap-1.5 text-[#526057]">
          <Users className="w-3.5 h-3.5 text-[#829087]" />
          <span className="font-mono font-semibold">{formatFollowers(influencer.followers_count)}</span>
          <span className="text-[10px] text-[#929c95]">followers</span>
        </div>
        <div className="flex items-center gap-1.5 text-[#68756e] truncate">
          <MapPin className="w-3.5 h-3.5 text-[#829087] flex-shrink-0" />
          <span className="truncate">{influencer.location}</span>
        </div>
      </div>

      {/* Email pill */}
      <div className="mt-3">
        {influencer.email ? (
          <div className="flex items-center gap-1.5 text-[11px] text-[#536159] bg-[#f7faf8] border border-[#e6ece7] px-2 py-1.5 rounded-md truncate">
            <Mail className="w-3 h-3 text-[#829087] flex-shrink-0" />
            <span className="truncate">{influencer.email}</span>
          </div>
        ) : (
          <div className="text-[11px] text-[#929c95] italic px-1">
            No public email listed
          </div>
        )}
      </div>

      {/* Claude AI Suitability Score & Summary */}
      <div className="mt-3.5 pt-3 border-t border-[#edf0ee]">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-[#758179] flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-[#829087]" />
            <span>Fit assessment</span>
          </span>
          {influencer.suitability_score !== null ? (
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${scoreBadge.class}`}>
              {influencer.suitability_score}/100
            </span>
          ) : (
            <span className="text-[10px] text-[#929c95] font-medium">Not assessed</span>
          )}
        </div>

        {influencer.profile_summary && (
          <p className="text-[11px] text-[#738078] line-clamp-2 mt-1.5 leading-relaxed">
            {influencer.profile_summary}
          </p>
        )}
      </div>

      {/* Bottom Status & Actions */}
      <div className="mt-4 pt-3 border-t border-[#edf0ee] flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
        <StatusBadge
          status={influencer.status}
          onStatusChange={(newStatus) => onStatusChange(influencer.id, newStatus)}
        />

        <div className="flex items-center gap-1">
          <button
            onClick={() => onViewDetails(influencer)}
            className="p-1.5 rounded-md text-[#89948d] hover:text-[#34463b] hover:bg-[#f1f5f2] transition-colors"
            title="Inspect"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onDelete(influencer.id)}
            className="p-1.5 rounded-md text-[#89948d] hover:text-rose-600 hover:bg-rose-50 transition-colors"
            title="Delete"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
