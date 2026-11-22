import React, { useState } from 'react';
import { ExternalLink, Mail, Copy, Check, Sparkles, Trash2, Eye, FileSpreadsheet, ArrowUpDown } from 'lucide-react';
import { formatFollowers, getScoreBadge } from '../utils/helpers';
import StatusBadge from './StatusBadge';

export default function InfluencerTable({
  influencers,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onViewDetails,
  onStatusChange,
  onDelete,
  sortBy,
  sortOrder,
  onSortChange
}) {
  const [copiedId, setCopiedId] = useState(null);

  const handleCopyEmail = (id, email, e) => {
    e.stopPropagation();
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const isAllSelected = influencers.length > 0 && influencers.every((inf) => selectedIds.includes(inf.id));

  return (
    <div className="overflow-x-auto rounded-lg border border-[#e8dbd4] bg-[#fffaf3]">
      <table className="w-full min-w-[1080px] text-left text-xs">
        <thead className="bg-[#f8f0e8] text-[#82757a] uppercase tracking-wide text-[10px] font-semibold border-b border-[#ecdfd9]">
          <tr>
            <th className="p-3.5 w-10">
              <input
                type="checkbox"
                checked={isAllSelected}
                onChange={onToggleSelectAll}
                className="w-4 h-4 rounded text-[#725565] border-[#d6c6c2] focus:ring-[#9c7d8b]"
              />
            </th>
            <th className="p-3.5">
              <button
                onClick={() => onSortChange('name')}
                className="flex items-center gap-1.5 hover:text-[#30262e] transition-colors"
              >
                <span>Influencer</span>
                <ArrowUpDown className="w-3 h-3" />
              </button>
            </th>
            <th className="p-3.5">Niche</th>
            <th className="p-3.5">
              <button
                onClick={() => onSortChange('followers_count')}
                className="flex items-center gap-1.5 hover:text-[#30262e] transition-colors"
              >
                <span>Followers</span>
                <ArrowUpDown className="w-3 h-3" />
              </button>
            </th>
            <th className="p-3.5">Public Email</th>
            <th className="p-3.5">Location</th>
            <th className="p-3.5">Lead Status</th>
            <th className="p-3.5">
              <button
                onClick={() => onSortChange('suitability_score')}
                className="flex items-center gap-1.5 hover:text-[#30262e] transition-colors"
              >
                <span>Fit score</span>
                <ArrowUpDown className="w-3 h-3" />
              </button>
            </th>
            <th className="p-3.5 text-center">Sheets</th>
            <th className="p-3.5 text-right">Actions</th>
          </tr>
        </thead>

        <tbody className="divide-y divide-[#f0e5df] text-[#62545d]">
          {influencers.length === 0 ? (
            <tr>
              <td colSpan="10" className="p-10 text-center text-[#82757a]">
                No creator records match these filters.
              </td>
            </tr>
          ) : (
            influencers.map((inf) => {
              const isSelected = selectedIds.includes(inf.id);
              const scoreBadge = getScoreBadge(inf.suitability_score);

              return (
                <tr
                  key={inf.id}
                  onClick={() => onViewDetails(inf)}
                  className={`cursor-pointer transition-colors ${
                    isSelected ? 'bg-[#f8eeeb]' : 'hover:bg-[#fffdf9]'
                  }`}
                >
                  {/* Checkbox */}
                  <td className="p-3.5" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelect(inf.id)}
                      className="w-4 h-4 rounded text-[#725565] border-[#d6c6c2] focus:ring-[#9c7d8b]"
                    />
                  </td>

                  {/* Name & Username */}
                  <td className="p-3.5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-md bg-[#efd9d5] flex items-center justify-center font-semibold text-[#725565] text-xs">
                        {inf.name.charAt(0)}
                      </div>
                      <div>
                        <div className="font-medium text-[#30262e] hover:text-[#725565] transition-colors">
                          {inf.name}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[#93858a] text-[11px]">@{inf.instagram_username}</span>
                          <a
                            href={inf.profile_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-[#a99b9c] hover:text-[#725565] transition-colors"
                            title="Open Instagram"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      </div>
                    </div>
                  </td>

                  {/* Niche */}
                  <td className="p-3.5">
                    <span className="px-2 py-1 rounded-md bg-[#f8f0e8] text-[#75686e] border border-[#ecdfd9] text-[11px]">
                      {inf.niche}
                    </span>
                  </td>

                  {/* Followers */}
                  <td className="p-3.5 font-medium text-[#493744]">
                    {formatFollowers(inf.followers_count)}
                  </td>

                  {/* Email */}
                  <td className="p-3.5" onClick={(e) => e.stopPropagation()}>
                    {inf.email ? (
                      <button
                        onClick={(e) => handleCopyEmail(inf.id, inf.email, e)}
                        className="flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-[#fffdf9] hover:bg-[#f8f0e8] border border-[#ecdfd9] text-[11px] text-[#62545d] transition-colors max-w-[190px] truncate"
                        title="Click to copy email"
                      >
                        <Mail className="w-3 h-3 text-[#9c7d8b] flex-shrink-0" />
                        <span className="truncate">{inf.email}</span>
                        {copiedId === inf.id ? (
                          <Check className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <Copy className="w-3 h-3 text-[#a99b9c] flex-shrink-0" />
                        )}
                      </button>
                    ) : (
                      <span className="text-[#a99b9c] italic text-[11px]">None listed</span>
                    )}
                  </td>

                  {/* Location */}
                  <td className="p-3.5 text-[#82757a] truncate max-w-[160px]">
                    {inf.location}
                  </td>

                  {/* Lead Status */}
                  <td className="p-3.5" onClick={(e) => e.stopPropagation()}>
                    <StatusBadge
                      status={inf.status}
                      onStatusChange={(newStatus) => onStatusChange(inf.id, newStatus)}
                    />
                  </td>

                  {/* Claude AI Suitability Score */}
                  <td className="p-3.5">
                    {inf.suitability_score !== null ? (
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${scoreBadge.class}`}>
                          {inf.suitability_score}/100
                        </span>
                        <div className="w-12 bg-[#ecdfd9] h-1.5 rounded-full overflow-hidden hidden sm:block">
                          <div
                            className={`h-full ${scoreBadge.barColor}`}
                            style={{ width: `${inf.suitability_score}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onViewDetails(inf);
                        }}
                        className="flex items-center gap-1 text-[11px] text-[#806478] hover:text-[#604759] font-medium"
                      >
                        <Sparkles className="w-3 h-3" />
                        <span>Run AI</span>
                      </button>
                    )}
                  </td>

                  {/* Sheets status */}
                  <td className="p-3.5 text-center">
                    {inf.synced_to_sheets ? (
                      <span title="Synced to Google Sheets" className="inline-block text-[#806478]">
                        <FileSpreadsheet className="w-4 h-4 mx-auto" />
                      </span>
                    ) : (
                      <span title="Not synced to Sheets" className="inline-block text-[#c8b9b6]">
                        <FileSpreadsheet className="w-4 h-4 mx-auto" />
                      </span>
                    )}
                  </td>

                  {/* Actions */}
                  <td className="p-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => onViewDetails(inf)}
                        className="p-1.5 rounded-md text-[#9a8b8e] hover:text-[#493744] hover:bg-[#f4e9e3] transition-colors"
                        title="View Full Profile & AI Analysis"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onDelete(inf.id)}
                        className="p-1.5 rounded-md text-[#9a8b8e] hover:text-rose-700 hover:bg-rose-50 transition-colors"
                        title="Delete Influencer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
