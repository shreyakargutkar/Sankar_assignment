import React from 'react';
import { FileSpreadsheet, Mail, Plus, RefreshCw, Search, Upload } from 'lucide-react';

export default function Navbar({
  integrationsStatus,
  onOpenDiscovery,
  onOpenCSVUpload,
  onOpenAddInfluencer,
  onOpenGoogleSheets,
  onOpenOutreach,
  onRefreshData,
  isRefreshing
}) {
  const isSheetsActive = integrationsStatus?.google_sheets?.configured;
  const gmailConnected = integrationsStatus?.gmail?.connected;
  const aiLabel = integrationsStatus?.claude_ai?.status_label || 'Demo mode';

  return (
    <header className="sticky top-0 z-40 border-b border-[#e8dbd4] bg-[#fffaf3]/95 backdrop-blur">
      <div className="max-w-[1440px] mx-auto px-5 lg:px-8">
        <div className="min-h-[72px] flex flex-wrap items-center justify-between gap-4 py-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#efd9d5] text-[#725565] flex items-center justify-center font-semibold text-sm">
              CH
            </div>
            <div>
              <div className="font-semibold text-[15px] leading-5 text-[#30262e]">Creator House</div>
              <p className="text-xs text-[#82757a]">Research and partnership management</p>
            </div>
          </div>

          <div className="hidden xl:flex items-center gap-2 text-[11px]">
            <span className="text-[#93858a] mr-1">Connected services</span>
            <span className="inline-flex items-center gap-1.5 rounded-md border border-[#eaded7] bg-[#fffaf3] px-2.5 py-1.5 text-[#62545d]">
              <span className={`w-1.5 h-1.5 rounded-full ${aiLabel.toLowerCase().includes('active') ? 'bg-[#806478]' : 'bg-[#c18a3d]'}`} />
              AI · {aiLabel}
            </span>
            <button
              onClick={onOpenGoogleSheets}
              className="inline-flex items-center gap-1.5 rounded-md border border-[#eaded7] bg-[#fffaf3] px-2.5 py-1.5 text-[#62545d] hover:bg-[#f8f0e8]"
              title="View Google Sheets connection"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-[#907586]" />
              Sheets · {isSheetsActive ? 'Connected' : 'Local sync'}
            </button>
            <button
              onClick={onOpenOutreach}
              className="inline-flex items-center gap-1.5 rounded-md border border-[#eaded7] bg-[#fffaf3] px-2.5 py-1.5 text-[#62545d] hover:bg-[#f8f0e8]"
              title="Gmail outreach settings"
            >
              <Mail className="w-3.5 h-3.5 text-[#907586]" />
              Gmail · {gmailConnected ? 'Connected' : 'Demo'}
            </button>
          </div>

          <nav className="flex items-center gap-2" aria-label="Creator actions">
            <button
              onClick={onRefreshData}
              disabled={isRefreshing}
              className="p-2 rounded-md text-[#82757a] hover:bg-[#f4e9e3] disabled:opacity-50"
              title="Refresh data"
              aria-label="Refresh data"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onOpenCSVUpload}
              className="hidden md:inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-[#e6d9d2] bg-[#fffaf3] text-[#51444c] text-sm hover:bg-[#f8f0e8]"
            >
              <Upload className="w-3.5 h-3.5" />
              Import
            </button>
            <button
              onClick={onOpenAddInfluencer}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-[#e6d9d2] bg-[#fffaf3] text-[#51444c] text-sm hover:bg-[#f8f0e8]"
            >
              <Plus className="w-4 h-4" />
              Add creator
            </button>
            <button
              onClick={onOpenOutreach}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-[#e6d9d2] bg-[#fffaf3] text-[#51444c] text-sm hover:bg-[#f8f0e8]"
            >
              <Mail className="w-3.5 h-3.5" />
              Outreach
            </button>
            <button
              onClick={onOpenDiscovery}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md bg-[#30262e] hover:bg-[#493744] text-[#fffaf3] text-sm font-medium"
            >
              <Search className="w-3.5 h-3.5" />
              Find creators
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
}
