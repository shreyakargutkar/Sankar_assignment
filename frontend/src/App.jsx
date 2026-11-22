import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Filter,
  SlidersHorizontal,
  LayoutGrid,
  List,
  Sparkles,
  FileSpreadsheet,
  Download,
  Trash2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  X,
  Mail,
} from 'lucide-react';

import Navbar from './components/Navbar';
import StatsOverview from './components/StatsOverview';
import InfluencerTable from './components/InfluencerTable';
import InfluencerCard from './components/InfluencerCard';
import CampaignDiscoveryModal from './components/CampaignDiscoveryModal';
import CSVUploadModal from './components/CSVUploadModal';
import AddInfluencerModal from './components/AddInfluencerModal';
import InfluencerDetailModal from './components/InfluencerDetailModal';
import GoogleSheetsModal from './components/GoogleSheetsModal';
import OutreachWorkspace from './components/OutreachWorkspace';

import { api } from './services/api';
import { NICHES, LEAD_STATUSES } from './utils/helpers';

export default function App() {
  // Data states
  const [influencers, setInfluencers] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [stats, setStats] = useState(null);
  const [integrationsStatus, setIntegrationsStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Search & Filter states
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedNiche, setSelectedNiche] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState(null);
  const [minScoreFilter, setMinScoreFilter] = useState('');
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'grid'

  // Sorting
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  // Selection
  const [selectedIds, setSelectedIds] = useState([]);

  // Modal states
  const [isDiscoveryOpen, setIsDiscoveryOpen] = useState(false);
  const [isCSVUploadOpen, setIsCSVUploadOpen] = useState(false);
  const [isAddLeadOpen, setIsAddLeadOpen] = useState(false);
  const [isSheetsModalOpen, setIsSheetsModalOpen] = useState(false);
  const [selectedInfluencer, setSelectedInfluencer] = useState(null);
  const [isOutreachOpen, setIsOutreachOpen] = useState(false);

  const showToast = (message, type = 'success') => {
    setToastMessage({ message, type });
    setTimeout(() => setToastMessage(null), 3500);
  };

  const loadData = useCallback(async (quiet = false) => {
    if (!quiet) setIsLoading(true);
    else setIsRefreshing(true);

    try {
      const [infRes, statsRes, statusRes] = await Promise.all([
        api.getInfluencers({
          search: searchTerm,
          niche: selectedNiche,
          status: selectedStatus || undefined,
          min_score: minScoreFilter ? parseInt(minScoreFilter, 10) : undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
          limit: 100,
        }),
        api.getStats(),
        api.getIntegrationsStatus(),
      ]);

      setInfluencers(infRes.data || []);
      setTotalCount(infRes.total || 0);
      setStats(statsRes);
      setIntegrationsStatus(statusRes);
    } catch (err) {
      console.error('Failed to load influencer data:', err);
      showToast('Error connecting to backend API.', 'error');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [searchTerm, selectedNiche, selectedStatus, minScoreFilter, sortBy, sortOrder]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Status update handler
  const handleStatusChange = async (id, newStatus) => {
    try {
      await api.updateStatus(id, newStatus);
      showToast(`Updated lead status to '${newStatus}'`);
      loadData(true);
      if (selectedInfluencer && selectedInfluencer.id === id) {
        setSelectedInfluencer((prev) => ({ ...prev, status: newStatus }));
      }
    } catch (err) {
      showToast(err.message || 'Failed to update status', 'error');
    }
  };

  // Delete handler
  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this influencer lead?')) return;
    try {
      await api.deleteInfluencer(id);
      showToast('Influencer lead removed');
      setSelectedIds((prev) => prev.filter((i) => i !== id));
      loadData(true);
      if (selectedInfluencer && selectedInfluencer.id === id) {
        setSelectedInfluencer(null);
      }
    } catch (err) {
      showToast('Failed to delete lead', 'error');
    }
  };

  // Selection handlers
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleToggleSelectAll = () => {
    if (selectedIds.length === influencers.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(influencers.map((i) => i.id));
    }
  };

  // Batch AI analyze
  const handleBatchAIAnalyze = async () => {
    if (selectedIds.length === 0) return;
    try {
      showToast(`Assessing ${selectedIds.length} creator profiles...`, 'info');
      await api.batchAnalyzeAI({
        influencer_ids: selectedIds,
        brand_name: 'Selected Campaign',
        campaign_description: 'Multi-creator influencer marketing outreach campaign',
      });
      showToast(`Assessed ${selectedIds.length} creator profiles.`);
      loadData(true);
    } catch (err) {
      showToast(`AI Analysis failed: ${err.message}`, 'error');
    }
  };

  // Export selected / all to CSV
  const handleExportCSV = () => {
    const recordsToExport = selectedIds.length > 0
      ? influencers.filter((i) => selectedIds.includes(i.id))
      : influencers;

    if (recordsToExport.length === 0) {
      showToast('No records to export', 'error');
      return;
    }

    const headers = ['Name', 'Instagram Username', 'Profile URL', 'Niche', 'Followers', 'Email', 'Location', 'Status', 'Suitability Score', 'AI Summary'];
    const rows = recordsToExport.map((i) => [
      `"${i.name.replace(/"/g, '""')}"`,
      `"@${i.instagram_username}"`,
      `"${i.profile_url}"`,
      `"${i.niche}"`,
      i.followers_count,
      `"${i.email || ''}"`,
      `"${i.location}"`,
      `"${i.status}"`,
      i.suitability_score || '',
      `"${(i.profile_summary || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `influencers_export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`Exported ${recordsToExport.length} influencers to CSV!`);
  };

  // Sort change handler
  const handleSortChange = (col) => {
    if (sortBy === col) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(col);
      setSortOrder('desc');
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f6f5] text-[#26342d] flex flex-col font-sans">
      
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 flex items-center gap-2 px-4 py-3 rounded-lg bg-white border border-[#dfe5e1] shadow-lg text-sm font-medium text-[#26342d]">
          {toastMessage.type === 'error' ? (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          )}
          <span>{toastMessage.message}</span>
        </div>
      )}

      {/* Navigation Header */}
      <Navbar
        integrationsStatus={integrationsStatus}
        onOpenDiscovery={() => setIsDiscoveryOpen(true)}
        onOpenCSVUpload={() => setIsCSVUploadOpen(true)}
        onOpenAddInfluencer={() => setIsAddLeadOpen(true)}
        onOpenGoogleSheets={() => setIsSheetsModalOpen(true)}
        onOpenOutreach={() => setIsOutreachOpen(true)}
        onRefreshData={() => loadData(true)}
        isRefreshing={isRefreshing}
      />

      {/* Main Body */}
      <main className="flex-1 max-w-[1440px] w-full mx-auto px-5 lg:px-8 py-6 space-y-5">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-[#849088]">Workspace</p>
            <h1 className="mt-1 text-xl font-semibold tracking-tight text-[#26342d]">Creator pipeline</h1>
            <p className="mt-1 text-sm text-[#738078]">Review prospects, manage contacts, and track partnership outreach.</p>
          </div>
          <p className="hidden sm:block text-xs text-[#8a948e]">
            {totalCount.toLocaleString()} {totalCount === 1 ? 'creator' : 'creators'}
          </p>
        </div>
        
        {/* Pipeline & Analytics Stats */}
        <StatsOverview
          stats={stats}
          currentStatusFilter={selectedStatus}
          onSelectStatusFilter={(status) => setSelectedStatus(status)}
        />

        {/* Search, Filter & Action Controls Bar */}
        <div className="p-4 rounded-lg bg-white border border-[#e1e7e3] space-y-3">
          
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
            
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-[#89948d] absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by creator name, @handle, keywords, email, or city..."
                className="w-full pl-9 pr-8 py-2.5 rounded-md bg-white border border-[#dfe5e1] text-sm text-[#29362f] placeholder-[#9aa39e] focus:outline-none focus:border-[#73917e] transition-colors"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#89948d] hover:text-[#34463b]"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Quick Filters */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Niche Dropdown */}
              <select
                value={selectedNiche}
                onChange={(e) => setSelectedNiche(e.target.value)}
                className="px-3 py-2.5 rounded-md bg-white border border-[#dfe5e1] text-sm text-[#536159] focus:outline-none focus:border-[#73917e]"
              >
                <option value="All">All Niches</option>
                {NICHES.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>

              {/* Min AI Score Filter */}
              <select
                value={minScoreFilter}
                onChange={(e) => setMinScoreFilter(e.target.value)}
                className="px-3 py-2.5 rounded-md bg-white border border-[#dfe5e1] text-sm text-[#536159] focus:outline-none focus:border-[#73917e]"
              >
                <option value="">Any fit score</option>
                <option value="80">Fit score 80+ (Strong)</option>
                <option value="70">Fit score 70+ (Good)</option>
                <option value="55">Fit score 55+ (Possible)</option>
              </select>

              {/* View Switcher */}
              <div className="flex items-center rounded-md bg-[#f4f6f4] border border-[#e1e7e3] p-0.5">
                <button
                  onClick={() => setViewMode('table')}
                  className={`p-1.5 rounded-md transition-colors ${
                    viewMode === 'table' ? 'bg-white text-[#315840] shadow-sm' : 'text-[#7a867f] hover:text-[#34463b]'
                  }`}
                  title="Table View"
                >
                  <List className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-1.5 rounded-md transition-colors ${
                    viewMode === 'grid' ? 'bg-white text-[#315840] shadow-sm' : 'text-[#7a867f] hover:text-[#34463b]'
                  }`}
                  title="Grid Cards View"
                >
                  <LayoutGrid className="w-4 h-4" />
                </button>
              </div>
            </div>

          </div>

          {/* Batch Actions Toolbar (Shown when items selected or always visible for export) */}
          <div className="flex flex-wrap items-center justify-between pt-3 border-t border-[#edf0ee] text-xs text-[#77837c]">
            <div className="flex items-center gap-2">
              <span>Showing <span className="font-semibold text-[#35433b]">{influencers.length}</span> of <span className="font-semibold text-[#35433b]">{totalCount}</span> creators</span>
              {selectedIds.length > 0 && (
                <span className="px-2 py-0.5 rounded-md bg-[#edf4ef] text-[#315840] border border-[#dce9df] font-medium">
                  {selectedIds.length} selected
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 mt-2 sm:mt-0">
              {selectedIds.length > 0 && (
                <>
                  <button
                    onClick={handleBatchAIAnalyze}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-[#f5f8f6] text-[#45644f] border border-[#dfe7e1] font-medium transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Assess selected ({selectedIds.length})</span>
                  </button>

                  <button
                    onClick={() => setIsOutreachOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-[#f5f8f6] text-[#45644f] border border-[#dfe7e1] font-medium transition-colors"
                  >
                    <Mail className="w-3.5 h-3.5" />
                    <span>Draft outreach ({selectedIds.length})</span>
                  </button>

                  <button
                    onClick={() => setIsSheetsModalOpen(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-[#f5f8f6] text-[#45644f] border border-[#dfe7e1] font-medium transition-colors"
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5" />
                    <span>Sync Selected</span>
                  </button>

                  <button
                    onClick={() => setSelectedIds([])}
                    className="px-2 py-1.5 text-[#77837c] hover:text-[#34463b]"
                  >
                    Clear Selection
                  </button>
                </>
              )}

              <button
                onClick={handleExportCSV}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white hover:bg-[#f6f8f6] text-[#526057] border border-[#dfe5e1] font-medium transition-colors"
                title="Download CSV of current list"
              >
                <Download className="w-3.5 h-3.5 text-slate-400" />
                <span>Export CSV</span>
              </button>
            </div>

          </div>

        </div>

        {/* Content Section: Table or Cards */}
        {isLoading ? (
          <div className="p-16 text-center rounded-lg bg-white border border-[#e1e7e3]">
            <RefreshCw className="w-7 h-7 text-[#52735f] animate-spin mx-auto mb-3" />
            <p className="text-sm font-medium text-[#68756e]">Loading creator records…</p>
          </div>
        ) : viewMode === 'table' ? (
          <InfluencerTable
            influencers={influencers}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelect}
            onToggleSelectAll={handleToggleSelectAll}
            onViewDetails={(inf) => setSelectedInfluencer(inf)}
            onStatusChange={handleStatusChange}
            onDelete={handleDelete}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSortChange={handleSortChange}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {influencers.map((inf) => (
              <InfluencerCard
                key={inf.id}
                influencer={inf}
                isSelected={selectedIds.includes(inf.id)}
                onToggleSelect={handleToggleSelect}
                onViewDetails={(creator) => setSelectedInfluencer(creator)}
                onStatusChange={handleStatusChange}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-[#e4e9e6] py-4 bg-white text-center text-xs text-[#8a948e]">
        Creator CRM · Research, contact management, and outreach
      </footer>

      {/* Modals */}
      <CampaignDiscoveryModal
        isOpen={isDiscoveryOpen}
        onClose={() => setIsDiscoveryOpen(false)}
        onDiscoveryComplete={() => {
          showToast('Discovery run completed! Added new matching leads.');
          loadData(true);
        }}
      />

      <CSVUploadModal
        isOpen={isCSVUploadOpen}
        onClose={() => setIsCSVUploadOpen(false)}
        onUploadComplete={() => {
          showToast('CSV import completed successfully.');
          loadData(true);
        }}
      />

      <AddInfluencerModal
        isOpen={isAddLeadOpen}
        onClose={() => setIsAddLeadOpen(false)}
        onCreated={() => {
          showToast('New influencer lead added.');
          loadData(true);
        }}
      />

      <InfluencerDetailModal
        influencer={selectedInfluencer}
        isOpen={!!selectedInfluencer}
        onClose={() => setSelectedInfluencer(null)}
        onStatusUpdate={handleStatusChange}
        onInfluencerUpdated={(updated) => {
          setSelectedInfluencer(updated);
          loadData(true);
          showToast('Creator profile updated.');
        }}
      />

      <GoogleSheetsModal
        isOpen={isSheetsModalOpen}
        onClose={() => setIsSheetsModalOpen(false)}
        selectedCount={selectedIds.length}
        onSyncSuccess={(res) => {
          showToast(res.message);
          loadData(true);
        }}
      />

      <OutreachWorkspace
        isOpen={isOutreachOpen}
        onClose={() => setIsOutreachOpen(false)}
        selectedInfluencers={influencers.filter((i) => selectedIds.includes(i.id))}
        onChanged={() => loadData(true)}
        showToast={showToast}
      />

    </div>
  );
}
